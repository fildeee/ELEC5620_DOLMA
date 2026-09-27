"""
The reason–act–observe loop itself (agent.py).

These cover the mechanics that make DOLMA an agent rather than a single
function call: that a tool's real result goes back to the model, that the model
can act again after seeing it, and that nothing a confused model does can take
the request down.
"""

from fakes import Call, FakeClient, Msg, stubbed_weather, tool_messages

import agent
import app as dolma_app
import tool_handlers
from tool_handlers import ToolContext, make_dispatcher
from tools import agent_tools

SYDNEY = {"lat": -33.86, "lon": 151.2}


def run_loop(script, ctx=None, max_steps=4):
    """Run one request's worth of loop and hand back the transcript."""
    ctx = ctx if ctx is not None else ToolContext(**SYDNEY)
    messages = [{"role": "system", "content": "system"}, {"role": "user", "content": "hi"}]
    client = FakeClient(script)
    # Handlers touch the Flask session, so they need a request context.
    with dolma_app.app.test_request_context("/api/chat"):
        result = agent.run(
            client=client,
            model="fake-model",
            messages=messages,
            tools=agent_tools,
            dispatch=make_dispatcher(ctx),
            max_steps=max_steps,
        )
    return result, messages, client


def test_tool_result_is_fed_back_as_an_observation():
    with stubbed_weather():
        result, messages, client = run_loop([
            Msg("let me check the forecast", [Call("get_weather")]),
            Msg("It is 19C and raining in Sydney."),
        ])

    observations = tool_messages(messages)
    assert len(observations) == 1
    # The model saw the real number, not a summary we wrote for it.
    assert observations[0]["temperature_c"] == 19

    # The assistant turn that requested the tool must be in the transcript too,
    # or the API rejects the follow-up request.
    assert any(m.get("role") == "assistant" and m.get("tool_calls") for m in messages)

    # Two round trips: one to act, one to answer having observed.
    assert len(client.seen) == 2
    assert any(m.get("role") == "tool" for m in client.seen[1]["messages"])

    # The user-facing words come from the model, not from the handler.
    assert result.reply == "It is 19C and raining in Sydney."


def test_reasoning_and_ui_payload_are_recorded():
    with stubbed_weather():
        result, _, _ = run_loop([
            Msg("let me check the forecast", [Call("get_weather")]),
            Msg("Rainy."),
        ])

    assert result.trace[0]["tool"] == "get_weather"
    assert result.trace[0]["thought"] == "let me check the forecast"
    # The weather card travels beside the reply, never through the model.
    assert result.ui["place_name"] == "Sydney, NSW"


def test_model_can_act_again_after_observing():
    with stubbed_weather():
        result, messages, client = run_loop([
            Msg(None, [Call("get_weather")]),
            Msg(None, [Call("get_weather")]),
            Msg("Checked twice, still raining."),
        ])

    assert len(tool_messages(messages)) == 2
    assert len(client.seen) == 3
    assert result.stop_reason == "answered"


def test_removed_goal_tools_are_gone():
    assert not any("goal" in t["function"]["name"] for t in agent_tools)


def test_calling_an_unknown_tool_is_an_observation():
    _, messages, _ = run_loop([
        Msg(None, [Call("list_goals")]),
        Msg("I can't track goals."),
    ])
    assert "Unknown tool" in tool_messages(messages)[0]["error"]


def test_a_handler_that_raises_does_not_fail_the_request():
    def explode(args, ctx):
        raise RuntimeError("provider exploded")

    original = tool_handlers.HANDLERS["get_weather"]
    tool_handlers.HANDLERS["get_weather"] = explode
    try:
        result, messages, _ = run_loop([
            Msg(None, [Call("get_weather")]),
            Msg("Sorry, the weather service is down."),
        ])
    finally:
        tool_handlers.HANDLERS["get_weather"] = original

    assert "provider exploded" in tool_messages(messages)[0]["error"]
    assert result.reply  # the user still gets an answer


def test_malformed_tool_arguments_are_recoverable():
    bad = Call("get_weather")
    bad.function.arguments = "{not json"
    _, messages, _ = run_loop([Msg(None, [bad]), Msg("Let me try that again.")])
    assert "Could not parse" in tool_messages(messages)[0]["error"]


def test_runaway_loop_is_capped_but_still_answers():
    with stubbed_weather():
        result, _, client = run_loop([Msg(None, [Call("get_weather")]) for _ in range(4)])

    assert result.stop_reason == "max_steps"
    # The forced final request must offer no tools, or it could loop forever.
    assert "tools" not in client.seen[-1]
    assert result.reply


def test_weather_without_a_location_is_an_observation():
    _, messages, _ = run_loop(
        [Msg(None, [Call("get_weather")]), Msg("Please enable location access.")],
        ctx=ToolContext(),
    )
    assert tool_messages(messages)[0]["status"] == "location_unavailable"
