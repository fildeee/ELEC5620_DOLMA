"""
The Sydney offset on an event the model scheduled.

Asked in September to book lunch at 11:45, the assistant wrote
`2026-09-24T11:45:00+11:00`. Sydney is +10:00 until October, so that is 10:45
local — the booking landed an hour before the user said, and nothing caught it
because the string was valid RFC3339 and the card obligingly displayed 10:45.

The offset is no longer the model's to choose: it gives a wall-clock time and
the backend resolves it against Australia/Sydney, which knows where the
daylight-saving boundary falls. These cover both sides of that boundary, and
that what the user approves in the preview is the moment that gets written.
"""

from datetime import datetime

from fakes import Call, FakeClient, Msg, stubbed_google

import app as dolma_app
from formatting import to_sydney_wall_clock

SYDNEY = {"lat": -33.86, "lon": 151.2}

# September is AEST (+10:00); late December is AEDT (+11:00).
AEST_DAY = "2026-09-24"
AEDT_DAY = "2026-12-24"


def post(script, message="hi"):
    client = FakeClient(script)
    dolma_app.client = client
    http = dolma_app.app.test_client()
    response = http.post("/api/chat", json={
        "message": message, "conversation": [], "location": SYDNEY,
    })
    return response, response.get_json(), client


def lunch(start, end, confirm=False):
    """One model turn that calls create_event for a single lunch."""
    return Msg(None, [Call("create_event", {
        "events": [{"summary": "Lunch with friends", "start_time": start, "end_time": end}],
        "confirm": confirm,
    })])


# --- the helper, directly ----------------------------------------------------

def test_an_aedt_offset_on_an_aest_date_keeps_the_wall_clock():
    # The reported bug, at its smallest.
    assert to_sydney_wall_clock(f"{AEST_DAY}T11:45:00+11:00") == f"{AEST_DAY}T11:45:00+10:00"


def test_an_aest_offset_on_an_aedt_date_keeps_the_wall_clock():
    # The same mistake in the other direction, which December would produce.
    assert to_sydney_wall_clock(f"{AEDT_DAY}T11:45:00+10:00") == f"{AEDT_DAY}T11:45:00+11:00"


def test_a_time_with_no_offset_gets_the_right_one_for_its_date():
    assert to_sydney_wall_clock(f"{AEST_DAY}T11:45:00") == f"{AEST_DAY}T11:45:00+10:00"
    assert to_sydney_wall_clock(f"{AEDT_DAY}T11:45:00") == f"{AEDT_DAY}T11:45:00+11:00"


def test_an_already_correct_time_is_left_alone():
    assert to_sydney_wall_clock(f"{AEST_DAY}T10:45:00+10:00") == f"{AEST_DAY}T10:45:00+10:00"


# --- through the agent, to what Google would have been sent ------------------

def test_the_hour_the_user_asked_for_is_the_hour_that_gets_written():
    with stubbed_google() as rec:
        post([
            lunch(f"{AEST_DAY}T11:45:00+11:00", f"{AEST_DAY}T13:15:00+11:00", confirm=True),
            Msg("Booked."),
        ])

    written = rec.created[0]["start_time"]
    assert isinstance(written, datetime)
    assert (written.hour, written.minute) == (11, 45)
    assert written.utcoffset().total_seconds() == 10 * 3600


def test_the_preview_card_shows_the_hour_the_user_asked_for():
    with stubbed_google():
        _, body, _ = post([
            lunch(f"{AEST_DAY}T11:45:00+11:00", f"{AEST_DAY}T13:15:00+11:00"),
            Msg("Shall I add it?"),
        ])

    shown = {item["label"]: item["value"] for item in body["items"]}
    assert shown["time"] == "11:45 AM – 1:15 PM"
    assert shown["date"] == "Thursday, 24 September 2026"


def test_what_was_previewed_is_what_is_written():
    # The user agrees to a card; the event must be that moment and not another.
    with stubbed_google() as rec:
        _, preview, _ = post([
            lunch(f"{AEST_DAY}T11:45:00+11:00", f"{AEST_DAY}T13:15:00+11:00"),
            Msg("Shall I add it?"),
        ])
        post([
            lunch(f"{AEST_DAY}T11:45:00+11:00", f"{AEST_DAY}T13:15:00+11:00", confirm=True),
            Msg("Booked."),
        ])

    shown = {item["label"]: item["value"] for item in preview["items"]}
    written = rec.created[0]["start_time"]
    assert shown["time"].startswith(f"{written.hour % 12 or 12}:{written.minute:02d}")


def test_rescheduling_corrects_the_offset_too():
    # update_event takes the same times from the same model and needs the same care.
    with stubbed_google() as rec:
        post([
            Msg(None, [Call("update_event", {
                "query": "Team meeting",
                # An explicit window, so the test does not depend on what day it is.
                "time_min": "2026-09-23T00:00:00+10:00",
                "time_max": "2026-09-23T23:59:59+10:00",
                "start_time": "2026-09-23T16:00:00+11:00",
                "end_time": "2026-09-23T17:00:00+11:00",
                "confirm": True,
            })]),
            Msg("Moved."),
        ])

    _, changes = rec.updated[0]
    assert (changes["start_time"].hour, changes["start_time"].minute) == (16, 0)
    assert changes["start_time"].utcoffset().total_seconds() == 10 * 3600
