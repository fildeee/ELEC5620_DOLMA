"""
find_places, the tool that stops the assistant inventing venues.

Before this tool existed, asking for a nearby bar sent the model looking for one in
the calendar or the weather, and once it answered with five plausible-looking
addresses it had made up. These cover the paths that keep that from happening: real
results are reported, and every way the lookup can come up empty is handed back as
something the model must relay rather than paper over.
"""

from fakes import (
    Call,
    FakeClient,
    Msg,
    SAMPLE_PLACES,
    stubbed_places,
    tool_messages,
)

import app as dolma_app
from tool_handlers import ToolContext, make_dispatcher

SYDNEY = {"lat": -33.8688, "lon": 151.2093}


def call_tool(args, ctx=None):
    ctx = ctx if ctx is not None else ToolContext(**SYDNEY)
    with dolma_app.app.test_request_context("/api/chat"):
        return make_dispatcher(ctx)("find_places", args)


def test_real_results_are_reported_with_their_source():
    with stubbed_places():
        result = call_tool({"category": "bar"})

    observation = result.observation
    assert observation["count"] == 2
    assert [p["name"] for p in observation["places"]] == ["Amber Bar", "SubSolo"]
    assert observation["source"] == "OpenStreetMap"
    # The UI gets the same list to render.
    assert result.ui["places"] == SAMPLE_PLACES


def test_a_missing_field_is_flagged_rather_than_left_to_the_model():
    with stubbed_places():
        observation = call_tool({"category": "bar"}).observation

    unlisted = next(p for p in observation["places"] if p["name"] == "SubSolo")
    assert unlisted["address"] is None
    # The instruction is what stops a null turning into an invented street address.
    assert "does not record it" in observation["instruction"]
    assert "not listed" in observation["instruction"]


def test_an_unknown_category_comes_back_with_the_valid_ones():
    with stubbed_places():
        observation = call_tool({"category": "casino"}).observation

    assert observation["status"] == "missing_input"
    assert "bar" in observation["available_categories"]


def test_no_results_tells_the_model_not_to_fill_the_gap():
    with stubbed_places(places=[]):
        observation = call_tool({"category": "bar", "radius_m": 300}).observation

    assert observation["status"] == "no_results"
    assert "from your own knowledge" in observation["instruction"]


def test_a_failed_lookup_is_an_observation_not_a_crash():
    with stubbed_places(error=RuntimeError("OpenStreetMap returned HTTP 504.")):
        observation = call_tool({"category": "bar"}).observation

    assert "504" in observation["error"]


def test_without_a_location_it_refuses_to_guess():
    with stubbed_places():
        observation = call_tool({"category": "bar"}, ctx=ToolContext()).observation

    assert observation["status"] == "location_unavailable"
    assert "Do not guess" in observation["instruction"]


def test_the_agent_reports_only_what_the_tool_returned():
    """The whole point: the venue in the reply came from an observation."""
    messages = [{"role": "system", "content": "system"},
                {"role": "user", "content": "推荐附近的酒吧"}]
    client = FakeClient([
        Msg(None, [Call("find_places", {"category": "bar"})]),
        Msg("Amber Bar is 88 m away at 122 Pitt Street."),
    ])
    import agent
    from tools import agent_tools

    with stubbed_places(), dolma_app.app.test_request_context("/api/chat"):
        result = agent.run(
            client=client, model="fake", messages=messages, tools=agent_tools,
            dispatch=make_dispatcher(ToolContext(**SYDNEY)), max_steps=4,
        )

    names = [p["name"] for p in tool_messages(messages)[0]["places"]]
    assert "Amber Bar" in names
    assert "Amber Bar" in result.reply
