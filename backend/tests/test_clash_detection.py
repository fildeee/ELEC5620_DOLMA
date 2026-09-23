"""
Whether a new event really collides with one already on the calendar.

The assistant used to decide this itself, and got it wrong in both directions:
told that lunch began at 11:45 and a tutorial ended at 11:45 it announced a
conflict, then declined to book anything at all. Interval arithmetic is not what
a language model is for, so the backend now works the list out and the preview
carries it; the model's only job is to read it out.

These pin down where the boundary lies and that a clash never becomes a refusal.
"""

from fakes import Call, FakeClient, Msg, stubbed_google, tool_messages

import app as dolma_app
import tool_handlers

SYDNEY = {"lat": -33.86, "lon": 151.2}

TUTORIAL = {
    "id": "t1", "summary": "Meeting with Tutor",
    "start": {"dateTime": "2026-09-24T10:45:00+10:00"},
    "end": {"dateTime": "2026-09-24T11:45:00+10:00"},
}
ALL_DAY = {
    "id": "a1", "summary": "Public holiday",
    "start": {"date": "2026-09-24"}, "end": {"date": "2026-09-25"},
}


def clashes(start, end, events=(TUTORIAL,)):
    with stubbed_google(events=list(events)):
        return tool_handlers._clashes_with(start, end)


def post(script, message="hi"):
    client = FakeClient(script)
    dolma_app.client = client
    http = dolma_app.app.test_client()
    response = http.post("/api/chat", json={
        "message": message, "conversation": [], "location": SYDNEY,
    })
    return response.get_json(), client


def creating(start, end):
    return Msg(None, [Call("create_event", {"events": [{
        "summary": "Lunch", "start_time": start, "end_time": end,
    }], "confirm": False})])


# --- where the boundary is ---------------------------------------------------

def test_starting_exactly_when_the_other_ends_is_not_a_clash():
    # The case that started this: 11:45 is free the moment the tutorial ends.
    assert clashes("2026-09-24T11:45:00+10:00", "2026-09-24T13:15:00+10:00") == []


def test_ending_exactly_when_the_other_starts_is_not_a_clash():
    assert clashes("2026-09-24T09:45:00+10:00", "2026-09-24T10:45:00+10:00") == []


def test_a_single_overlapping_minute_is_a_clash():
    found = clashes("2026-09-24T11:44:00+10:00", "2026-09-24T13:00:00+10:00")
    assert len(found) == 1 and "Meeting with Tutor" in found[0]


def test_an_event_swallowing_another_clashes():
    found = clashes("2026-09-24T09:00:00+10:00", "2026-09-24T17:00:00+10:00")
    assert len(found) == 1


def test_an_event_inside_another_clashes():
    found = clashes("2026-09-24T11:00:00+10:00", "2026-09-24T11:30:00+10:00")
    assert len(found) == 1


def test_a_different_day_is_never_a_clash():
    assert clashes("2026-09-25T11:00:00+10:00", "2026-09-25T12:00:00+10:00") == []


def test_an_all_day_event_has_no_times_to_compare_and_is_skipped():
    # It carries a date but no dateTime; reading it must not raise.
    assert clashes("2026-09-24T11:00:00+10:00", "2026-09-24T12:00:00+10:00",
                   events=(ALL_DAY,)) == []


# --- what the preview tells the model ----------------------------------------

def test_a_free_slot_is_reported_as_free():
    with stubbed_google(events=[TUTORIAL]):
        _, client = post([
            creating("2026-09-24T11:45:00+10:00", "2026-09-24T13:15:00+10:00"),
            Msg("Nothing else is on then — shall I add it?"),
        ])

    preview = tool_messages(client.last_request_messages())[0]
    assert preview["clashes"] == []


def test_a_real_clash_is_named_in_the_preview():
    with stubbed_google(events=[TUTORIAL]):
        _, client = post([
            creating("2026-09-24T11:00:00+10:00", "2026-09-24T12:00:00+10:00"),
            Msg("That overlaps your tutorial — still add it?"),
        ])

    preview = tool_messages(client.last_request_messages())[0]
    assert len(preview["clashes"]) == 1
    assert "Meeting with Tutor" in preview["clashes"][0]


def test_a_clash_is_not_a_veto():
    # It still previews and still offers to write; the user decides, not the agent.
    with stubbed_google(events=[TUTORIAL]) as rec:
        body, client = post([
            creating("2026-09-24T11:00:00+10:00", "2026-09-24T12:00:00+10:00"),
            Msg("Still add it?"),
        ])

    preview = tool_messages(client.last_request_messages())[0]
    assert preview["status"] == "awaiting_confirmation"
    assert body["cta"] == "add this now?"
    assert rec.created == []
