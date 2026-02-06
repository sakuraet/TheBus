import json
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd

# ----------------------------
# CONFIG (edit these)
# ----------------------------
GTFS_DIR = Path(r"C:\Users\1saku\Desktop\Mega Code\UHERO\Transportation\TheBus\data\thebus_gtfs")
STOP_TIMES_TXT = GTFS_DIR / "stop_times.txt"

ALINE_ARRIVALS_JSON = Path(
    r"C:\Users\1saku\Desktop\Mega Code\UHERO\Transportation\TheBus\data\routes\route_23_arrivals.json"
)

OUT_CSV = Path(
    r"C:\Users\1saku\Desktop\Mega Code\UHERO\Transportation\TheBus\data\routes\route23_sched_vs_estimated.csv"
)
OUT_JSON = Path(
    r"C:\Users\1saku\Desktop\Mega Code\UHERO\Transportation\TheBus\data\routes\route23_sched_vs_estimated.json"
)

# If you only want GPS-backed estimates, keep this True (recommended)
GPS_ONLY = True  # keeps only arrivals where estimated == "1"

# ----------------------------
# HELPERS
# ----------------------------
def to_list(x):
    if isinstance(x, dict):
        return [x]
    if isinstance(x, list):
        return x
    return []

def parse_api_datetime(date_str: str, time_str: str) -> datetime:
    """
    API example:
      date = "2/5/2026"
      stopTime = "10:34 AM"
    """
    return datetime.strptime(f"{date_str} {time_str}", "%m/%d/%Y %I:%M %p")

def parse_gtfs_time_to_datetime(service_date: datetime.date, hhmmss: str) -> datetime:
    """
    GTFS stop_times arrival_time is HH:MM:SS and can exceed 24:00:00.
    Convert to datetime on service_date, rolling to next day if needed.
    """
    hhmmss = str(hhmmss).strip()
    parts = hhmmss.split(":")
    if len(parts) != 3:
        raise ValueError(f"Bad GTFS time: {hhmmss}")

    h = int(parts[0])
    m = int(parts[1])
    s = int(parts[2])

    day_offset = h // 24
    h = h % 24

    base = datetime(service_date.year, service_date.month, service_date.day, h, m, s)
    return base + timedelta(days=day_offset)

# ----------------------------
# LOAD GTFS stop_times and build lookup (trip_id, stop_id) -> scheduled arrival_time
# ----------------------------
stop_times = pd.read_csv(STOP_TIMES_TXT, dtype=str).fillna("")
needed_cols = {"trip_id", "stop_id", "arrival_time", "stop_sequence"}
missing_cols = needed_cols - set(stop_times.columns)
if missing_cols:
    raise ValueError(f"stop_times.txt missing columns: {missing_cols}")

stop_times = stop_times[list(needed_cols)].copy()
stop_times["stop_sequence"] = stop_times["stop_sequence"].astype(int)
stop_times = stop_times.sort_values(["trip_id", "stop_id", "stop_sequence"])

# If a trip somehow hits the same stop twice, keep the first occurrence (lowest sequence)
lookup = stop_times.drop_duplicates(subset=["trip_id", "stop_id"]).set_index(["trip_id", "stop_id"])

# ----------------------------
# LOAD A LINE arrivals JSON (list of per-stop API objects)
# ----------------------------
with open(ALINE_ARRIVALS_JSON, "r", encoding="utf-8") as f:
    payloads = json.load(f)

rows = []
missing_match = 0

for stop_payload in payloads:
    stop_id = str(stop_payload.get("stop", "")).strip()
    arrivals = to_list(stop_payload.get("arrivals", []))

    for a in arrivals:
        trip_id = str(a.get("trip", "")).strip()
        date_str = str(a.get("date", "")).strip()
        stop_time_str = str(a.get("stopTime", "")).strip()

        if not (stop_id and trip_id and date_str and stop_time_str):
            continue

        # Optional: only compare GPS-backed estimates
        if GPS_ONLY and str(a.get("estimated", "")).strip() != "1":
            continue

        key = (trip_id, stop_id)
        if key not in lookup.index:
            missing_match += 1
            continue

        scheduled_str = lookup.loc[key, "arrival_time"]

        # Build datetimes
        est_dt = parse_api_datetime(date_str, stop_time_str)
        sched_dt = parse_gtfs_time_to_datetime(est_dt.date(), scheduled_str)

        # Difference in minutes: estimated - scheduled
        diff_min = (est_dt - sched_dt).total_seconds() / 60.0

        rows.append({
            "date": date_str,
            "stop_id": stop_id,
            "trip_id": trip_id,
            "vehicle": str(a.get("vehicle", "")),
            "route": str(a.get("route", "")),
            "headsign": str(a.get("headsign", "")),
            "direction": str(a.get("direction", "")),
            "shape": str(a.get("shape", "")),
            "estimated_flag": str(a.get("estimated", "")),
            "scheduled_arrival_time": scheduled_str,      # HH:MM:SS from GTFS
            "estimated_stopTime": stop_time_str,          # "10:34 AM" from API
            "scheduled_datetime": sched_dt.isoformat(sep=" "),
            "estimated_datetime": est_dt.isoformat(sep=" "),
            "diff_minutes": round(diff_min, 2),           # e.g., +4.00 or -5.00
        })

# ----------------------------
# EXPORT CSV + JSON
# ----------------------------
df = pd.DataFrame(rows)
if not df.empty:
    df = df.sort_values(["date", "trip_id", "stop_id"])

OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUT_CSV, index=False)

# JSON export: list of row dicts
with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(rows, f, indent=2)

print(f"Wrote CSV : {OUT_CSV}")
print(f"Wrote JSON: {OUT_JSON}")
print(f"Matched rows: {len(rows)}")
print(f"Missing (trip_id, stop_id) matches in GTFS: {missing_match}")
