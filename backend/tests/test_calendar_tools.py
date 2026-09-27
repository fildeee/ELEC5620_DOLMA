"""
The calendar tools, driven end to end through POST /api/chat.

Google Calendar is stubbed, so these assert on what the agent *decided* to do:
which tools it reached for, what it previewed, and — the part that matters —
that nothing is written to the calendar until the user has agreed.
"""

from fakes import (
    Call,
    FakeClient,
    Msg,
    SAMPLE_WEATHER,
    stubbed_google,
    stubbed_weather,
    tool_messages,
)

import app as dolma_app

SYDNEY = {"lat": -33.86, "lon": 151.2}


def post(script, message="hi", location=None):
    """Send one chat request with the model's turns scripted."""
    client = FakeClient(script)
    dolma_app.client = client
    http = dolma_app.app.test_client()
    response = http.post("/api/chat", json={
        "message": message,
        "conversation": [],
        "location": location if location is not None else SYDNEY,
    })
    return response, response.get_json(), client


def observations(client):
    """The observations the loop appended, read off the model's last request."""
    return tool_messages(client.last_request_messages())


def test_find_events_answers_from_what_it_observed():
    with stubbed_google():
        response, body, client = post([
            Msg(None, [Call("find_events", {"preset": "this_week"})]),
            Msg("You have Gym twice and a Team meeting."),
        ])

    assert response.status_code == 200
    assert body["reply"] == "You have Gym twice and a Team meeting."
    # The model was handed the real titles rather than inventing them.
    assert [e["title"] for e in observations(client)[0]["events"]] == [
        "Gym", "Team meeting", "Gym",
    ]
    assert body["trace"][0]["tool"] == "find_events"


def test_lookup_then_update_chains_in_one_request():
    with stubbed_google() as rec:
        response, body, client = post([
            Msg(None, [Call("find_events", {"preset": "this_week"})]),
            Msg(None, [Call("update_event", {
                "query": "gym", "preset": "this_week",
                "start_time": "2026-09-23T18:00:00+10:00",
                "end_time": "2026-09-23T19:00:00+10:00",
            })]),
            Msg("I found 2 gym sessions. Move them to 6pm?"),
        ])

    # Look it up, then act on what was found: three passes through the model.
    assert len(client.seen) == 3
    preview = observations(client)[1]
    assert preview["status"] == "awaiting_confirmation"
    assert rec.updated == []  # previewing must not write
    # The preview hands the ids back so the confirm can target exactly these.
    assert preview["event_ids"] == ["e1", "e3"]
    assert body["cta"] == "apply now?"


def test_confirm_updates_only_the_previewed_events():
    with stubbed_google() as rec:
        post([
            Msg(None, [Call("update_event", {
                "query": "gym", "preset": "this_week", "event_ids": ["e1"],
                "start_time": "2026-09-23T18:00:00+10:00", "confirm": True,
            })]),
            Msg("Moved it."),
        ])

    assert [event_id for event_id, _ in rec.updated] == ["e1"]
    assert "start_time" in rec.updated[0][1]


def test_delete_previews_before_it_deletes():
    with stubbed_google() as rec:
        post([
            Msg(None, [Call("delete_event", {"query": "gym", "preset": "this_week"})]),
            Msg("Delete both gym sessions?"),
        ])
        assert rec.deleted == []

    with stubbed_google() as rec:
        post([
            Msg(None, [Call("delete_event", {
                "query": "gym", "preset": "this_week",
                "event_ids": ["e3"], "confirm": True,
            })]),
            Msg("Deleted."),
        ])
        assert rec.deleted == ["e3"]


def test_a_write_cannot_be_confirmed_in_the_turn_that_previewed_it():
    """The user has not spoken between the two calls, so the second is refused."""
    with stubbed_google() as rec:
        _, _, client = post([
            Msg(None, [Call("create_event", {"events": [{
                "summary": "Study", "start_time": "2026-09-24T09:00:00+10:00",
                "end_time": "2026-09-24T11:00:00+10:00",
            }]})]),
            Msg(None, [Call("create_event", {"events": [{
                "summary": "Study", "start_time": "2026-09-24T09:00:00+10:00",
                "end_time": "2026-09-24T11:00:00+10:00",
            }], "confirm": True})]),
            Msg("Shall I add it?"),
        ])

    seen = observations(client)
    assert seen[0]["status"] == "awaiting_confirmation"
    assert seen[1]["status"] == "not_confirmed"
    assert rec.created == []


def test_create_writes_once_the_user_has_agreed():
    with stubbed_google() as rec:
        _, body, _ = post([
            Msg(None, [Call("create_event", {"events": [{
                "summary": "Study", "start_time": "2026-09-24T09:00:00+10:00",
                "end_time": "2026-09-24T11:00:00+10:00",
            }], "confirm": True})]),
            Msg("Added Study on Thursday."),
        ])

    assert len(rec.created) == 1
    assert rec.created[0]["summary"] == "Study"
    assert body["reply"] == "Added Study on Thursday."


def test_a_disconnected_calendar_is_reported_not_crashed():
    with stubbed_google(connected=False):
        response, _, client = post([
            Msg(None, [Call("find_events", {"preset": "today"})]),
            Msg("Please connect Google Calendar in Settings."),
        ])

    assert response.status_code == 200
    assert observations(client)[0]["status"] == "calendar_not_connected"


def test_an_unusable_time_window_comes_back_for_correction():
    with stubbed_google():
        _, _, client = post([
            Msg(None, [Call("find_events", {})]),
            Msg(None, [Call("find_events", {"preset": "today"})]),
            Msg("Nothing on today."),
        ])

    seen = observations(client)
    assert seen[0]["status"] == "missing_input"
    # Having been told what was wrong, the model retried successfully.
    assert "events" in seen[1]


def test_weather_then_calendar_is_one_chain_of_reasoning():
    with stubbed_google(), stubbed_weather():
        _, body, _ = post(
            [
                Msg(None, [Call("get_weather")]),
                Msg(None, [Call("find_events", {"preset": "today"})]),
                Msg("It's raining, and your Gym session is at 7am."),
            ],
            message="should I run outside today?",
        )

    assert [step["tool"] for step in body["trace"]] == ["get_weather", "find_events"]
    assert body["place_name"] == SAMPLE_WEATHER["place_name"]
    assert body["tips"] == SAMPLE_WEATHER["tips"]


def test_weather_no_longer_needs_a_keyword():
    """The old build only fetched weather when the message said 'weather'."""
    with stubbed_weather():
        _, body, _ = post(
            [Msg(None, [Call("get_weather")]), Msg("Cool and wet out there.")],
            message="is it a good day to cycle to campus?",
        )

    assert body["trace"][0]["tool"] == "get_weather"
