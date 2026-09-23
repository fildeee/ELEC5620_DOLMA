"""
The agent's hands.

Every handler takes the arguments the model produced and returns a ToolResult
whose `observation` goes straight back into the conversation as a
`role: "tool"` message. Handlers therefore never build HTTP responses and never
decide what the user gets told -- they report what happened and let the model
narrate it on the next pass of the loop.

Anything the browser needs to *render* (the weather card, the confirmation
chips) travels separately in `ui`, which the model never sees.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from flask import session

from agent import ToolResult
from formatting import (
    _fmt,
    _fmt_date_only,
    _fmt_time_range,
    _to_sydney_datetime,
    describe_event,
    resolve_window,
    to_sydney_wall_clock,
)
from google_calendar import (
    create_calendar_event,
    delete_calendar_event,
    find_events,
    is_connected,
    update_calendar_event,
)
from places import CATEGORY_TAGS, find_nearby
from weather import current_conditions, ip_to_location

# Tools that are useless without an authorised Google account.
CALENDAR_TOOLS = {"create_event", "find_events", "update_event", "delete_event"}

# Tools that change something and therefore go through preview -> confirm.
WRITE_TOOLS = {"create_event", "update_event", "delete_event"}

# How far either side of today we look when the model names no window.
DEFAULT_SEARCH_SPAN_DAYS = 30


@dataclass
class ToolContext:
    """Per-request state the handlers need but the model should not have to pass."""

    lat: Optional[float] = None
    lon: Optional[float] = None
    client_ip: Optional[str] = None
    # Write tools that have shown a preview during *this* HTTP request.
    awaiting_confirmation: Set[str] = field(default_factory=set)


def _confirmation(
    action: str,
    preview: List[str],
    *,
    note: Optional[str] = None,
    ui: Optional[Dict[str, Any]] = None,
    details_in_card: bool = False,
    extra: Optional[Dict[str, Any]] = None,
) -> ToolResult:
    """Build the 'previewed, nothing written yet' observation."""
    instruction = (
        "NOTHING HAS BEEN CHANGED YET. Relay this preview to the user and ask for "
        "explicit approval. Do not call this tool with confirm=true until the user "
        "agrees in a later message — end your turn here."
    )
    if details_in_card:
        instruction += (
            " The details are already shown to the user in a card beneath your "
            "message, so ask in one short sentence rather than repeating every field."
        )
    observation: Dict[str, Any] = {
        "status": "awaiting_confirmation",
        "action": action,
        "preview": preview,
        "instruction": instruction,
    }
    if note:
        observation["note"] = note
    if extra:
        observation.update(extra)
    return ToolResult(observation=observation, ui=ui, awaiting_confirmation=True)


def _needs(message: str, **extra: Any) -> ToolResult:
    """Observation for 'you did not give me enough to work with'."""
    return ToolResult(observation={"status": "missing_input", "message": message, **extra})


def _match_titles(events: List[dict], query: str) -> List[dict]:
    parts = [
        q.strip()
        for q in query.lower().replace(" and ", ",").replace("&", ",").split(",")
        if q.strip()
    ]
    if not parts:
        return []
    return [ev for ev in events if any(p in (ev.get("summary") or "").lower() for p in parts)]


# --------------------------------------------------------------------------- #
# weather
# --------------------------------------------------------------------------- #

def _resolve_location(ctx: ToolContext):
    """The granted browser position, falling back to a rough IP estimate."""
    if ctx.lat is not None and ctx.lon is not None:
        return ctx.lat, ctx.lon
    if ctx.client_ip:
        approx = ip_to_location(ctx.client_ip)
        if approx:
            return approx
    return None, None


def _location_unavailable() -> ToolResult:
    return ToolResult(
        observation={
            "status": "location_unavailable",
            "message": "No location available: the browser did not grant geolocation "
            "and the IP lookup failed.",
            "instruction": "Ask the user to enable location access, or to tell you their city. "
            "Do not guess where they are.",
        }
    )


def handle_get_weather(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    lat, lon = _resolve_location(ctx)
    if lat is None or lon is None:
        return _location_unavailable()

    conditions = current_conditions(lat, lon)
    if not conditions:
        return ToolResult(
            observation={"error": "Both weather providers failed to respond."}
        )

    return ToolResult(
        observation={
            "place": conditions["place_name"],
            "temperature_c": conditions["temp"],
            "feels_like_c": conditions["feels"],
            "humidity_pct": conditions["humidity"],
            "wind_ms": conditions["wind"],
            "conditions": conditions["cond"],
            "tips": conditions["tips"],
        },
        ui={
            "tips": conditions["tips"],
            "place_name": conditions["place_name"],
            "weather": {
                "temp": conditions["temp"],
                "feels": conditions["feels"],
                "humidity": conditions["humidity"],
                "wind": conditions["wind"],
                "cond": conditions["cond"],
            },
        },
    )


def handle_find_places(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    lat, lon = _resolve_location(ctx)
    if lat is None or lon is None:
        return _location_unavailable()

    category = (args.get("category") or "").strip().lower()
    try:
        places = find_nearby(
            category,
            lat,
            lon,
            radius_m=args.get("radius_m"),
            limit=args.get("limit"),
            keyword=(args.get("keyword") or "").strip() or None,
        )
    except ValueError as exc:
        return _needs(str(exc), available_categories=sorted(CATEGORY_TAGS))
    except RuntimeError as exc:
        return ToolResult(observation={"error": str(exc)})

    if not places:
        return ToolResult(
            observation={
                "status": "no_results",
                "category": category,
                "message": f"No {category} found within {args.get('radius_m') or 1500} m.",
                "instruction": "Offer to search a wider radius rather than naming places "
                "from your own knowledge.",
            }
        )

    return ToolResult(
        observation={
            "category": category,
            "count": len(places),
            "places": places,
            "source": "OpenStreetMap",
            "instruction": "Report only these places — naming one this list does not "
            "contain would be an invention. A null address, opening_hours or website means "
            "OpenStreetMap does not record it — say it is not listed rather than supplying "
            "one. Every name, distance, address and opening time is already displayed to "
            "the user in a card below your message, so your reply must name at most TWO of "
            "these places — the nearest, or whichever best fits what they asked — in one or "
            "two sentences, then tell them the rest are in the list below. Writing them all "
            "out only duplicates the card. Do not use markdown links.",
        },
        ui={"places": places, "places_category": category},
    )


# --------------------------------------------------------------------------- #
# calendar
# --------------------------------------------------------------------------- #

def handle_find_events(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    try:
        start, end, label = resolve_window(
            args.get("preset"), args.get("time_min"), args.get("time_max")
        )
    except ValueError as exc:
        return _needs(str(exc))

    items = find_events(start, end, max_results=args.get("max_results") or 50)
    compact = [
        {
            "id": ev.get("id"),
            "title": ev.get("summary") or "(no title)",
            "start": (ev.get("start") or {}).get("dateTime") or (ev.get("start") or {}).get("date"),
            "end": (ev.get("end") or {}).get("dateTime") or (ev.get("end") or {}).get("date"),
            "location": ev.get("location") or "",
            "summary_line": describe_event(ev),
        }
        for ev in items
    ]
    return ToolResult(
        observation={"window": label, "count": len(compact), "events": compact},
        ui={"events": compact},
    )


def _clashes_with(start_iso: str, end_iso: str) -> List[str]:
    """
    Events already on the calendar that genuinely overlap this one.

    Worked out here rather than left to the model. Asked to compare a lunch at
    11:45 against a tutorial ending at 11:45 it reported a clash, then refused to
    book at all; no wording of the rule in the prompt reliably stopped it, because
    the comparison is arithmetic and that is not what a language model is for.
    Touching at the boundary is not an overlap — hence strict inequality on both
    sides — and the model is told to trust this list over its own reading.
    """
    start = datetime.fromisoformat(start_iso)
    end = datetime.fromisoformat(end_iso)
    day_start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = end.replace(hour=23, minute=59, second=59, microsecond=999000)

    found = []
    for ev in find_events(day_start, day_end, max_results=100):
        ev_start = (ev.get("start") or {}).get("dateTime")
        ev_end = (ev.get("end") or {}).get("dateTime")
        if not ev_start or not ev_end:
            continue  # an all-day event has a date but no time to compare
        try:
            other_start = datetime.fromisoformat(ev_start.replace("Z", "+00:00"))
            other_end = datetime.fromisoformat(ev_end.replace("Z", "+00:00"))
        except ValueError:
            continue
        if other_start < end and other_end > start:
            found.append(describe_event(ev))
    return found


def handle_create_event(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    batch = args.get("events")
    if batch and not isinstance(batch, list):
        batch = [batch]
    if not batch and any(args.get(k) for k in ("summary", "start_time", "end_time")):
        batch = [args]

    confirmed = bool(args.get("confirm"))

    if not batch and confirmed:
        # The model confirmed without resending the events; fall back to the
        # batch stashed when we previewed it.
        batch = session.get("pending_creates") or []

    if not batch:
        return _needs("No events supplied. Send an `events` array.")

    missing = [
        i
        for i, ev in enumerate(batch, start=1)
        if not all(isinstance(ev, dict) and ev.get(k) for k in ("summary", "start_time", "end_time"))
    ]
    if missing:
        return _needs(
            "Every event needs summary, start_time and end_time, as Sydney local "
            f"time, e.g. 2025-11-22T14:00:00. Incomplete: event(s) {missing}."
        )

    # Pin the times to Sydney before anything reads them, so the preview the user
    # approves and the event finally written are the same moment.
    try:
        for ev in batch:
            ev["start_time"] = to_sydney_wall_clock(ev["start_time"])
            ev["end_time"] = to_sydney_wall_clock(ev["end_time"])
    except Exception as exc:
        return _needs(
            f"Could not read those datetimes ({exc}). Give the Sydney local time, "
            "e.g. 2025-11-22T14:00:00."
        )

    lines = [
        f"{i}. {ev['summary']} — {_fmt_date_only(ev['start_time'])}, "
        f"{_fmt_time_range(ev['start_time'], ev['end_time'])}"
        for i, ev in enumerate(batch, start=1)
    ]

    if not confirmed:
        session["pending_creates"] = batch
        ui = None
        if len(batch) == 1:
            ev = batch[0]
            ui = {
                "items": [
                    {"label": "title", "value": ev.get("summary") or "(no title)"},
                    {"label": "date", "value": _fmt_date_only(ev["start_time"])},
                    {"label": "time", "value": _fmt_time_range(ev["start_time"], ev["end_time"])},
                ],
                "cta": "add this now?",
            }
        extra: Dict[str, Any] = {}
        try:
            clashes = []
            for ev in batch:
                clashes.extend(_clashes_with(ev["start_time"], ev["end_time"]))
            extra["clashes"] = clashes
            extra["clash_check"] = (
                "Computed from the calendar, not estimated. An event appears here "
                "only if it truly overlaps; one that ends exactly when this begins "
                "does not. Trust this over your own reading of the times: if the "
                "list is empty the slot is free and you should say so, and if it is "
                "not, name what is in it. Either way still offer to add the event — "
                "a clash is for the user to weigh, not a reason to refuse."
            )
        except Exception as exc:
            extra["clash_check"] = (
                f"Could not check the calendar for clashes ({exc}). Say the preview "
                "stands but that you could not confirm the slot is free."
            )

        return _confirmation(
            "create_event", lines, ui=ui, details_in_card=bool(ui), extra=extra
        )

    created, failed = [], []
    for ev in batch:
        try:
            start_dt = datetime.fromisoformat(ev["start_time"].replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(ev["end_time"].replace("Z", "+00:00"))
            saved = create_calendar_event(
                summary=ev["summary"],
                description=ev.get("description", ""),
                start_time=start_dt,
                end_time=end_dt,
                location=ev.get("location"),
                attendees=ev.get("attendees"),
                recurrence=ev.get("recurrence"),
                reminders=ev.get("reminders"),
            )
            created.append({"id": saved.get("id"), "title": saved.get("summary") or "(no title)"})
        except Exception as exc:
            failed.append({"title": ev.get("summary"), "error": str(exc)})

    session.pop("pending_creates", None)
    return ToolResult(
        observation={"status": "created" if not failed else "partial", "created": created, "failed": failed}
    )


def handle_delete_event(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    query = (args.get("query") or "").strip()
    if not query:
        return _needs("I need a title keyword to know which event(s) to delete.")

    try:
        start, end, label = resolve_window(
            args.get("preset"),
            args.get("time_min"),
            args.get("time_max"),
            default_span_days=DEFAULT_SEARCH_SPAN_DAYS,
        )
    except ValueError as exc:
        return _needs(str(exc))

    matches = _match_titles(find_events(start, end, max_results=100), query)
    if not matches:
        return ToolResult(
            observation={
                "status": "no_match",
                "query": query,
                "window": label,
                "message": f"No events matching '{query}' in {label}.",
            }
        )

    wanted_ids = args.get("event_ids") or []
    if wanted_ids:
        matches = [ev for ev in matches if ev.get("id") in wanted_ids]
        if not matches:
            return ToolResult(
                observation={"status": "no_match", "message": "None of those event_ids are in this window."}
            )

    if not bool(args.get("confirm")):
        shown = matches[:10]
        return _confirmation(
            "delete_event",
            [f"{i}. {describe_event(ev)}" for i, ev in enumerate(shown, start=1)],
            note=f"{len(matches)} event(s) matched '{query}' in {label}. Deletion cannot be undone.",
            ui={"cta": "delete now?"},
            extra={"event_ids": [ev.get("id") for ev in shown]},
        )

    deleted, failed = [], []
    for ev in matches:
        try:
            delete_calendar_event(ev["id"])
            deleted.append(ev.get("summary") or "(no title)")
        except Exception as exc:
            failed.append({"title": ev.get("summary"), "error": str(exc)})

    return ToolResult(
        observation={
            "status": "deleted" if not failed else "partial",
            "deleted_count": len(deleted),
            "deleted": deleted,
            "failed": failed,
        }
    )


def handle_update_event(args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    query = (args.get("query") or "").strip()
    if not query:
        return _needs("I need a title keyword to know which event(s) to update.")

    updates = {
        field_name: args[field_name]
        for field_name in ("summary", "description", "location", "start_time", "end_time")
        if args.get(field_name)
    }
    if not updates:
        return _needs(
            "Nothing to change. Provide at least one of summary, description, "
            "location, start_time or end_time."
        )

    # As in handle_create_event: the wall clock is what the user asked for, so
    # read it as Sydney rather than trusting the offset the model attached.
    try:
        for field_name in ("start_time", "end_time"):
            if field_name in updates:
                updates[field_name] = to_sydney_wall_clock(updates[field_name])
    except Exception as exc:
        return _needs(
            f"Could not read that datetime ({exc}). Give the Sydney local time, "
            "e.g. 2025-11-22T14:00:00."
        )

    try:
        start, end, label = resolve_window(
            args.get("preset"),
            args.get("time_min"),
            args.get("time_max"),
            default_span_days=DEFAULT_SEARCH_SPAN_DAYS,
        )
    except ValueError as exc:
        return _needs(str(exc))

    matches = _match_titles(find_events(start, end, max_results=100), query)
    if not matches:
        return ToolResult(
            observation={
                "status": "no_match",
                "query": query,
                "window": label,
                "message": f"No events matching '{query}' in {label}.",
            }
        )

    wanted_ids = args.get("event_ids") or []
    if wanted_ids:
        matches = [ev for ev in matches if ev.get("id") in wanted_ids]
        if not matches:
            return ToolResult(
                observation={"status": "no_match", "message": "None of those event_ids are in this window."}
            )

    change_desc = ", ".join(
        f"{k} → {_fmt(v) if k in ('start_time', 'end_time') and 'T' in str(v) else v}"
        for k, v in updates.items()
    )

    if not bool(args.get("confirm")):
        shown = matches[:10]
        return _confirmation(
            "update_event",
            [f"{i}. {describe_event(ev)}" for i, ev in enumerate(shown, start=1)],
            note=f"Proposed change: {change_desc}",
            ui={"cta": "apply now?"},
            extra={"event_ids": [ev.get("id") for ev in shown]},
        )

    updated, failed = [], []
    clean = {
        k: (_to_sydney_datetime(v) if k in ("start_time", "end_time") else v)
        for k, v in updates.items()
    }
    for ev in matches:
        try:
            update_calendar_event(ev["id"], **clean)
            updated.append(ev.get("summary") or "(no title)")
        except Exception as exc:
            failed.append({"title": ev.get("summary"), "error": str(exc)})

    return ToolResult(
        observation={
            "status": "updated" if not failed else "partial",
            "updated_count": len(updated),
            "updated": updated,
            "changes": change_desc,
            "failed": failed,
        }
    )


HANDLERS = {
    "get_weather": handle_get_weather,
    "find_places": handle_find_places,
    "find_events": handle_find_events,
    "create_event": handle_create_event,
    "update_event": handle_update_event,
    "delete_event": handle_delete_event,
}


def make_dispatcher(ctx: ToolContext):
    """
    Build the callable the ReAct loop uses to act.

    It owns the two rules that must not be left to the prompt: calendar tools
    need a connected account, and a write cannot be confirmed in the same turn
    that previewed it (the user has not spoken since).
    """

    def dispatch(name: str, args: Dict[str, Any]) -> ToolResult:
        handler = HANDLERS.get(name)
        if handler is None:
            return ToolResult(
                observation={
                    "error": f"Unknown tool '{name}'.",
                    "available": sorted(HANDLERS),
                }
            )

        if name in CALENDAR_TOOLS and not is_connected():
            return ToolResult(
                observation={
                    "status": "calendar_not_connected",
                    "message": "Google Calendar is not connected for this user.",
                    "instruction": "Tell the user to connect Google Calendar in Settings, "
                    "then stop — do not retry this tool.",
                }
            )

        if name in WRITE_TOOLS and bool(args.get("confirm")) and name in ctx.awaiting_confirmation:
            return ToolResult(
                observation={
                    "status": "not_confirmed",
                    "message": "You previewed this in the current turn and the user has not "
                    "replied yet, so confirm=true was refused.",
                    "instruction": "End your turn and wait for the user to approve.",
                }
            )

        result = handler(args, ctx)
        if result.awaiting_confirmation:
            ctx.awaiting_confirmation.add(name)
        return result

    return dispatch
