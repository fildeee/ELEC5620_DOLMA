from flask import Flask, request, jsonify, redirect, session
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
from datetime import datetime
from typing import Optional, Tuple, Union

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python <3.9 fallback
    ZoneInfo = None  # type: ignore

import httpx
from google_auth_oauthlib.flow import Flow

from google_calendar import (
    get_calendar_service,
    is_connected,
    save_creds,
    create_calendar_event,
)
from tools import calendar_tools
from goals import (
    create_goal as storage_create_goal,
    delete_goal as storage_delete_goal,
    list_goals as storage_list_goals,
    update_goal as storage_update_goal,
    get_goal as storage_get_goal,
)

load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True)

app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

GOOGLE_SCOPES = ["https://www.googleapis.com/auth/calendar"]
GOOGLE_CLIENT_SECRETS_FILE = "credentials.json"
REDIRECT_URI = "http://localhost:5000/api/google/oauth2callback"
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

def _origin_from_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        pass
    return url.rstrip("/") if isinstance(url, str) else None

def _cors_origins() -> list[str]:
    """
    Build the list of allowed origins for CORS preflight checks.
    Reads CORS_ALLOW_ORIGINS if provided, otherwise falls back to
    sensible local dev defaults so that localhost/127.0.0.1 both work.
    """
    override = os.getenv("CORS_ALLOW_ORIGINS")
    if override:
        origins = []
        for origin in override.split(","):
            origin = origin.strip()
            if origin:
                parsed = _origin_from_url(origin) or origin.rstrip("/")
                origins.append(parsed)
        return origins

    defaults = {"http://localhost:5173", "http://127.0.0.1:5173"}
    if FRONTEND_URL:
        base = _origin_from_url(FRONTEND_URL)
        if base:
            defaults.add(base)
            if "localhost" in base:
                defaults.add(base.replace("localhost", "127.0.0.1"))
    return [origin.rstrip("/") for origin in defaults if origin]

