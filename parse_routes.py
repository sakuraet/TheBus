import json
from pathlib import Path

import pandas as pd
import requests

# ----------------------------
# CONFIG
# ----------------------------
API_KEY = "EADED611-1025-4670-81C4-6892A9495490"
GTFS_DIR = Path(r"C:\Users\1saku\Desktop\Mega Code\UHERO\Transportation\TheBus\data\thebus_gtfs")
ROUTES_TXT = GTFS_DIR / "routes.txt"

ROUTE_API_URL = "http://api.thebus.org/routeJSON"

OUT_OK = "route_api_dump_all.json"
OUT_EMPTY = "route_api_empty_or_failed.json"

TIMEOUT_SECS = 15
SLEEP_BETWEEN_CALLS_SECS = 0.15  # be polite; adjust if you want faster

# ----------------------------
# LOAD routes.txt
# ----------------------------
routes = pd.read_csv(ROUTES_TXT, dtype=str).fillna("")

# We'll use route_short_name as the route parameter for the Route API
route_short_names = (
    routes["route_short_name"]
    .astype(str)
    .str.strip()
    .replace("", pd.NA)
    .dropna()
    .unique()
    .tolist()
)

ok_results = {}       # route_short_name -> API JSON payload
empty_or_failed = []  # list of {route_short_name, reason, ...}

session = requests.Session()

for rsn in route_short_names:
    try:
        r = session.get(
            ROUTE_API_URL,
            params={"key": API_KEY, "route": rsn},
            timeout=TIMEOUT_SECS,
        )

        # If server error / not found, record it
        if r.status_code != 200:
            empty_or_failed.append({
                "route_short_name": rsn,
                "http_status": r.status_code,
                "url": r.url,
                "reason": f"HTTP {r.status_code}",
                "body_preview": r.text[:500],
            })
            continue

        # Parse JSON
        payload = r.json()

        # If API returns explicit errorMessage
        if isinstance(payload, dict) and payload.get("errorMessage"):
            empty_or_failed.append({
                "route_short_name": rsn,
                "http_status": r.status_code,
                "url": r.url,
                "reason": payload.get("errorMessage"),
                "payload": payload,
            })
            continue

        # If API returns empty route list like {"route": []}
        if isinstance(payload, dict) and payload.get("route") == []:
            empty_or_failed.append({
                "route_short_name": rsn,
                "http_status": r.status_code,
                "url": r.url,
                "reason": "Empty route response",
                "payload": payload,
            })
            continue

        # Otherwise store full JSON dump (exactly what API gave)
        ok_results[rsn] = payload

    except Exception as e:
        empty_or_failed.append({
            "route_short_name": rsn,
            "reason": f"Exception: {type(e).__name__}: {e}",
        })

    # small pause to reduce chance of rate limiting
    import time
    time.sleep(SLEEP_BETWEEN_CALLS_SECS)

# ----------------------------
# WRITE OUTPUT FILES
# ----------------------------
with open(OUT_OK, "w", encoding="utf-8") as f:
    json.dump(ok_results, f, indent=2)

with open(OUT_EMPTY, "w", encoding="utf-8") as f:
    json.dump(empty_or_failed, f, indent=2)

print(f"Saved OK routes JSON to: {OUT_OK}  (count={len(ok_results)})")
print(f"Saved empty/failed routes to: {OUT_EMPTY}  (count={len(empty_or_failed)})")
