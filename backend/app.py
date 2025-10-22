from flask import Flask, request, jsonify, redirect, session
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
from datetime import datetime
from typing import Optional, Tuple

import httpx
from google_auth_oauthlib.flow import Flow

from google_calendar import (
    get_calendar_service,
    is_connected,
    save_creds,
    create_calendar_event,
)
from tools import calendar_tools

load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True)

app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

GOOGLE_SCOPES = ["https://www.googleapis.com/auth/calendar"]
GOOGLE_CLIENT_SECRETS_FILE = os.getenv(
    "GOOGLE_CLIENT_SECRETS_FILE", "backend/credentials.json"
)
REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI", "http://localhost:5000/api/google/oauth2callback"
)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

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

@app.post("/api/chat")
def chat():
    data = request.get_json(force=True, silent=True) or {}
    user_message = data.get("message")
    conversation = data.get("conversation", [])
    user_location = data.get("location")

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    system_prompt = (
        "You are DOLMA, a friendly and intelligent personal assistant. "
        "Always respond helpfully and conversationally, even for repeated questions. "
        "Your main tasks are to aid the user in managing their calendar schedule, tracking goals, and providing reminders. "
        "You are a schedule-managing assistant designed to help users organize tasks and appointments effectively. "
        "Stay within role: personal assistant only. "
        "Only change the user's calendar upon explicit instructions. "
        "If a scheduling conflict arises, suggest polite alternatives. "
        "Do not add or remove events without explicit consent; summarize details first and ask for confirmation. "
        "It's 2025 in Sydney, Australia—include the year in dates you mention. "
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
                if call.function.name == "create_event":
                    args = json.loads(call.function.arguments or "{}")
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
