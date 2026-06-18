"""
NavigationService.py — Geocoding, Routing, Traffic & Navigation for Jarvis
Uses free APIs: OSRM (routing), Nominatim (geocoding), Open-Meteo (weather)
"""

import requests
import math
import datetime
import threading

HEADERS = {"User-Agent": "Jarvis-AI-Assistant/1.0"}

# ========== PHONE GPS STATE ==========
_phone_location = {
    "lat": None,
    "lon": None,
    "accuracy": None,
    "timestamp": None
}
_phone_lock = threading.Lock()

def update_phone_location(lat, lon, accuracy=None):
    """Called by the server when phone sends its GPS coordinates."""
    with _phone_lock:
        _phone_location["lat"] = lat
        _phone_location["lon"] = lon
        _phone_location["accuracy"] = accuracy
        _phone_location["timestamp"] = datetime.datetime.now().isoformat()

def get_phone_location():
    """Return the latest phone GPS coordinates."""
    with _phone_lock:
        return dict(_phone_location)


# ========== HOME LOCATION ==========
_home_location = {"lat": None, "lon": None}

def set_home_location(lat, lon):
    global _home_location
    _home_location = {"lat": lat, "lon": lon}

def get_home_location():
    return dict(_home_location)


# ========== GEOCODING (Nominatim — free) ==========
def geocode(place_name):
    """Convert a place name to lat/lon coordinates."""
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": place_name, "format": "json", "limit": 1}
        res = requests.get(url, params=params, headers=HEADERS, timeout=10).json()
        if res:
            return {
                "lat": float(res[0]["lat"]),
                "lon": float(res[0]["lon"]),
                "display_name": res[0].get("display_name", place_name)
            }
        return None
    except Exception as e:
        print(f"[Navigation] Geocode failed: {e}")
        return None


def reverse_geocode(lat, lon):
    """Convert lat/lon to a human-readable address."""
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {"lat": lat, "lon": lon, "format": "json"}
        res = requests.get(url, params=params, headers=HEADERS, timeout=10).json()
        return {
            "display_name": res.get("display_name", f"{lat}, {lon}"),
            "address": res.get("address", {})
        }
    except Exception as e:
        print(f"[Navigation] Reverse geocode failed: {e}")
        return {"display_name": f"{lat:.4f}, {lon:.4f}", "address": {}}


# ========== ROUTING (OSRM — free, no key) ==========
def get_route(origin_lat, origin_lon, dest_lat, dest_lon):
    """Get driving route with turn-by-turn directions using OSRM."""
    try:
        url = (f"http://router.project-osrm.org/route/v1/driving/"
               f"{origin_lon},{origin_lat};{dest_lon},{dest_lat}"
               f"?overview=full&steps=true&geometries=geojson")
        res = requests.get(url, headers=HEADERS, timeout=15).json()

        if res.get("code") != "Ok" or not res.get("routes"):
            return None

        route = res["routes"][0]
        legs = route.get("legs", [{}])
        steps_raw = legs[0].get("steps", []) if legs else []

        steps = []
        for s in steps_raw:
            maneuver = s.get("maneuver", {})
            steps.append({
                "instruction": s.get("name", "Continue"),
                "distance_m": s.get("distance", 0),
                "duration_s": s.get("duration", 0),
                "maneuver_type": maneuver.get("type", ""),
                "maneuver_modifier": maneuver.get("modifier", ""),
                "bearing_after": maneuver.get("bearing_after", 0),
                "location": maneuver.get("location", [0, 0])
            })

        return {
            "distance_km": round(route.get("distance", 0) / 1000, 1),
            "duration_min": round(route.get("duration", 0) / 60, 1),
            "steps": steps,
            "geometry": route.get("geometry", {})
        }
    except Exception as e:
        print(f"[Navigation] Route failed: {e}")
        return None


# ========== DESTINATION WEATHER ==========
def get_destination_weather(lat, lon):
    """Fetch current weather at a specific location using Open-Meteo."""
    try:
        url = (f"https://api.open-meteo.com/v1/forecast?"
               f"latitude={lat}&longitude={lon}"
               f"&current=temperature_2m,weather_code,wind_speed_10m,precipitation")
        res = requests.get(url, headers=HEADERS, timeout=10).json()
        current = res.get("current", {})

        # Decode weather code
        code = current.get("weather_code", 0)
        conditions = {
            0: "Clear", 1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast",
            45: "Foggy", 48: "Icy Fog", 51: "Light Drizzle", 53: "Drizzle",
            55: "Heavy Drizzle", 61: "Light Rain", 63: "Rain", 65: "Heavy Rain",
            71: "Light Snow", 73: "Snow", 75: "Heavy Snow", 80: "Rain Showers",
            81: "Heavy Rain Showers", 95: "Thunderstorm"
        }
        condition = conditions.get(code, "Unknown")

        return {
            "temp": current.get("temperature_2m", 0),
            "condition": condition,
            "wind_speed": current.get("wind_speed_10m", 0),
            "precipitation": current.get("precipitation", 0)
        }
    except Exception as e:
        print(f"[Navigation] Destination weather failed: {e}")
        return None


