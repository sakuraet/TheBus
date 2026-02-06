import json
import time
from pathlib import Path
from datetime import datetime

import requests

# ----------------------------
# CONFIG
# ----------------------------
API_KEY = "PUT_YOUR_KEY_HERE"

# Your generated file that contains routes -> variants -> by_direction -> stops_ordered
ALL_ROUTES_STOPS_BY_VARIANT_JSON = Path(
    r"C:\Users\1saku\Desktop\Mega Code\UHERO\Transportation\TheBus\data\routes\all_routes_stops_by_variant.json"
)

# Output file (written every minute)
OUT_JSON = Path(
    r"C:\Users\1saku\Desktop\Mega Code\UHERO\Transportation\TheBus\data\routes\aline_arrivals.json"
)

ARRIVALS_URL = "http://api.thebus.org/arrivalsJSON/"

# Route key in your JSON
ROUTE_KEY = "A LINE"   # <-- per your instruction

# Dedupe Sinclair (only ping once per minute)
SINCLAIR_STOP_ID = "983"

POLL_EVERY_SECONDS = 60
SLEEP_BETWEEN_CALLS = 0.15

# ----------------------------
# LOAD A LINE STOPS FROM all_routes_stops_by_variant.json
# ----------------------------
with open(ALL_ROUTES_STOPS_BY_VARIANT_JSON, "r", encoding="utf-8") as f:
    all_data = json.load(f)

if ROUTE_KEY not in all_data:
    raise KeyError(
        f"Route '{ROUTE_KEY}' not found in all_routes_stops_by_variant.json.\n"
        f"Example keys: {list(all_data.keys())[:20]}"
    )

a_route = all_data[ROUTE_KEY]
variants = a_route.get("variants", [])

def add_unique(lst, x):
    x = str(x).strip()
    if x and x not in lst:
        lst.append(x)

# Collect unique stop_ids from BOTH outbound and inbound across ALL invariants (shape variants)
all_stop_ids = []

for v in variants:
    by_dir = v.get("by_direction", {})
    for _direction_id, drec in by_dir.items():
        for s in drec.get("stops_ordered", []):
            add_unique(all_stop_ids, s.get("stop_id", ""))

# Ensure Sinclair only appears once; we'll poll it once per cycle anyway
all_stop_ids = [sid for sid in all_stop_ids if sid != SINCLAIR_STOP_ID]
all_stop_ids.insert(0, SINCLAIR_STOP_ID)  # optional: poll Sinclair first

print(f"Loaded route '{ROUTE_KEY}'")
print("Total unique stops to poll:", len(all_stop_ids))

# ----------------------------
# ARRIVALS FETCH
# ----------------------------
session = requests.Session()

def fetch_arrivals(stop_id: str) -> dict:
    r = session.get(
        ARRIVALS_URL,
        params={"key": API_KEY, "stop": stop_id},
        timeout=15
    )
    r.raise_for_status()
    return r.json()

def as_list(x):
    if isinstance(x, list):
        return x
    if isinstance(x, dict):
        return [x]
    return []

# ----------------------------
# MAIN LOOP (writes every minute)
# ----------------------------
while True:
    stop_payloads = []  # list of per-stop payloads, matching arrivalsJSON structure

    for stop_id in all_stop_ids:
        try:
            data = fetch_arrivals(stop_id)

            arrivals = as_list(data.get("arrivals", []))

            # Only write arrivals that have GPS (estimated == "1")
            gps_arrivals = [
                a for a in arrivals
                if str(a.get("estimated", "")).strip() == "1"
            ]

            # Only include this stop object if it has at least one GPS arrival
            if gps_arrivals:
                stop_payloads.append({
                    "stop": str(data.get("stop", stop_id)),
                    "timestamp": data.get("timestamp", ""),
                    "arrivals": gps_arrivals
                })

        except Exception as e:
            print(f"[WARN] stop {stop_id} failed: {type(e).__name__}: {e}")

        time.sleep(SLEEP_BETWEEN_CALLS)

    # Write aline_arrivals.json every minute
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(stop_payloads, f, indent=2)

    print(f"Wrote {OUT_JSON} | stops_with_gps_arrivals={len(stop_payloads)} | {datetime.now().isoformat()}")

    time.sleep(POLL_EVERY_SECONDS)
