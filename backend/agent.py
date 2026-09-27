"""
The ReAct loop that drives DOLMA.

Reason -> Act -> Observe, repeated until the model answers without asking for a
tool:

    1. send the conversation (plus the tool schemas) to the model
    2. if it replies with tool calls, run every one of them
    3. append each result as a `role: "tool"` message so the model can *observe*
       what actually happened
    4. go back to 1, so the model can chain another tool or write its answer

This module knows nothing about calendars or weather: it takes a
`dispatch` callable and just runs the loop. The domain logic lives in
tool_handlers.py.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

# Generous enough for find_events -> update_event -> find_events style chains,
# low enough that a confused model cannot bill the user for an infinite loop.
DEFAULT_MAX_STEPS = 6

# How much of an observation we keep in the returned trace (the full value still
# goes to the model; this is only for the debug panel / report screenshots).
TRACE_OBSERVATION_CHARS = 400


@dataclass
class ToolResult:
    """What a tool handler hands back to the loop."""

    # Fed to the model as the tool message. Anything JSON-serialisable.
    observation: Any
    # Extra fields merged into the HTTP response for the frontend to render
    # (weather card, confirmation chips...). Never shown to the model.
    ui: Optional[Dict[str, Any]] = None
    # True when the tool only produced a preview and is waiting for the user to
    # approve. The dispatcher uses this to refuse a confirm in the same turn.
    awaiting_confirmation: bool = False


@dataclass
class AgentRun:
    reply: str = ""
    ui: Dict[str, Any] = field(default_factory=dict)
    trace: List[Dict[str, Any]] = field(default_factory=list)
    steps: int = 0
    stop_reason: str = "answered"


def _assistant_turn(msg, calls) -> Dict[str, Any]:
    """
    Rebuild the assistant message as a plain dict.

    We construct it by hand rather than using model_dump(): the SDK object also
    carries fields like `refusal` and `annotations` that the API rejects when
    they are echoed back.
    """
    return {
        "role": "assistant",
        "content": msg.content or "",
        "tool_calls": [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.function.name,
                    "arguments": call.function.arguments or "{}",
                },
            }
            for call in calls
        ],
    }


def _as_tool_message(call_id: str, observation: Any) -> Dict[str, Any]:
    if isinstance(observation, str):
        content = observation
    else:
        content = json.dumps(observation, ensure_ascii=False, default=str)
    return {"role": "tool", "tool_call_id": call_id, "content": content}


def _trim(value: Any) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    if len(text) > TRACE_OBSERVATION_CHARS:
        return text[:TRACE_OBSERVATION_CHARS] + "…"
    return text


def run(
    *,
    client,
    model: str,
    messages: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
    dispatch: Callable[[str, Dict[str, Any]], ToolResult],
    max_steps: int = DEFAULT_MAX_STEPS,
    max_tokens: int = 800,
) -> AgentRun:
    """
    Run the reason/act/observe loop until the model answers in plain text.

    `messages` is mutated in place, so the caller can inspect the full transcript
    (including tool messages) afterwards.
    """
    run_state = AgentRun()

    for step in range(1, max_steps + 1):
        run_state.steps = step
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_completion_tokens=max_tokens,
        )
        msg = response.choices[0].message
        calls = list(getattr(msg, "tool_calls", None) or [])

        if not calls:
            # No action requested: this is the answer.
            run_state.reply = _finalize(
                client=client,
                model=model,
                messages=messages,
                text=(msg.content or "").strip(),
                max_tokens=max_tokens,
            )
            run_state.stop_reason = "answered"
            return run_state

        # Record the reasoning that came alongside the tool calls, if any.
        thought = (msg.content or "").strip() or None
        messages.append(_assistant_turn(msg, calls))

        # Every tool_call MUST get a matching tool message or the next request
        # is rejected, so nothing in this block may bail out early.
        for call in calls:
            name = call.function.name
            raw_args = call.function.arguments or "{}"
            try:
                args = json.loads(raw_args)
                if not isinstance(args, dict):
                    raise ValueError("arguments must be a JSON object")
            except Exception as exc:
                args = {}
                result = ToolResult(
                    observation={
                        "error": f"Could not parse the arguments you sent ({exc}). "
                        "Call the tool again with valid JSON."
                    }
                )
            else:
                try:
                    result = dispatch(name, args)
                except Exception as exc:  # a tool blowing up is an observation, not a 500
                    print(f"[agent] tool {name} raised: {exc}")
                    result = ToolResult(
                        observation={
                            "error": f"{name} failed: {exc}",
                            "hint": "Tell the user plainly that this step did not work.",
                        }
                    )

            messages.append(_as_tool_message(call.id, result.observation))
            if result.ui:
                run_state.ui.update(result.ui)
            run_state.trace.append(
                {
                    "step": step,
                    "thought": thought,
                    "tool": name,
                    "args": args,
                    "observation": _trim(result.observation),
                }
            )
            thought = None  # only attach it to the first call of the turn

    # Ran out of steps: ask once more with no tools so the user still gets words.
    run_state.stop_reason = "max_steps"
    messages.append(
        {
            "role": "system",
            "content": (
                "You have reached the tool-call limit for this turn. Answer the user "
                "now in plain language using what you already observed, and say what "
                "is still missing if the task is unfinished."
            ),
        }
    )
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_completion_tokens=max_tokens,
    )
    run_state.reply = _finalize(
        client=client,
        model=model,
        messages=messages,
        text=(response.choices[0].message.content or "").strip(),
        max_tokens=max_tokens,
    )
    return run_state


def _finalize(*, client, model, messages, text: str, max_tokens: int) -> str:
    """Nudge the model once if it answered with nothing useful."""
    if text and text not in ("...", "…", "Ok", "Okay"):
        return text
    retry = client.chat.completions.create(
        model=model,
        messages=messages + [{"role": "user", "content": "Please elaborate."}],
        max_completion_tokens=max_tokens,
    )
    return (retry.choices[0].message.content or "").strip()