# ========== BEARING CALCULATION ==========
def calculate_bearing(lat1, lon1, lat2, lon2):
    """Calculate compass bearing from point 1 to point 2."""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360


def bearing_to_compass(bearing):
    """Convert bearing degrees to compass direction."""
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return dirs[int((bearing + 11.25) / 22.5) % 16]


# ========== HIGH-LEVEL FUNCTIONS ==========
def get_traffic_summary(origin_name_or_coords, destination_name):
    """Get full navigation summary: route + ETA + destination weather."""
    # Resolve origin
    if isinstance(origin_name_or_coords, dict):
        origin_lat = origin_name_or_coords["lat"]
        origin_lon = origin_name_or_coords["lon"]
        origin_name = f"{origin_lat:.4f}, {origin_lon:.4f}"
    else:
        geo = geocode(origin_name_or_coords)
        if not geo:
            return {"error": f"Could not find location: {origin_name_or_coords}"}
        origin_lat, origin_lon = geo["lat"], geo["lon"]
        origin_name = geo["display_name"]

    # Resolve destination
    dest_geo = geocode(destination_name)
    if not dest_geo:
        return {"error": f"Could not find destination: {destination_name}"}

    # Get route
    route = get_route(origin_lat, origin_lon, dest_geo["lat"], dest_geo["lon"])
    if not route:
        return {"error": "Could not calculate route"}

    # Get destination weather
    weather = get_destination_weather(dest_geo["lat"], dest_geo["lon"])

    # Get bearing
    bearing = calculate_bearing(origin_lat, origin_lon, dest_geo["lat"], dest_geo["lon"])

    return {
        "origin": origin_name,
        "destination": dest_geo["display_name"],
        "dest_lat": dest_geo["lat"],
        "dest_lon": dest_geo["lon"],
        "distance_km": route["distance_km"],
        "duration_min": route["duration_min"],
        "steps": route["steps"],
        "bearing": round(bearing, 1),
        "compass": bearing_to_compass(bearing),
        "dest_weather": weather,
        "geometry": route.get("geometry")
    }


def navigate_from_phone(destination_name):
    """Navigate from phone's current GPS location to a destination."""
    phone = get_phone_location()
    if phone["lat"] is None:
        return {"error": "Phone location not available. Please enable GPS on your phone."}

    return get_traffic_summary(
        {"lat": phone["lat"], "lon": phone["lon"]},
        destination_name
    )


def navigate_home():
    """Navigate from phone's current location back to home (laptop location)."""
    phone = get_phone_location()
    if phone["lat"] is None:
        return {"error": "Phone location not available. Please enable GPS on your phone."}

    home = get_home_location()
    if home["lat"] is None:
        return {"error": "Home location not set."}

    route = get_route(phone["lat"], phone["lon"], home["lat"], home["lon"])
    if not route:
        return {"error": "Could not calculate route home."}

    bearing = calculate_bearing(phone["lat"], phone["lon"], home["lat"], home["lon"])
    weather = get_destination_weather(home["lat"], home["lon"])

    home_geo = reverse_geocode(home["lat"], home["lon"])

    return {
        "origin": f"Your location ({phone['lat']:.4f}, {phone['lon']:.4f})",
        "destination": home_geo["display_name"],
        "dest_lat": home["lat"],
        "dest_lon": home["lon"],
        "distance_km": route["distance_km"],
        "duration_min": route["duration_min"],
        "steps": route["steps"],
        "bearing": round(bearing, 1),
        "compass": bearing_to_compass(bearing),
        "dest_weather": weather,
        "geometry": route.get("geometry")
    }


def where_am_i():
    """Get a description of where the phone currently is."""
    phone = get_phone_location()
    if phone["lat"] is None:
        return {"error": "Phone location not available. Please enable GPS on your phone."}

    geo = reverse_geocode(phone["lat"], phone["lon"])
    weather = get_destination_weather(phone["lat"], phone["lon"])

    return {
        "location": geo["display_name"],
        "lat": phone["lat"],
        "lon": phone["lon"],
        "accuracy": phone["accuracy"],
        "weather": weather,
        "timestamp": phone["timestamp"]
    }
