"""Collect one round of traffic + weather data and append it to data/traffic_log.csv.
Run by GitHub Actions every 10 minutes (see .github/workflows/collect.yml)."""
import csv, os, sys
from datetime import datetime
from zoneinfo import ZoneInfo
import requests

API_KEY = os.environ.get("TOMTOM_API_KEY")
if not API_KEY:
    sys.exit("TOMTOM_API_KEY is not set")

OUT = "data/traffic_log.csv"
POINTS = {
    "Pimpri_Chowk":  (18.6298, 73.7997),
    "Chinchwad":     (18.6425, 73.7978),
    "Nashik_Phata":  (18.6007, 73.8189),
    "Wakad":         (18.5984, 73.7608),
    "Hinjewadi_Ph1": (18.5912, 73.7389),
    "Shivajinagar":  (18.5308, 73.8475),
}
COLUMNS = ["point", "lat", "lon", "current_speed", "free_flow_speed", "current_travel_time",
           "free_flow_travel_time", "confidence", "road_closure",
           "temperature_2m", "precipitation", "wind_speed_10m", "timestamp"]

TOMTOM_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

ts = datetime.now(ZoneInfo("Asia/Kolkata")).replace(tzinfo=None, microsecond=0).isoformat(sep=" ")

# weather (centre of all points)
clat = sum(v[0] for v in POINTS.values()) / len(POINTS)
clon = sum(v[1] for v in POINTS.values()) / len(POINTS)
try:
    r = requests.get(WEATHER_URL, params={"latitude": clat, "longitude": clon, "timezone": "Asia/Kolkata",
                     "current": "temperature_2m,precipitation,wind_speed_10m"}, timeout=20)
    r.raise_for_status()
    c = r.json()["current"]
    weather = {k: c[k] for k in ("temperature_2m", "precipitation", "wind_speed_10m")}
except Exception as e:
    print("weather error:", e)
    weather = {"temperature_2m": "", "precipitation": "", "wind_speed_10m": ""}

rows = []
for name, (lat, lon) in POINTS.items():
    try:
        r = requests.get(TOMTOM_URL, params={"key": API_KEY, "point": f"{lat},{lon}", "unit": "KMPH"}, timeout=20)
        r.raise_for_status()
        d = r.json()["flowSegmentData"]
        rows.append({"point": name, "lat": lat, "lon": lon,
                     "current_speed": d["currentSpeed"], "free_flow_speed": d["freeFlowSpeed"],
                     "current_travel_time": d["currentTravelTime"], "free_flow_travel_time": d["freeFlowTravelTime"],
                     "confidence": d.get("confidence", ""), "road_closure": int(d.get("roadClosure", False)),
                     **weather, "timestamp": ts})
    except Exception as e:
        print(f"traffic error at {name}: {e}")

if not rows:
    sys.exit("No rows collected this round")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
new_file = not os.path.exists(OUT)
with open(OUT, "a", newline="") as f:
    w = csv.DictWriter(f, fieldnames=COLUMNS)
    if new_file:
        w.writeheader()
    w.writerows(rows)
print(f"[{ts}] saved {len(rows)} rows")
