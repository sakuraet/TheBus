import json
import time
from pathlib import Path
from datetime import datetime

import requests

# ----------------------------
# CONFIG
# ----------------------------
API_KEY = "PUT_YOUR_KEY_HERE"

ALL_ROUTES_STOPS_BY_VARIANT_JSON = Path(
    r"C:\Users\1saku\Desktop\Mega Code\UHERO\Transportation\TheBus\data\routes\all_routes_stops_by_variant.json"
)

# Output file (written every minute)
OUT_JSON = Path(
    r"C:\Users\1saku\Desktop\Mega Code\UHERO\Transportation\TheBus\data\routes\route_307_arrivals.json"
)

ARRIVALS_URL = "http://api.thebus.org/arrivalsJSON"

# Route short name key in your JSON
ROUTE_KEY = "307"

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
# LOAD ROUTE 307 STOP IDS (DEDUPED ACROSS ALL INVARIANTS)
# ----------------------------
with open(ALL_ROUTES_STOPS_BY_VARIANT_JSON, "r", encoding="utf-8") as f:
    all_data = json.load(f)

if ROUTE_KEY not in all_data:
    raise KeyError(
        f"Route '{ROUTE_KEY}' not found in {ALL_ROUTES_STOPS_BY_VARIANT_JSON}\n"
        f"Example keys: {list(all_data.keys())[:30]}"
    )

variants = all_data[ROUTE_KEY].get("variants", [])

# Build a UNIQUE stop list across all invariants/directions so we never send identical requests
stop_ids = []
for v in variants:
    by_dir = v.get("by_direction", {})
    if not isinstance(by_dir, dict):
        continue
    for _dir_id, drec in by_dir.items():
        stops_ordered = drec.get("stops_ordered", [])
        if not isinstance(stops_ordered, list):
            continue
        for s in stops_ordered:
            if isinstance(s, dict):
                add_unique(stop_ids, s.get("stop_id", ""))

# Final dedupe pass (just to be safe)
deduped = []
for sid in stop_ids:
    add_unique(deduped, sid)
stop_ids = deduped

print(f"Loaded route '{ROUTE_KEY}' unique stops: {len(stop_ids)}")
print("First 15 stop IDs:", stop_ids[:15])

# ----------------------------
# MAIN LOOP (WRITE EVERY MINUTE)
# ----------------------------
session = requests.Session()

while True:
    cycle_start = datetime.now().isoformat()

    # Output is a LIST of per-stop API objects (outer structure unchanged),
    # only includes stops that have >=1 arrival with estimated == "1"
    output = []

    for stop_id in stop_ids:
        try:
            data = fetch_arrivals(session, stop_id)

            arrivals = to_list(data.get("arrivals", []))

            # Keep ONLY estimated == "1"
            gps_arrivals = [
                a for a in arrivals
                if str(a.get("estimated", "")).strip() == "1"
            ]

            # Only write the outer object if it has GPS-backed arrivals
            if gps_arrivals:
                data["arrivals"] = gps_arrivals
                output.append(data)

        except Exception as e:
            print(f"[WARN] stop {stop_id} failed: {type(e).__name__}: {e}")

        time.sleep(SLEEP_BETWEEN_CALLS)

    # Write file every minute (overwrite)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(
        f"Wrote {OUT_JSON} @ {cycle_start} | "
        f"stops_with_estimated1={len(output)} | stops_polled={len(stop_ids)}"
    )

    time.sleep(POLL_EVERY_SECONDS)
