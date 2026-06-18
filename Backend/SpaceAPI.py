import requests
import datetime
import os
import ctypes
import threading
from dotenv import dotenv_values

env_vars = dotenv_values(".env")
NASA_API_KEY = env_vars.get("NASA_API_KEY", "DEMO_KEY")
STATIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Frontend", "remote", "static"))
os.makedirs(STATIC_DIR, exist_ok=True)

class SpaceAPI:
    def __init__(self):
        self.cache = {}
        self.lock = threading.Lock()
        
    def _is_cache_valid(self, key, expiry_hours=1):
        if key in self.cache:
            if datetime.datetime.now() < self.cache[key]['expires']:
                return True
        return False

    def get_location(self):
        """Fetch approximate GPS coordinates based on IP address."""
        key = "location"
        if self._is_cache_valid(key, expiry_hours=24):
            return self.cache[key]['data']
            
        try:
            res = requests.get("https://ipinfo.io/json", timeout=5).json()
            loc = res.get("loc", "0,0").split(",")
            data = {
                "city": res.get("city", "Unknown"),
                "lat": float(loc[0]),
                "lon": float(loc[1])
            }
            with self.lock:
                self.cache[key] = {
                    'data': data,
                    'expires': datetime.datetime.now() + datetime.timedelta(hours=24)
                }
            return data
        except Exception as e:
            print(f"[SpaceAPI] Location fetch failed: {e}")
            return {"city": "Unknown", "lat": 0, "lon": 0}

    def get_map_tile(self, lat=None, lon=None, zoom=11):
        """Fetch OpenStreetMap tiles and stitch a 3x3 grid centered on location."""
        import math
        if lat is None or lon is None:
            loc = self.get_location()
            lat, lon = loc["lat"], loc["lon"]
        
        # Convert lat/lon to tile coordinates
        n = 2 ** zoom
        x_tile = int((lon + 180.0) / 360.0 * n)
        y_tile = int((1.0 - math.log(math.tan(math.radians(lat)) + 1.0 / math.cos(math.radians(lat))) / math.pi) / 2.0 * n)
        
        try:
            import io
            from PIL import Image
            
            # Fetch 3x3 grid of tiles
            tile_size = 256
            result = Image.new('RGB', (tile_size * 3, tile_size * 3))
            headers = {"User-Agent": "Jarvis-AI-Assistant/1.0"}
            
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    tx = x_tile + dx
                    ty = y_tile + dy
                    url = f"https://tile.openstreetmap.org/{zoom}/{tx}/{ty}.png"
                    resp = requests.get(url, headers=headers, timeout=10)
                    if resp.status_code == 200:
                        tile_img = Image.open(io.BytesIO(resp.content))
                        result.paste(tile_img, ((dx + 1) * tile_size, (dy + 1) * tile_size))
            
            map_path = os.path.join(STATIC_DIR, "map_base.png")
            result.save(map_path)
            return {"path": map_path, "lat": lat, "lon": lon, "city": self.get_location()["city"]}
        except Exception as e:
            print(f"[SpaceAPI] Map tile fetch failed: {e}")
            return None

    def get_weather_data(self):
        """Fetch weather data from Open-Meteo (free, no key needed)."""
        key = "weather"
        if self._is_cache_valid(key, expiry_hours=0.5):
            return self.cache[key]['data']
        
        try:
            loc = self.get_location()
            lat, lon = loc["lat"], loc["lon"]
            url = (f"https://api.open-meteo.com/v1/forecast?"
                   f"latitude={lat}&longitude={lon}"
                   f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
                   f"precipitation,weather_code,wind_speed_10m,wind_direction_10m,"
                   f"surface_pressure,cloud_cover"
                   f"&hourly=temperature_2m,wind_speed_10m,precipitation_probability"
                   f"&forecast_days=1&timezone=auto")
            res = requests.get(url, timeout=10).json()
            current = res.get("current", {})
            hourly = res.get("hourly", {})
            
            # Weather code to description
            codes = {0:"Clear Sky",1:"Mainly Clear",2:"Partly Cloudy",3:"Overcast",
                     45:"Foggy",48:"Rime Fog",51:"Light Drizzle",53:"Drizzle",
                     55:"Heavy Drizzle",61:"Light Rain",63:"Rain",65:"Heavy Rain",
                     71:"Light Snow",73:"Snow",75:"Heavy Snow",80:"Rain Showers",
                     81:"Heavy Showers",82:"Violent Showers",95:"Thunderstorm",
                     96:"Thunderstorm+Hail",99:"Severe Thunderstorm"}
            
            wcode = current.get("weather_code", 0)
            data = {
                "city": loc["city"],
                "temp": current.get("temperature_2m", 0),
                "feels_like": current.get("apparent_temperature", 0),
                "humidity": current.get("relative_humidity_2m", 0),
                "wind_speed": current.get("wind_speed_10m", 0),
                "wind_dir": current.get("wind_direction_10m", 0),
                "pressure": current.get("surface_pressure", 0),
                "clouds": current.get("cloud_cover", 0),
                "precipitation": current.get("precipitation", 0),
                "condition": codes.get(wcode, f"Code {wcode}"),
                "hourly_temp": hourly.get("temperature_2m", [])[:12],
                "hourly_wind": hourly.get("wind_speed_10m", [])[:12],
                "hourly_precip": hourly.get("precipitation_probability", [])[:12]
            }
            
            with self.lock:
                self.cache[key] = {
                    'data': data,
                    'expires': datetime.datetime.now() + datetime.timedelta(minutes=30)
                }
            return data
        except Exception as e:
            print(f"[SpaceAPI] Weather fetch failed: {e}")
            return None

    def get_apod(self):
        """Fetch NASA Astronomy Picture of the Day."""
        key = "apod"
        if self._is_cache_valid(key, expiry_hours=12):
            return self.cache[key]['data']
            
        try:
            url = f"https://api.nasa.gov/planetary/apod?api_key={NASA_API_KEY}"
            res = requests.get(url, timeout=10).json()
            
            data = {
                "title": res.get("title", ""),
                "explanation": res.get("explanation", ""),
                "url": res.get("url", ""),
                "hdurl": res.get("hdurl", "")
            }
            
            # Download image locally for the dashboard
            if data["url"]:
                img_data = requests.get(data["url"], timeout=10).content
                img_path = os.path.join(STATIC_DIR, "apod.jpg")
                with open(img_path, 'wb') as handler:
                    handler.write(img_data)
                data["local_path"] = "/static/apod.jpg"
                
            with self.lock:
                self.cache[key] = {
                    'data': data,
                    'expires': datetime.datetime.now() + datetime.timedelta(hours=12)
                }
            return data
        except Exception as e:
            print(f"[SpaceAPI] APOD fetch failed: {e}")
            return None

    def get_asteroid_threats(self):
        """Fetch today's Near Earth Objects (Asteroids) making a close approach."""
        key = "asteroids"
        if self._is_cache_valid(key, expiry_hours=6):
            return self.cache[key]['data']
            
        try:
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            url = f"https://api.nasa.gov/neo/rest/v1/feed?start_date={today}&end_date={today}&api_key={NASA_API_KEY}"
            res = requests.get(url, timeout=10).json()
            
            asteroids = res.get("near_earth_objects", {}).get(today, [])
            threats = []
            
            for a in asteroids:
                close_approach = a.get("close_approach_data", [{}])[0]
                threats.append({
                    "name": a.get("name", "Unknown"),
                    "is_hazardous": a.get("is_potentially_hazardous_asteroid", False),
                    "diameter_meters_max": a.get("estimated_diameter", {}).get("meters", {}).get("estimated_diameter_max", 0),
                    "miss_distance_km": float(close_approach.get("miss_distance", {}).get("kilometers", 0)),
                    "velocity_kph": float(close_approach.get("relative_velocity", {}).get("kilometers_per_hour", 0))
                })
                
            # Sort by distance
            threats = sorted(threats, key=lambda x: x["miss_distance_km"])
            
            with self.lock:
                self.cache[key] = {
                    'data': threats,
                    'expires': datetime.datetime.now() + datetime.timedelta(hours=6)
                }
            return threats
        except Exception as e:
            print(f"[SpaceAPI] Asteroids fetch failed: {e}")
            return []

    def get_telescope_image(self, telescope="jwst"):
        """Fetch latest image from Hubble or JWST via NASA Image Library."""
        import random
        key = f"telescope_{telescope}"
        if self._is_cache_valid(key, expiry_hours=6):
            return self.cache[key]['data']
            
        try:
            search_term = "james webb space telescope" if telescope == "jwst" else "hubble space telescope"
            url = f"https://images-api.nasa.gov/search?q={search_term}&media_type=image&page_size=20&year_start=2024"
            headers = {"User-Agent": "Jarvis-AI-Assistant/1.0"}
            res = requests.get(url, headers=headers, timeout=15).json()
            items = res.get("collection", {}).get("items", [])
            
            if not items:
                # Fallback to older images if 2024+ has none
                url = f"https://images-api.nasa.gov/search?q={search_term}&media_type=image&page_size=20&year_start=2023"
                res = requests.get(url, headers=headers, timeout=15).json()
                items = res.get("collection", {}).get("items", [])
            
            if not items:
                return None
            
            # Collect all valid items with preview images
            valid_items = []
            for item in items:
                item_data = item.get("data", [{}])[0]
                links = item.get("links", [])
                img_url = None
                for link in links:
                    if link.get("rel") == "preview":
                        img_url = link.get("href")
                        break
                if img_url:
                    valid_items.append((item_data, img_url))
            
            if not valid_items:
                return None
            
            # Pick a RANDOM image from the valid set
            item_data, img_url = random.choice(valid_items)
            
            data = {
                "title": item_data.get("title", "Deep Space Image"),
                "description": item_data.get("description", "")[:200],
                "date_created": item_data.get("date_created", "")[:10],
                "telescope": telescope.upper(),
                "img_url": img_url
            }
            
            # Download locally
            img_data = requests.get(img_url, headers=headers, timeout=15).content
            filename = f"telescope_{telescope}.jpg"
            img_path = os.path.join(STATIC_DIR, filename)
            with open(img_path, 'wb') as handler:
                handler.write(img_data)
            data["local_path"] = f"/static/{filename}"
            data["local_full_path"] = img_path
            
            with self.lock:
                self.cache[key] = {
                    'data': data,
                    'expires': datetime.datetime.now() + datetime.timedelta(hours=6)
                }
            return data
            
            return None
        except Exception as e:
            print(f"[SpaceAPI] Telescope ({telescope}) fetch failed: {e}")
            return None

    def get_upcoming_launches(self):
        """Fetch upcoming rocket launches."""
        key = "launches"
        if self._is_cache_valid(key, expiry_hours=1):
            return self.cache[key]['data']
            
        try:
            url = "https://ll.thespacedevs.com/2.2.0/launch/upcoming/?limit=3"
            headers = {"User-Agent": "Jarvis-AI-Assistant/1.0"}
            res = requests.get(url, headers=headers, timeout=10).json()
            
            launches = []
            for l in res.get("results", []):
                launches.append({
                    "name": l.get("name"),
                    "status": l.get("status", {}).get("name"),
                    "window_start": l.get("window_start"),
                    "provider": l.get("launch_service_provider", {}).get("name"),
                    "location": l.get("pad", {}).get("location", {}).get("name"),
                    "vidURL": l.get("vidURLs", [{"url": None}])[0].get("url") if l.get("vidURLs") else None
                })
                
            with self.lock:
                self.cache[key] = {
                    'data': launches,
                    'expires': datetime.datetime.now() + datetime.timedelta(hours=1)
                }
            return launches
        except Exception as e:
            print(f"[SpaceAPI] Launches fetch failed: {e}")
            return []

    def get_iss_position(self):
        """Fetch live ISS position and calculate distance from user."""
        try:
            res = requests.get("http://api.open-notify.org/iss-now.json", timeout=5).json()
            iss_lat = float(res["iss_position"]["latitude"])
            iss_lon = float(res["iss_position"]["longitude"])
            
            loc = self.get_location()
            user_lat = loc["lat"]
            user_lon = loc["lon"]
            
            # Haversine formula for distance
            import math
            R = 6371  # Earth radius in km
            dlat = math.radians(iss_lat - user_lat)
            dlon = math.radians(iss_lon - user_lon)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(user_lat)) * math.cos(math.radians(iss_lat)) * math.sin(dlon/2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            distance_km = R * c
            
            return {
                "iss_lat": iss_lat,
                "iss_lon": iss_lon,
                "user_city": loc["city"],
                "distance_km": round(distance_km, 1),
                "is_overhead": distance_km < 500  # Visible within ~500km radius
            }
        except Exception as e:
            print(f"[SpaceAPI] ISS fetch failed: {e}")
            return None

    def get_launch_countdown(self):
        """Fetch upcoming launches with precise countdown in seconds."""
        launches = self.get_upcoming_launches()
        if not launches:
            return []
        
        result = []
        for l in launches:
            try:
                window_start = l.get("window_start", "")
                if window_start:
                    # Parse ISO 8601 date
                    from dateutil import parser as dateparser
                    launch_time = dateparser.parse(window_start)
                    now = datetime.datetime.now(launch_time.tzinfo)
                    delta = (launch_time - now).total_seconds()
                    l["countdown_seconds"] = max(0, int(delta))
                    l["countdown_str"] = self._format_countdown(delta)
                else:
                    l["countdown_seconds"] = -1
                    l["countdown_str"] = "TBD"
            except Exception:
                l["countdown_seconds"] = -1
                l["countdown_str"] = "TBD"
            result.append(l)
        return result
    
    def _format_countdown(self, seconds):
        """Format seconds into T-minus countdown string."""
        if seconds <= 0:
            return "LAUNCHED"
        d = int(seconds // 86400)
        h = int((seconds % 86400) // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        if d > 0:
            return f"T-{d}d {h}h {m}m"
        elif h > 0:
            return f"T-{h}h {m}m {s}s"
        else:
            return f"T-{m}m {s}s"

    def set_wallpaper(self, image_path):
        """Set Windows desktop wallpaper."""
        try:
            ctypes.windll.user32.SystemParametersInfoW(20, 0, image_path, 0)
            return True
        except Exception as e:
            print(f"[SpaceAPI] Failed to set wallpaper: {e}")
            return False

# Global instance for easy importing
space_client = SpaceAPI()
