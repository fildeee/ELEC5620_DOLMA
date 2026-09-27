"""
Weather and coarse geolocation lookups.

Extracted from app.py so the agent's get_weather tool can call them without
importing the Flask app.
"""

import os
from typing import Optional, Tuple

import httpx

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")


def get_client_ip(req) -> Optional[str]:
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


# function to fetch weather data from OpenWeatherMap
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


def current_conditions(lat: float, lon: float) -> Optional[dict]:
    """
    Fetch and normalise the current weather into the flat shape the chat reply
    and the frontend's weather card both use.

    Returns None when neither provider answers.
    """
    raw = fetch_weather(lat, lon)
    if not raw:
        return None

    source = raw.get("_source")
    place = None
    temp = feels = humidity = wind = cond = code = None

    if source == "owm":
        place = raw.get("name") or None
        main = raw.get("main") or {}
        temp = main.get("temp")
        feels = main.get("feels_like")
        humidity = main.get("humidity")
        wind = (raw.get("wind") or {}).get("speed")
        cond = ", ".join(
            w.get("description", "") for w in raw.get("weather", []) if isinstance(w, dict)
        ) or None
    elif "current_weather" in raw:
        cw = raw.get("current_weather") or {}
        temp = cw.get("temperature")
        wind = cw.get("windspeed")
        code = cw.get("weathercode")

    if not place:
        place = reverse_geocode(lat, lon) or "your area"

    return {
        "place_name": place,
        "temp": temp,
        "feels": feels,
        "humidity": humidity,
        "wind": wind,
        "cond": cond,
        "tips": build_weather_tips(temp, cond, wind, code),
    }