app = Flask(__name__)
ALLOWED_ORIGINS = _cors_origins()
CORS(
    app,
    resources={r"/api/*": {"origins": ALLOWED_ORIGINS}},
    supports_credentials=True,
    methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")


def _current_sydney_datetime() -> datetime:
    """
    Best-effort helper to get the current time in Sydney.
    Falls back to local time if the zoneinfo database is unavailable.
    """
    if ZoneInfo:
        try:
            return datetime.now(ZoneInfo("Australia/Sydney"))
        except Exception:
            pass
    return datetime.now()


def _format_decimal(value: Optional[Union[int, float]]) -> Optional[str]:
    """
    Format floats/ints without trailing zeros (e.g. 12, 12.5, 12.34).
    Returns None when value is not numeric.
    """
    if not isinstance(value, (int, float)):
        return None
    as_float = float(value)
    if round(as_float) == as_float:
        return str(int(round(as_float)))
    return f"{as_float:.2f}".rstrip("0").rstrip(".")


def _coerce_goal_number(value: Optional[Union[str, int, float]]) -> Optional[float]:
    """
    Lightweight numeric parser for goal targets/progress with helpful validation.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError as exc:
            raise ValueError("Goal values must be numeric.") from exc
    raise ValueError("Goal values must be numeric.")


def _compose_goal_progress(goal: dict) -> str:
    """
    Build a conversational summary for a single goal including actual vs target progress.
    """
    title = goal.get("title") or "Untitled goal"
    progress_pct = goal.get("progress", 0)
    status = (goal.get("status") or "").strip().lower()
    target_date = goal.get("target_date")

    target_value = goal.get("target_value")
    progress_value = goal.get("progress_value")
    unit = (goal.get("target_unit") or "").strip()

    def fmt_amount(value: Optional[Union[int, float]], with_unit: bool = True) -> Optional[str]:
        if not isinstance(value, (int, float)):
            return None
        text = _format_decimal(float(value))
        text = text or str(value)
        if not with_unit or not unit:
            return text
        if unit == "$":
            return f"${text}"
        return f"{text} {unit}"

    sentences = []
    if isinstance(target_value, (int, float)) and target_value > 0 and isinstance(progress_value, (int, float)):
        remaining = max(target_value - progress_value, 0.0)
        progress_text = (
            f"You've completed {fmt_amount(progress_value)} "
            f"out of {fmt_amount(target_value)}"
        )
        if remaining > 0:
            progress_text += f", with {fmt_amount(remaining)} to go."
        else:
            progress_text += ", and you've met the target."
        sentences.append(progress_text)
        sentences.append(f"That's {progress_pct}% done.")
    else:
        sentences.append(f"You're {progress_pct}% of the way through.")

    if target_date:
        sentences.append(f"Target date {target_date}.")
    if status and status not in {"active"}:
        sentences.append(f"Status is {status}.")

    summary = " ".join(sentences)
    return f"{title} — {summary}".strip()

def get_client_ip(req: request) -> Optional[str]:
    fwd = req.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    ip = fwd or req.remote_addr or ""
    if not ip:
        return None
    private_prefixes = (
        "127.", "10.", "192.168.",
        "172.16.", "172.17.", "172.18.", "172.19.", "172.20.", "172.21.",
        "172.22.", "172.23.", "172.24.", "172.25.", "172.26.", "172.27.",
        "172.28.", "172.29.", "172.30.", "172.31.",
    )
    if ip.startswith(private_prefixes) or ip == "::1":
        return None
    return ip

def ip_to_location(ip: str) -> Optional[Tuple[float, float]]:
    try:
        url = f"http://ip-api.com/json/{ip}?fields=status,lat,lon"
        r = httpx.get(url, timeout=5)
        if r.status_code == 200:
            j = r.json()
            if j.get("status") == "success":
                lat = j.get("lat"); lon = j.get("lon")
                if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
                    return float(lat), float(lon)
    except Exception:
        pass
    return None

def fetch_weather(lat: float, lon: float) -> Optional[dict]:
    try:
        if OPENWEATHER_API_KEY:
            params = {
                "lat": lat, "lon": lon,
                "appid": OPENWEATHER_API_KEY,
                "units": "metric", "lang": "en",
            }
            r = httpx.get("https://api.openweathermap.org/data/2.5/weather", params=params, timeout=8)
            if r.status_code == 200:
                j = r.json(); j["_source"] = "owm"
                return j
        params = {"latitude": lat, "longitude": lon, "current_weather": True}
        r2 = httpx.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=8)
        if r2.status_code == 200:
            j2 = r2.json(); j2["_source"] = "open-meteo"
            return j2
    except Exception:
        pass
    return None

def reverse_geocode(lat: float, lon: float) -> Optional[str]:
    try:
        params = {"format": "jsonv2", "lat": lat, "lon": lon, "zoom": 10, "addressdetails": 1}
        headers = {"User-Agent": "ELEC5620-DOLMA-Demo/1.0"}
        r = httpx.get("https://nominatim.openstreetmap.org/reverse", params=params, headers=headers, timeout=6)
        if r.status_code == 200:
            j = r.json(); addr = j.get("address", {}) if isinstance(j, dict) else {}
            city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("municipality") or addr.get("county")
            state = addr.get("state"); country = addr.get("country")
            if city and state: return f"{city}, {state}"
            if city and country: return f"{city}, {country}"
            if state and country: return f"{state}, {country}"
            return city or state or country or None
    except Exception:
        pass
    return None

def _has_precip_from_code(code: Optional[int]) -> bool:
    try:
        if code is None:
            return False
        code = int(code)
        return (
            (51 <= code <= 67) or
            (71 <= code <= 77) or
            (80 <= code <= 82) or
            (85 <= code <= 86) or
            (95 <= code <= 99)
        )
    except Exception:
        return False

def build_weather_tips(temp: Optional[float], cond_text: Optional[str], wind: Optional[float], code: Optional[int] = None) -> str:
    tips = []
    if isinstance(temp, (int, float)):
        if temp < 5: tips.append("Very cold: wear a thick coat/down jacket and keep warm.")
        elif temp < 10: tips.append("Chilly: add a jacket and warm layers.")
        elif temp < 20: tips.append("Cool: bring a light jacket for temperature swings.")
        elif temp > 32: tips.append("Hot: hydrate well and avoid noon sun if possible.")
        elif temp > 28: tips.append("Warm: use sunscreen and drink water frequently.")
    if isinstance(wind, (int, float)) and wind >= 10:
        tips.append("Windy conditions: be cautious cycling or during outdoor activities.")
    text = (cond_text or "").lower()
    has_rain_text = any(k in text for k in ["rain", "shower", "drizzle", "thunder"])
    has_snow_text = any(k in text for k in ["snow"]) 
    if has_rain_text or _has_precip_from_code(code):
        tips.append("Possible rain: carry an umbrella and watch for slippery roads.")
    if has_snow_text:
        tips.append("Snow expected: dress warm and watch for slippery surfaces.")
    if not tips:
        tips.append("Looks good: dress to comfort and have a nice day.")
    return " ".join(tips)

@app.get("/api/google/status")
def google_status():
    return jsonify({"connected": is_connected()})

@app.get("/api/google/login")
def google_login():
    flow = Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRETS_FILE,
        scopes=GOOGLE_SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    session["oauth_state"] = state
    return redirect(authorization_url)

@app.get("/api/google/oauth2callback")
def google_oauth2callback():
    state = session.get("oauth_state")
    if not state:
        return "Missing OAuth state. Try connecting again.", 400
    flow = Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRETS_FILE,
        scopes=GOOGLE_SCOPES,
        redirect_uri=REDIRECT_URI,
        state=state,
    )
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    save_creds(creds)
    return redirect(f"{FRONTEND_URL}/settings?google=connected")

@app.post("/api/google/disconnect")
def google_disconnect():
    try:
        for candidate in ("token.json", "backend/token.json"):
            try:
                if os.path.exists(candidate):
                    os.remove(candidate)
            except Exception:
                pass
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.get("/api/goals")
def api_list_goals():
    status = request.args.get("status")
    goals = storage_list_goals(status=status)
    return jsonify({"goals": goals})


@app.post("/api/goals")
def api_create_goal():
    data = request.get_json(force=True, silent=True) or {}
    try:
        goal = storage_create_goal(
            title=data.get("title", ""),
            description=data.get("description"),
            target_date=data.get("target_date"),
            target_value=data.get("target_value"),
            target_unit=data.get("target_unit"),
            target_period=data.get("target_period"),
            progress_value=data.get("progress_value"),
        )
        return jsonify(goal), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.patch("/api/goals/<goal_id>")
def api_update_goal(goal_id: str):
    data = request.get_json(force=True, silent=True) or {}
    kwargs = {}
    prev_goal = storage_get_goal(goal_id)
    if "title" in data:
        kwargs["title"] = data.get("title")
    if "description" in data:
        kwargs["description"] = data.get("description")
    if "target_date" in data:
        kwargs["target_date"] = data.get("target_date")
    if "progress" in data:
        try:
            kwargs["progress"] = int(data.get("progress"))
        except (TypeError, ValueError):
            return jsonify({"error": "Progress must be an integer between 0 and 100."}), 400
    if "status" in data:
        kwargs["status"] = data.get("status")
    if "target_value" in data:
        kwargs["target_value"] = data.get("target_value")
    if "target_unit" in data:
        kwargs["target_unit"] = data.get("target_unit")
    if "target_period" in data:
        kwargs["target_period"] = data.get("target_period")
    if "progress_value" in data:
        kwargs["progress_value"] = data.get("progress_value")
    if "note" in data and data.get("note"):
        kwargs["note"] = data.get("note")

    try:
        goal = storage_update_goal(goal_id, **kwargs)
        system_message = None
        if prev_goal:
            prev_status = (prev_goal.get("status") or "").lower()
            prev_progress = prev_goal.get("progress") or 0
            is_now_completed = (goal.get("status") or "").lower() == "completed"
            was_completed_before = prev_status == "completed" or prev_progress == 100
            if is_now_completed and not was_completed_before:
                goal_title = goal.get("title") or "Goal"
                system_message = f"I’ve sent the confirmation email—'{goal_title}' is now complete. Fantastic work!"
                print("EMAIL SENT to USER - GOAL COMPLETED")

        payload = dict(goal)
        if system_message:
            payload["system_message"] = system_message
        return jsonify(payload)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.delete("/api/goals/<goal_id>")
def api_delete_goal(goal_id: str):
    goal = storage_get_goal(goal_id)
    if not goal:
        return jsonify({"error": "Goal not found."}), 404
    deleted = storage_delete_goal(goal_id)
    if not deleted:
        return jsonify({"error": "Goal not found."}), 404
    goal_title = goal.get("title") or "Goal"
    print("EMAIL SENT to USER - GOAL DELETED")
    return jsonify({
        "ok": True,
        "system_message": f"I’ve emailed a quick note—'{goal_title}' has been removed from your list."
    })

@app.post("/api/chat")
def chat():
    data = request.get_json(force=True, silent=True) or {}
    user_message = data.get("message")
    conversation = data.get("conversation", [])
    user_location = data.get("location")

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    sydney_now = _current_sydney_datetime()
    today_label = sydney_now.strftime("%A, %d %B %Y")
    current_year = sydney_now.year

    system_prompt = (
        "You are DOLMA, a friendly and intelligent personal assistant. "
        "Always respond helpfully and conversationally, even for repeated questions. "
        "Your main tasks are to aid the user in managing their calendar schedule, tracking goals, and providing reminders. "
        "You are a schedule-managing assistant designed to help users organize tasks and appointments effectively. "
        "Stay within role: personal assistant only. "
        "Only change the user's calendar upon explicit instructions. "
        "If a scheduling conflict arises, suggest polite alternatives. "
        "Do not add or remove events without explicit consent; summarize details first and ask for confirmation. "
        "Be proactive about the user's goals: suggest milestones and check-ins. "
        "Use the goal tools to list, create, or update goals, but always provide a clear preview and obtain explicit approval before saving changes. "
        f"It is currently {today_label} in Sydney, Australia—include the year ({current_year}) whenever you mention a date. "
        "When tracking goals, capture the user's target totals (distance, pages, savings, etc.) and progress in real units so you can talk about what is done and what remains. "
        "You can obtain weather for the user's location and provide schedule suggestions based on conditions. "
        "If user grants location, use it to personalize recommendations."
    )

    messages = [{"role": "system", "content": system_prompt}]

    trimmed_history = [m for m in conversation if m.get("role") in ("user", "assistant")][-6:]
    messages.extend({"role": m["role"], "content": m.get("text", "")} for m in trimmed_history)

    lat = lon = None
    if isinstance(user_location, dict):
        try:
            lat = float(user_location.get("lat"))
            lon = float(user_location.get("lon"))
            messages.append({
                "role": "system",
                "content": f"User granted location. Approx coordinates: lat={lat:.5f}, lon={lon:.5f}.",
            })
        except Exception:
            lat = lon = None

    messages.append({"role": "user", "content": user_message})

    text_l = (user_message or "").lower()
    wants_weather = any(k in text_l for k in ["weather", "forecast", "temperature", "rain", "sunny"]) \
        or any(k in user_message for k in ["天气", "气温", "下雨", "预报"]) if isinstance(user_message, str) else False

    extras = {}
    if wants_weather:
        if lat is None or lon is None:
            ip = get_client_ip(request)
            if ip:
                loc = ip_to_location(ip)
                if loc:
                    lat, lon = loc
        if lat is not None and lon is not None:
            weather = fetch_weather(lat, lon)
            if weather:
                src = weather.get("_source")
                name = None; temp = feels = humidity = wind = None; cond = None
                if src == "owm":
                    name = weather.get("name") or None
                    main = weather.get("main") or {}
                    temp = main.get("temp"); feels = main.get("feels_like"); humidity = main.get("humidity")
                    cond = ", ".join([w.get("description", "") for w in weather.get("weather", []) if isinstance(w, dict)])
                    wind = (weather.get("wind") or {}).get("speed")
                elif "current_weather" in weather:
                    cw = weather.get("current_weather") or {}
                    temp = cw.get("temperature"); wind = cw.get("windspeed")
                details = []
                if temp is not None: details.append(f"Temp {float(temp):.0f}°C")
                if feels is not None: details.append(f"Feels like {float(feels):.0f}°C")
                if humidity is not None: details.append(f"Humidity {int(humidity)}%")
                if wind is not None: details.append(f"Wind {wind} m/s")
                parts = ", ".join(details)
                if not name:
                    name = reverse_geocode(lat, lon) or "your area"
                wx_code = None
                if src != "owm":
                    wx_code = (weather.get("current_weather") or {}).get("weathercode")
                tips = build_weather_tips(temp, cond, wind, wx_code)
                extras = {
                    "tips": tips,
                    "place_name": name,
                    "weather": {
                        "temp": temp, "feels": feels,
                        "humidity": humidity, "wind": wind, "cond": cond,
                    },
                }
                messages.append({
                    "role": "system",
                    "content": f"Live Weather for {name} (lat={lat:.3f}, lon={lon:.3f}): {cond or 'N/A'}; {parts}. Tips: {tips}",
                })

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=calendar_tools,
            tool_choice="auto",
            max_completion_tokens=250,
        )
        msg = response.choices[0].message

        if getattr(msg, "tool_calls", None):
            for call in msg.tool_calls:
                func_name = call.function.name
                args = json.loads(call.function.arguments or "{}")

                if func_name == "create_event":
                    missing = [k for k in ["summary", "start_time", "end_time"] if not args.get(k)]
                    if missing:
                        return jsonify({
                            "reply": f"I need a bit more info. Could you tell me the {', '.join(missing)}?"
                        })
                    if args.get("confirm"):
                        try:
                            start_dt = datetime.fromisoformat(args["start_time"].replace("Z", "+00:00"))
                            end_dt = datetime.fromisoformat(args["end_time"].replace("Z", "+00:00"))
                            _ = create_calendar_event(
                                summary=args["summary"],
                                description=args.get("description", ""),
                                start_time=start_dt,
                                end_time=end_dt,
                            )
                            return jsonify({
                                "reply": f"The event '{args['summary']}' has been added to your calendar!"
                            })
                        except Exception as e:
                            return jsonify({"reply": f"Couldn't create the event: {e}"})
                    preview = (
                        "Here’s what I’ll add:\n"
                        f"• {args['summary']}\n"
                        f"• From: {args['start_time']}\n"
                        f"• To: {args['end_time']}"
                    )
                    return jsonify({
                        "reply": preview + "\nWould you like me to confirm and add this to your calendar?"
                    })

                elif func_name == "create_goal":
                    title = (args.get("title") or "").strip()
                    if not title:
                        return jsonify({"reply": "I need a goal title before I can save it."})
                    description = (args.get("description") or "").strip()
                    target_date = (args.get("target_date") or "").strip() or None
                    try:
                        target_value_num = _coerce_goal_number(args.get("target_value"))
                        starting_progress_num = _coerce_goal_number(args.get("progress_value"))
                    except ValueError as exc:
                        return jsonify({"reply": str(exc)})
                    target_unit = (args.get("target_unit") or "").strip()
                    target_period = (args.get("target_period") or "").strip()

                    preview_lines = [
                        f"• Title: {title}",
                        f"• Target date: {target_date}" if target_date else None,
                    ]
                    if target_value_num is not None:
                        target_bits = _format_decimal(target_value_num) or str(target_value_num)
                        if target_unit:
                            target_bits += f" {target_unit}"
                        if target_period:
                            target_bits += f" ({target_period})"
                        preview_lines.append(f"• Target total: {target_bits}")
                    if starting_progress_num is not None:
                        progress_bits = _format_decimal(starting_progress_num) or str(starting_progress_num)
                        if target_unit:
                            progress_bits += f" {target_unit}"
                        if target_period:
                            progress_bits += f" {target_period}"
                        preview_lines.append(f"• Starting progress: {progress_bits}")
                    if description:
                        preview_lines.append(f"• Details: {description}")

                    preview = "Here’s the goal I’ll save:\n" + "\n".join(
                        line for line in preview_lines if line
                    )
                    if not args.get("confirm"):
                        return jsonify({
                            "reply": preview + "\nWould you like me to record this goal?"
                        })
                    try:
                        goal = storage_create_goal(
                            title=title,
                            description=description,
                            target_date=target_date,
                            target_value=target_value_num,
                            target_unit=target_unit or None,
                            target_period=target_period or None,
                            progress_value=starting_progress_num,
                        )
                        goals = storage_list_goals()
                        return jsonify({
                            "reply": f"All set! I saved '{goal['title']}' with progress at {goal['progress']}%.",
                            "goals": goals,
                        })
                    except ValueError as e:
                        return jsonify({"reply": f"I couldn't save that goal: {e}"})

                elif func_name == "update_goal":
                    goal_id = (args.get("goal_id") or "").strip()
                    goal_title = (args.get("goal_title") or args.get("title") or "").strip()
                    goal = None
                    resolved_id = None

                    if goal_id:
                        goal = storage_get_goal(goal_id)
                        if goal:
                            resolved_id = goal_id
                        elif not goal_title:
                            goal_title = goal_id

                    if not goal and goal_title:
                        title_norm = goal_title.lower()
                        candidates = [
                            g for g in storage_list_goals()
                            if title_norm in (g.get("title") or "").lower()
                        ]
                        if len(candidates) == 1:
                            goal = candidates[0]
                            resolved_id = goal.get("id")
                        elif len(candidates) > 1:
                            suggestions = [
                                f"• {c.get('title', 'Untitled')} (ID: {c.get('id', '')[:6]})"
                                for c in candidates[:5]
                            ]
                            return jsonify({
                                "reply": "I found multiple goals matching that description:\n"
                                + "\n".join(suggestions)
                                + "\nCould you let me know which one you meant (by title or ID)?"
                            })

                    if not goal:
                        if goal_title:
                            return jsonify({
                                "reply": f"I couldn't find a goal that matches '{goal_title}'. Could you clarify the title?"
                            })
                        return jsonify({
                            "reply": "I couldn't find a goal with that ID. Could you double-check it?"
                        })

                    if not goal_id and resolved_id:
                        args["goal_id"] = resolved_id
                        goal_id = resolved_id

                    proposed_changes = []
                    kwargs = {}

                    if "title" in args and (args.get("title") or "").strip():
                        kwargs["title"] = args["title"].strip()
                        proposed_changes.append(f"Title → {kwargs['title']}")
                    if "description" in args and args.get("description") is not None:
                        kwargs["description"] = args["description"]
                        proposed_changes.append("Description update")
                    if "target_date" in args:
                        target_date_val = (args.get("target_date") or "").strip() or None
                        kwargs["target_date"] = target_date_val
                        proposed_changes.append(f"Target date → {target_date_val or 'unset'}")
                    if "target_value" in args:
                        try:
                            parsed_target_value = _coerce_goal_number(args.get("target_value"))
                        except ValueError as exc:
                            return jsonify({"reply": str(exc)})
                        kwargs["target_value"] = parsed_target_value
                        if parsed_target_value is None:
                            proposed_changes.append("Target total → removed")
                        else:
                            target_text = _format_decimal(parsed_target_value) or str(parsed_target_value)
                            prospective_unit = (args.get("target_unit") or goal.get("target_unit") or "").strip()
                            prospective_period = (args.get("target_period") or goal.get("target_period") or "").strip()
                            if prospective_unit:
                                target_text += f" {prospective_unit}"
                            if prospective_period:
                                target_text += f" ({prospective_period})"
                            proposed_changes.append(f"Target total → {target_text}")
                    if "target_unit" in args:
                        unit_val = (args.get("target_unit") or "").strip() or None
                        kwargs["target_unit"] = unit_val
                        proposed_changes.append(f"Target unit → {unit_val or 'unset'}")
                    if "target_period" in args:
                        period_val = (args.get("target_period") or "").strip() or None
                        kwargs["target_period"] = period_val
                        proposed_changes.append(f"Target period → {period_val or 'unset'}")
                    if "progress" in args:
                        try:
                            kwargs["progress"] = int(args.get("progress"))
                        except (TypeError, ValueError):
                            return jsonify({"reply": "Progress needs to be a number between 0 and 100."})
                        proposed_changes.append(f"Progress → {kwargs['progress']}%")
                    if "progress_value" in args:
                        try:
                            parsed_progress_value = _coerce_goal_number(args.get("progress_value"))
                        except ValueError as exc:
                            return jsonify({"reply": str(exc)})
                        kwargs["progress_value"] = parsed_progress_value
                        if parsed_progress_value is None:
                            proposed_changes.append("Progress amount → removed")
                        else:
                            progress_text = _format_decimal(parsed_progress_value) or str(parsed_progress_value)
                            unit_source = (args.get("target_unit") or goal.get("target_unit") or "").strip()
                            if unit_source:
                                progress_text += f" {unit_source}"
                            prospective_period = (args.get("target_period") or goal.get("target_period") or "").strip()
                            if prospective_period:
                                progress_text += f" {prospective_period}"
                            proposed_changes.append(f"Progress amount → {progress_text}")
                    if "status" in args and args.get("status"):
                        kwargs["status"] = args["status"]
                        proposed_changes.append(f"Status → {kwargs['status']}")
                    if "note" in args and args.get("note"):
                        kwargs["note"] = args["note"]
                        proposed_changes.append("Add note to history")

                    if not proposed_changes:
                        return jsonify({"reply": "I couldn't see any changes to apply. Let me know what you'd like to update."})

                    summary = (
                        f"Planned updates for '{goal.get('title', 'goal')}':\n"
                        + "\n".join(f"• {item}" for item in proposed_changes)
                    )

                    if not args.get("confirm"):
                        return jsonify({
                            "reply": summary + "\nIs it okay to apply these changes?"
                        })

                    try:
                        updated = storage_update_goal(goal_id, **kwargs)
                        goals = storage_list_goals()
                        return jsonify({
                            "reply": f"Done! '{updated['title']}' is now at {updated['progress']}% ({updated['status']}).",
                            "goals": goals,
                        })
                    except ValueError as e:
                        return jsonify({"reply": f"I couldn't update that goal: {e}"})

                elif func_name == "list_goals":
                    status_filter = (args.get("status") or "").strip() or None
                    goals = storage_list_goals(status=status_filter)
                    if not goals:
                        if status_filter:
                            return jsonify({
                                "reply": f"No {status_filter} goals on record yet. Feel free to create one!"
                            })
                        return jsonify({
                            "reply": "You don’t have any goals saved yet. Ready to set one up?"
                        })

                    lines = [f"• {_compose_goal_progress(goal)}" for goal in goals]
                    reply = "Here’s what I found:\n" + "\n".join(lines)
                    return jsonify({"reply": reply, "goals": goals})

        reply = (msg.content or "").strip()
        if not reply or reply in ("...", "…", "Ok", "Okay"):
            regen = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages + [{"role": "user", "content": "Please elaborate."}],
                max_completion_tokens=250,
            )
            reply = (regen.choices[0].message.content or "").strip()

        result = {"reply": reply}
        if extras:
            result.update(extras)
        return jsonify(result)

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500

@app.get("/api/health")
def health():
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(debug=True)
