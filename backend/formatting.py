"""
Date, time and number formatting shared by the Flask routes and the agent tools.

These used to live in app.py, but the tool handlers need them too and importing
them from app.py would be circular (app.py imports the handlers).
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

SYDNEY = "Australia/Sydney"

# Presets the calendar tools accept in place of an explicit time_min/time_max.
WINDOW_PRESETS = ("today", "tomorrow", "this_week", "next_week")


# function to format current datetime in Sydney timezone
def _current_sydney_datetime() -> datetime:
    if ZoneInfo:
        try:
            return datetime.now(ZoneInfo(SYDNEY))
        except Exception:
            pass
    return datetime.now()


# formats date for Sydney
def _fmt_date_only(dt_iso: str) -> str:
    tz = ZoneInfo(SYDNEY)
    dt = datetime.fromisoformat(dt_iso.replace("Z", "+00:00")).astimezone(tz)
    return dt.strftime("%A, %d %B %Y")


# format time for Sydney
def _fmt_time_range(start_iso: str, end_iso: str) -> str:
    tz = ZoneInfo(SYDNEY)
    s = datetime.fromisoformat(start_iso.replace("Z", "+00:00")).astimezone(tz)
    e = datetime.fromisoformat(end_iso.replace("Z", "+00:00")).astimezone(tz)
    # remove leading zero from hour
    st = s.strftime("%I:%M %p").lstrip("0")
    et = e.strftime("%I:%M %p").lstrip("0")
    return f"{st} – {et}"


# converts ISO 8601 string to a short human-readable datetime in Sydney
def _fmt(dt_iso: str) -> str:
    tz = ZoneInfo(SYDNEY)
    dt = datetime.fromisoformat(dt_iso.replace("Z", "+00:00")).astimezone(tz)
    # example: 'Mon, 3 Nov 2:00 PM'
    # Built by hand because the no-pad flags (%-d/%-I) are glibc-only and raise
    # ValueError on Windows.
    hour12 = dt.hour % 12 or 12
    return (
        f"{dt.strftime('%a')}, {dt.day} {dt.strftime('%b')} "
        f"{hour12}:{dt.strftime('%M %p')}"
    )


def to_sydney_wall_clock(dt_iso: str) -> str:
    """
    Read a datetime as Sydney local time, whatever offset it arrived with.

    The model writes these, and a language model cannot be trusted to know
    whether a date falls inside Australian daylight saving. Asked for 11:45 on a
    morning in September it produced `2026-09-24T11:45:00+11:00` — Sydney is
    +10:00 until October, so that is 10:45 local, an hour before the user said,
    and the hour was lost silently because the string was well-formed RFC3339.

    The wall clock is the part the user actually spoke, so keep it and let
    zoneinfo supply the offset, which it gets right on both sides of a
    transition. Any offset already on the string is discarded: this assistant
    schedules in Sydney and nowhere else, so a time from the model is a Sydney
    time by definition.
    """
    dt = datetime.fromisoformat(dt_iso.replace("Z", "+00:00"))
    return dt.replace(tzinfo=ZoneInfo(SYDNEY)).isoformat()


# converts ISO 8601 string to tz-aware datetime for Google Calendar updates.
def _to_sydney_datetime(dt_iso: str):
    tz = ZoneInfo(SYDNEY)
    if isinstance(dt_iso, str) and "T" in dt_iso:
        return datetime.fromisoformat(dt_iso.replace("Z", "+00:00")).astimezone(tz)
    return dt_iso  # return as-is if already datetime


def describe_event(ev: dict) -> str:
    """One-line human summary of a Google Calendar event, used in previews."""
    title = ev.get("summary") or "(no title)"
    start = (ev.get("start") or {}).get("dateTime") or (ev.get("start") or {}).get("date")
    end = (ev.get("end") or {}).get("dateTime") or (ev.get("end") or {}).get("date")
    try:
        if start and end and "T" in start and "T" in end:
            return f"{title} — {_fmt_date_only(start)}, {_fmt_time_range(start, end)}"
        if start:
            return f"{title} — {_fmt_date_only(start)} (all day)"
    except Exception:
        pass
    return title


def resolve_window(
    preset: Optional[str],
    time_min: Optional[str],
    time_max: Optional[str],
    default_span_days: Optional[int] = None,
) -> Tuple[datetime, datetime, str]:
    """
    Turn a preset (or an explicit RFC3339 range) into a concrete Sydney-local
    window plus a human-readable label.

    The three calendar tools each open-coded this; sharing it keeps 'this_week'
    meaning the same thing whether you are listing, updating or deleting.
    Raises ValueError when there is nothing usable to work with and no default
    span was supplied.
    """
    tz = ZoneInfo(SYDNEY)
    now = _current_sydney_datetime().astimezone(tz)
    preset = (preset or "").strip().lower()

    def day_bounds(day: datetime) -> Tuple[datetime, datetime]:
        start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        end = day.replace(hour=23, minute=59, second=59, microsecond=999000)
        return start, end

    if preset:
        if preset == "today":
            start, end = day_bounds(now)
        elif preset == "tomorrow":
            start, end = day_bounds(now + timedelta(days=1))
        elif preset in ("this_week", "next_week"):
            offset = 7 if preset == "next_week" else 0
            monday = (now - timedelta(days=now.weekday()) + timedelta(days=offset)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            start = monday
            end = (monday + timedelta(days=6)).replace(
                hour=23, minute=59, second=59, microsecond=999000
            )
        else:
            raise ValueError(
                f"Unknown preset '{preset}'. Use one of: {', '.join(WINDOW_PRESETS)}."
            )
    elif time_min and time_max:
        start = datetime.fromisoformat(time_min.replace("Z", "+00:00"))
        end = datetime.fromisoformat(time_max.replace("Z", "+00:00"))
    elif default_span_days is not None:
        start = now - timedelta(days=default_span_days)
        end = now + timedelta(days=default_span_days)
    else:
        raise ValueError(
            "Provide either a preset (today/tomorrow/this_week/next_week) "
            "or both time_min and time_max."
        )

    if start.date() == end.date():
        label = _fmt_date_only(start.isoformat())
    else:
        label = f"{_fmt_date_only(start.isoformat())} → {_fmt_date_only(end.isoformat())}"
    return start, end, label
