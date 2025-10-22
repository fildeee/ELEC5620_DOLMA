from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import os
import httpx
from typing import Optional, Tuple

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")


def get_client_ip(req: request) -> Optional[str]:
    # Honor proxies if any
    fwd = req.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    ip = fwd or req.remote_addr or ""
    if not ip:
        return None
    # Skip localhost/private ranges commonly seen in dev
    private_prefixes = ("127.", "10.", "192.168.", "172.16.", "172.17.", "172.18.", "172.19.", "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.", "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.")
    if ip.startswith(private_prefixes) or ip == "::1":
        return None
    return ip


def ip_to_location(ip: str) -> Optional[Tuple[float, float]]:
    # Free, no-key IP geolocation service suitable for demos
    try:
        url = f"http://ip-api.com/json/{ip}?fields=status,lat,lon"
        r = httpx.get(url, timeout=5)
        if r.status_code == 200:
            j = r.json()
            if j.get("status") == "success":
                lat = j.get("lat")
                lon = j.get("lon")
                if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
                    return float(lat), float(lon)
    except Exception:
        pass
    return None


def fetch_weather(lat: float, lon: float) -> Optional[dict]:
    """Fetch current weather.

    - Uses OpenWeatherMap if OPENWEATHER_API_KEY is set.
    - Falls back to Open-Meteo (no key) for demos if not.
    """
    try:
        if OPENWEATHER_API_KEY:
            params = {
                "lat": lat,
                "lon": lon,
                "appid": OPENWEATHER_API_KEY,
                "units": "metric",
                "lang": "en",
            }
            r = httpx.get("https://api.openweathermap.org/data/2.5/weather", params=params, timeout=8)
            if r.status_code == 200:
                j = r.json()
                j["_source"] = "owm"
                return j
        # Fallback: Open-Meteo (no API key)
        params = {
            "latitude": lat,
            "longitude": lon,
            "current_weather": True,
        }
        r2 = httpx.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=8)
        if r2.status_code == 200:
            j2 = r2.json()
            j2["_source"] = "open-meteo"
            return j2
    except Exception:
        pass
    return None


def reverse_geocode(lat: float, lon: float) -> Optional[str]:
    """Reverse geocode coordinates to a readable place name via OSM Nominatim.
    Intended for demo use only (rate limited)."""
    try:
        params = {
            "format": "jsonv2",
            "lat": lat,
            "lon": lon,
            "zoom": 10,
            "addressdetails": 1,
        }
        headers = {"User-Agent": "ELEC5620-DOLMA-Demo/1.0"}
        r = httpx.get("https://nominatim.openstreetmap.org/reverse", params=params, headers=headers, timeout=6)
        if r.status_code == 200:
            j = r.json()
            addr = j.get("address", {}) if isinstance(j, dict) else {}
            city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("municipality") or addr.get("county")
            state = addr.get("state")
            country = addr.get("country")
            if city and state:
                return f"{city}, {state}"
            if city and country:
                return f"{city}, {country}"
            if state and country:
                return f"{state}, {country}"
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
            (51 <= code <= 67)  # drizzle/rain freezing rain
            or (71 <= code <= 77)  # snow
            or (80 <= code <= 82)  # rain showers
            or (85 <= code <= 86)  # snow showers
            or (95 <= code <= 99)  # thunderstorms
        )
    except Exception:
        return False


