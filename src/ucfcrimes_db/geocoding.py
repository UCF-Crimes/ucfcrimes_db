"""Locate new reports using the monorepo's Google and campus address lookups."""

import json
import re
from functools import lru_cache
from importlib.resources import files
from math import atan2, cos, radians, sin, sqrt

import editdistance
import requests

GOOGLE_MAPS_URL = "https://maps.googleapis.com/maps/api"
ORLANDO_BOUNDS = "28.522318,-81.407249|28.644500,-81.155722"
ADDRESS_OVERRIDES = {
    "B8": (28.5939606, -81.2014182),
    "36 PINE ST W": (28.5412345, -81.3797360),
    "ON CAMPUS": (28.6024367, -81.2000568),
    "PLAZA DR E": (28.6069698, -81.1967868),
    "PLAZA DR W": (28.6074074, -81.1980356),
    "GEMINI/SCORPIUS": (28.6018854, -81.1944728),
    "KINGS KNIGHT": (28.6104158, -81.2154757),
    "KROSSING": (28.6113891, -81.2113697),
    "410 TERRY AVE N": (28.537944, -81.386917),
}
ADDRESS_SUBSTITUTIONS = {
    " W ": " WEST ",
    " E ": " EAST ",
    " N ": " NORTH ",
    " S ": " SOUTH ",
    "BLD": "BLVD",
    r" ?(?: and |/) ?": " & ",
}


@lru_cache(maxsize=2)
def read_lookup(name: str) -> dict[str, str]:
    return json.loads(files("ucfcrimes_db").joinpath("data", name).read_text(encoding="utf-8"))


def google_results(endpoint: str, params: dict[str, str]) -> list[dict]:
    try:
        response = requests.get(f"{GOOGLE_MAPS_URL}/{endpoint}", params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            status = data.get("status")
            if status == "OK" and isinstance(data.get("results"), list):
                return data["results"]
            if status == "ZERO_RESULTS":
                return []
            if status and status != "OK":
                print(f"Google Maps returned status {status}.")
                return []
        print("Google Maps returned an invalid response.")
    except requests.RequestException as error:
        # Network exception messages can contain the API key.
        print(f"Google Maps request failed: {type(error).__name__}")
    return []


def google_geocoder(address: str, api_key: str) -> tuple[float | None, float | None]:
    for phrase, coordinates in ADDRESS_OVERRIDES.items():
        if phrase in address:
            return coordinates

    if api_key:
        results = google_results(
            "geocode/json", {"address": address, "key": api_key, "bounds": ORLANDO_BOUNDS}
        )
        if results:
            try:
                location = results[0]["geometry"]["location"]
                return round(location["lat"], 7), round(location["lng"], 7)
            except (KeyError, TypeError, ValueError):
                print("Google Maps returned an invalid geocoding result.")
    return None, None


def distance_km(lat: float, lng: float, other_lat: float, other_lng: float) -> float:
    latitude, other_latitude = radians(lat), radians(other_lat)
    latitude_delta = other_latitude - latitude
    longitude_delta = radians(other_lng - lng)
    a = sin(latitude_delta / 2) ** 2 + cos(latitude) * cos(other_latitude) * sin(longitude_delta / 2) ** 2
    return 6371 * 2 * atan2(sqrt(a), sqrt(1 - a))


def nearby_place(lat: float, lng: float, api_key: str) -> str | None:
    candidates = []
    for result in google_results(
        "place/nearbysearch/json", {"location": f"{lat},{lng}", "radius": "100", "key": api_key}
    ):
        try:
            if {"route", "transit_station"}.intersection(result["types"]):
                continue
            location = result["geometry"]["location"]
            candidates.append((distance_km(lat, lng, location["lat"], location["lng"]), result["name"]))
        except (KeyError, TypeError, ValueError):
            continue
    return min(candidates, default=(0, None))[1]


def address_to_place(address: str, lat: float | None, lng: float | None, api_key: str) -> str:
    normalized = f" {address.replace('.', '')} "
    for pattern, replacement in ADDRESS_SUBSTITUTIONS.items():
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
    address_tokens = normalized.split()
    if not address_tokens:
        return address

    for alias, place in read_lookup("locations.json").items():
        alias_tokens = alias.split()
        address_number, alias_number = address_tokens[0], alias_tokens[0]
        if address_number[0].isdigit() and alias_number[0].isdigit() and address_number != alias_number:
            continue
        if all(
            any(editdistance.eval(alias_token, token) <= 1 for token in address_tokens)
            for alias_token in alias_tokens
        ):
            return place

    if api_key and lat is not None and lng is not None and (place := nearby_place(lat, lng, api_key)):
        return f"near {place}"

    exceptions = read_lookup("title_exceptions.json")
    return " ".join(exceptions.get(token, token.title()) for token in address_tokens)
