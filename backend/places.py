"""
Nearby place lookups, backed by OpenStreetMap.

Queried through the public Overpass API, which needs no key or account — the same
reasoning that put Open-Meteo behind the weather fallback. Results are real OSM
records, so the assistant can name a place because it was returned here rather
than because it remembered something that sounded plausible.
"""

import math
from typing import Dict, List, Optional, Tuple

import httpx

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Public instances ask that clients identify themselves.
HEADERS = {"User-Agent": "ELEC5620-DOLMA-Demo/1.0"}

DEFAULT_RADIUS_M = 1500
MAX_RADIUS_M = 5000
DEFAULT_LIMIT = 8
MAX_LIMIT = 20

# What each category the model can ask for means in OpenStreetMap's tagging.
# A category maps to several tags where the everyday word covers several of them:
# someone asking for a bar in Sydney means pubs too.
CATEGORY_TAGS: Dict[str, List[Tuple[str, str]]] = {
    "bar": [("amenity", "bar"), ("amenity", "pub"), ("amenity", "biergarten")],
    "nightclub": [("amenity", "nightclub")],
    "cafe": [("amenity", "cafe")],
    "restaurant": [("amenity", "restaurant"), ("amenity", "fast_food")],
    "supermarket": [("shop", "supermarket"), ("shop", "convenience")],
    "pharmacy": [("amenity", "pharmacy")],
    "gym": [("leisure", "fitness_centre"), ("leisure", "sports_centre")],
    "park": [("leisure", "park")],
    "library": [("amenity", "library")],
    "bank": [("amenity", "bank"), ("amenity", "atm")],
    "hospital": [("amenity", "hospital"), ("amenity", "clinic")],
}


def _distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    """Great-circle distance, good enough for ordering results by nearness."""
    radius = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return int(round(2 * radius * math.asin(math.sqrt(a))))


def _build_query(category: str, lat: float, lon: float, radius_m: int) -> str:
    clauses = []
    for key, value in CATEGORY_TAGS[category]:
        for element in ("node", "way"):
            clauses.append(f'{element}["{key}"="{value}"](around:{radius_m},{lat},{lon});')
    return f"[out:json][timeout:25];({''.join(clauses)});out center tags 60;"


def _compose_address(tags: Dict[str, str]) -> Optional[str]:
    number = tags.get("addr:housenumber")
    street = tags.get("addr:street")
    suburb = tags.get("addr:suburb") or tags.get("addr:city")
    line = " ".join(part for part in (number, street) if part)
    if line and suburb:
        return f"{line}, {suburb}"
    return line or suburb or None


def find_nearby(
    category: str,
    lat: float,
    lon: float,
    radius_m: int = DEFAULT_RADIUS_M,
    limit: int = DEFAULT_LIMIT,
    keyword: Optional[str] = None,
) -> List[dict]:
    """
    Return nearby places of one category, nearest first.

    Raises ValueError for an unknown category and RuntimeError when Overpass does
    not answer, so the caller can turn either into an observation.
    """
    if category not in CATEGORY_TAGS:
        raise ValueError(
            f"Unknown category '{category}'. Choose one of: {', '.join(sorted(CATEGORY_TAGS))}."
        )

    radius_m = max(100, min(int(radius_m or DEFAULT_RADIUS_M), MAX_RADIUS_M))
    limit = max(1, min(int(limit or DEFAULT_LIMIT), MAX_LIMIT))

    try:
        response = httpx.post(
            OVERPASS_URL,
            data={"data": _build_query(category, lat, lon, radius_m)},
            headers=HEADERS,
            timeout=30,
        )
    except Exception as exc:
        raise RuntimeError(f"OpenStreetMap lookup failed: {exc}") from exc

    if response.status_code != 200:
        raise RuntimeError(f"OpenStreetMap returned HTTP {response.status_code}.")

    results = []
    for element in response.json().get("elements", []):
        tags = element.get("tags") or {}
        name = tags.get("name")
        if not name:
            continue  # an unnamed pub is no use in a recommendation
        if keyword and keyword.lower() not in name.lower():
            continue

        centre = element.get("center") or element
        place_lat, place_lon = centre.get("lat"), centre.get("lon")
        if place_lat is None or place_lon is None:
            continue

        results.append(
            {
                "name": name,
                "kind": tags.get("amenity") or tags.get("shop") or tags.get("leisure"),
                "distance_m": _distance_m(lat, lon, place_lat, place_lon),
                "address": _compose_address(tags),
                "opening_hours": tags.get("opening_hours"),
                "website": tags.get("website") or tags.get("contact:website"),
            }
        )

    # Overpass returns nodes and ways separately, so the same venue can appear twice.
    seen, unique = set(), []
    for place in sorted(results, key=lambda p: p["distance_m"]):
        if place["name"] in seen:
            continue
        seen.add(place["name"])
        unique.append(place)

    return unique[:limit]