def build_weather_tips(temp: Optional[float], cond_text: Optional[str], wind: Optional[float], code: Optional[int] = None) -> str:
    tips = []
    # Temperature-based tips
    if isinstance(temp, (int, float)):
        if temp < 5:
            tips.append("Very cold: wear a thick coat/down jacket and keep warm.")
        elif temp < 10:
            tips.append("Chilly: add a jacket and warm layers.")
        elif temp < 20:
            tips.append("Cool: bring a light jacket for temperature swings.")
        elif temp > 32:
            tips.append("Hot: hydrate well and avoid noon sun if possible.")
        elif temp > 28:
            tips.append("Warm: use sunscreen and drink water frequently.")

    # Wind tip
    if isinstance(wind, (int, float)) and wind >= 10:
        tips.append("Windy conditions: be cautious cycling or during outdoor activities.")

    # Precipitation tips from text or code
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


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message")
    conversation = data.get("conversation", [])
    user_location = data.get("location")  # {"lat": float, "lon": float} optionally from frontend

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    # System role
    messages = [
        {
            "role": "system",
            "content": (
                "You are DOLMA, a friendly and intelligent personal assistant. "
                "Always respond helpfully and conversationally, even for repeated questions."
                "You can obtain the weather of the user's city and provide schedule suggestions based on the weather conditions."
                "You can obtain the user's location to provide localized recommendations like scenic spot and local events."
                "you have access to the user's calendar and give suggestions to optimize their schedule based on their habit and real-time information."
                "Your main tasks are to aid the user in managing their schedule, tracking goals, and providing reminders."
                "You are a schedule managing assistant designed to help users organize their tasks and appointments effectively."
                "You are to maintain your role strictly as a perosonal assistant and not deviate into other roles."
                "You will change the user's calendar upon explicit instructions only."
                "Whenever a conflict arises in scheduling, you will suggest alternative times politely."
                "Events shall not be added or removed from the user's calendar without their explicit consent."
            ),
        }
    ]

    # Add trimmed context (only recent 6 messages)
    trimmed_history = [
        m for m in conversation if m["role"] in ["user", "assistant"]
    ][-6:]

    messages.extend(
        {"role": m["role"], "content": m["text"]} for m in trimmed_history
    )

    # If the frontend provided location, attach a brief note so the model can respond contextually
    lat = lon = None
    if user_location and isinstance(user_location, dict):
        try:
            lat = float(user_location.get("lat"))
            lon = float(user_location.get("lon"))
            messages.append({
                "role": "system",
                "content": f"User has granted location. Approx coordinates: lat={lat:.5f}, lon={lon:.5f}.",
            })
        except Exception:
            lat = lon = None

    # Add the new message
    messages.append({"role": "user", "content": user_message})

    try:
        # Simple weather-intent detection; if matched, fetch real weather
        text_l = (user_message or "").lower()
        wants_weather = any(k in text_l for k in ["weather", "forecast", "temperature", "rain", "sunny"]) or any(k in user_message for k in ["天气", "气温", "下雨", "预报"])

        extras = {}
        if wants_weather:
            # Determine location: prefer provided coords, else IP-based
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
                    name = None
                    temp = feels = humidity = wind = None
                    cond = None
                    if src == "owm":
                        name = weather.get("name") or None
                        main = weather.get("main") or {}
                        temp = main.get("temp")
                        feels = main.get("feels_like")
                        humidity = main.get("humidity")
                        cond = ", ".join([w.get("description", "") for w in weather.get("weather", []) if isinstance(w, dict)])
                        wind = weather.get("wind", {}).get("speed")
                    elif "current_weather" in weather:
                        cw = weather.get("current_weather") or {}
                        temp = cw.get("temperature")
                        wind = cw.get("windspeed")
                        # Open-Meteo gives weathercode numeric; leave cond as None for demo

                    details = []
                    if temp is not None:
                        details.append(f"Temp {temp:.0f}°C")
                    if feels is not None:
                        details.append(f"Feels like {feels:.0f}°C")
                    if humidity is not None:
                        details.append(f"Humidity {int(humidity)}%")
                    if wind is not None:
                        details.append(f"Wind {wind} m/s")
                    parts = ", ".join(details)

                    # Resolve readable place name if missing
                    if not name:
                        name = reverse_geocode(lat, lon) or "your area"

                    # Add concise, rule-based suggestions
                    wx_code = None
                    if src != "owm":
                        wx_code = (weather.get("current_weather") or {}).get("weathercode")
                    tips = build_weather_tips(temp, cond, wind, wx_code)

                    # Save extras for frontend to render a tips card
                    extras = {
                        "tips": tips,
                        "place_name": name,
                        "weather": {
                            "temp": temp,
                            "feels": feels,
                            "humidity": humidity,
                            "wind": wind,
                            "cond": cond,
                        },
                    }

                    messages.append({
                        "role": "system",
                        "content": f"Live Weather for {name} (lat={lat:.3f}, lon={lon:.3f}): {cond or 'N/A'}; {parts}. Tips: {tips}",
                    })
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_completion_tokens=250,
        )

        reply = response.choices[0].message.content.strip()

        # If reply is empty or too minimal, re-ask once
        if not reply or reply in ["...", "Ok", "Okay"]:
            regen = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages
                + [{"role": "user", "content": "Please elaborate."}],
                max_completion_tokens=250,
            )
            reply = regen.choices[0].message.content.strip()

        result = {"reply": reply}
        # Attach extras only when present
        for k in ("tips", "place_name", "weather"):
            if k in locals().get("extras", {}):
                result[k] = extras[k]
        return jsonify(result)

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
