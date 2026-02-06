import json
import time
from pathlib import Path
from datetime import datetime

import requests

# ----------------------------
# CONFIG
# ----------------------------
API_KEY = "EADED611-1025-4670-81C4-6892A9495490"

ALL_ROUTES_STOPS_BY_VARIANT_JSON = Path(
    r"C:\Users\1saku\Desktop\Mega Code\UHERO\Transportation\TheBus\data\routes\all_routes_stops_by_variant.json"
)

OUT_JSON = Path(
    r"C:\Users\1saku\Desktop\Mega Code\UHERO\Transportation\TheBus\data\routes\route_23_arrivals.json"
)

ARRIVALS_URL = "http://api.thebus.org/arrivalsJSON"

ROUTE_KEY = "23"

POLL_EVERY_SECONDS = 60
SLEEP_BETWEEN_CALLS = 0.15

# ----------------------------
# HELPERS
# ----------------------------
def add_unique(lst, value):
    s = str(value).strip()
    if s and s not in lst:
        lst.append(s)

def to_list(x):
    if isinstance(x, dict):
        return [x]
    if isinstance(x, list):
        return x
    return []

def fetch_arrivals(session: requests.Session, stop_id: str) -> dict:
    r = session.get(
        ARRIVALS_URL,
        params={"key": API_KEY, "stop": stop_id},
        timeout=15
    )
    r.raise_for_status()
    return r.json()

# ----------------------------
# LOAD ROUTE 23 STOP IDS (DEDUPED)
# ----------------------------
with open(ALL_ROUTES_STOPS_BY_VARIANT_JSON, "r", encoding="utf-8") as f:
    all_data = json.load(f)

if ROUTE_KEY not in all_data:
    raise KeyError(f"Route '{ROUTE_KEY}' not found.")

variants = all_data[ROUTE_KEY].get("variants", [])

stop_ids = []

for v in variants:
    by_dir = v.get("by_direction", {})
    for drec in by_dir.values():
        for s in drec.get("stops_ordered", []):
            add_unique(stop_ids, s.get("stop_id"))

# Final dedupe
stop_ids = list(dict.fromkeys(stop_ids))

print(f"Loaded route 23 unique stops: {len(stop_ids)}")

# ----------------------------
# MAIN LOOP
# ----------------------------
session = requests.Session()

while True:
    cycle_start = datetime.now().isoformat()

    output = []

    for stop_id in stop_ids:
        try:
            data = fetch_arrivals(session, stop_id)

            arrivals = to_list(data.get("arrivals", []))

            # ✅ ONLY route 23 AND GPS-backed
            filtered = [
                a for a in arrivals
                if str(a.get("estimated")) == "1"
                and str(a.get("route")).strip() == "23"
            ]

            if filtered:
                data["arrivals"] = filtered
                output.append(data)

        except Exception as e:
            print(f"[WARN] stop {stop_id}: {e}")

        time.sleep(SLEEP_BETWEEN_CALLS)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(
        f"Wrote route_23_arrivals.json @ {cycle_start} | "
        f"gps stops: {len(output)} / total stops: {len(stop_ids)}"
    )

    time.sleep(POLL_EVERY_SECONDS)
