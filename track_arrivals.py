import time
import requests
import json
from collections import defaultdict
from datetime import datetime

API_KEY = "EADED611-1025-4670-81C4-6892A9495490"
ARRIVALS_URL = "http://api.thebus.org/arrivalsJSON"

ANCHOR_STOPS = {
    "lagoon_dr": "4852",
    "south_king": "4858",
    "sinclair": "983"
}

OUTPUT_FILE = "a_line_gps_realtime.json"
POLL_SECONDS = 60

def fetch_arrivals(stop_id: str) -> dict:
    r = requests.get(
        ARRIVALS_URL,
        params={"key": API_KEY, "stop": stop_id},
        timeout=15
    )
    r.raise_for_status()
    return r.json()

def to_list(x):
    if isinstance(x, dict):
        return [x]
    if isinstance(x, list):
        return x
    return []

def is_gps_backed(a: dict) -> bool:
    # GPS-backed per your Sinclair example:
    # estimated == "1", real vehicle number, nonzero lat/lon
    est = str(a.get("estimated", "")).strip()
    vehicle = str(a.get("vehicle", "")).strip()
    lat = str(a.get("latitude", "")).strip()
    lon = str(a.get("longitude", "")).strip()

    return (
        est == "1"
        and vehicle not in ("", "???")
        and lat not in ("", "0")
        and lon not in ("", "0")
    )

def main():
    while True:
        vehicles = defaultdict(list)

        for stop_name, stop_id in ANCHOR_STOPS.items():
            data = fetch_arrivals(stop_id)
            arrivals = to_list(data.get("arrivals", []))

            for a in arrivals:
                # Only Line A
                if str(a.get("route", "")).strip().upper() != "A":
                    continue

                # Only GPS-backed vehicles
                if not is_gps_backed(a):
                    continue

                vehicle_id = str(a.get("vehicle")).strip()

                vehicles[vehicle_id].append({
                    "stop_name": stop_name,
                    "stop_id": stop_id,
                    "direction": a.get("direction"),
                    "headsign": a.get("headsign"),
                    "trip": a.get("trip"),
                    "shape": a.get("shape"),
                    "stopTime": a.get("stopTime"),
                    "date": a.get("date"),
                    "latitude": a.get("latitude"),
                    "longitude": a.get("longitude"),
                    "canceled": a.get("canceled")
                })

            time.sleep(0.2)

        output = {
            "generated_at": datetime.now().isoformat(),
            "route": "A",
            "anchor_stops": ANCHOR_STOPS,
            "gps_only": True,
            "vehicles": vehicles
        }

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)

        print(f"Wrote {OUTPUT_FILE} @ {output['generated_at']} (gps vehicles: {len(vehicles)})")

        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    main()
