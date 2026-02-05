import pandas as pd
from pathlib import Path

# ----------------------------
# CONFIG
# ----------------------------
GTFS_DIR = Path(r"C:\Users\1saku\Desktop\Mega Code\UHERO\Transportation\TheBus\data\thebus_gtfs")
OUT_DIR  = Path(r"C:\Users\1saku\Desktop\Mega Code\UHERO\Transportation\TheBus\data\routes")

ROUTE_ID = "189"  # A Line route_id
ROUTE_SHORT_NAME = "A_LINE"  # used for filenames

OUT_DIR.mkdir(parents=True, exist_ok=True)

# ----------------------------
# LOAD GTFS FILES
# ----------------------------
trips = pd.read_csv(GTFS_DIR / "trips.txt", dtype=str)
stop_times = pd.read_csv(GTFS_DIR / "stop_times.txt", dtype=str)
stops = pd.read_csv(GTFS_DIR / "stops.txt", dtype=str)

print("stops.txt columns:", list(stops.columns))

# ----------------------------
# STEP 1: FILTER TO THIS ROUTE'S TRIPS
# ----------------------------
a_trips = trips[trips["route_id"] == ROUTE_ID].copy()

if "direction_id" not in a_trips.columns:
    raise ValueError("direction_id not found in trips.txt (can't split inbound/outbound).")

print("\nA Line trips per direction_id:")
print(a_trips.groupby("direction_id").size())

# ----------------------------
# STEP 2: PICK ONE REPRESENTATIVE TRIP PER direction_id
#   - Prefer most common shape_id within each direction (if shape_id exists)
# ----------------------------
def pick_representative_trip(df: pd.DataFrame) -> pd.Series:
    df = df.copy()
    if "shape_id" in df.columns and df["shape_id"].notna().any():
        top_shape = df["shape_id"].value_counts().idxmax()
        df = df[df["shape_id"] == top_shape]
    return df.sort_values("trip_id").iloc[0]  # stable pick

representative_trips: dict[str, dict[str, str]] = {}

for direction in ["0", "1"]:
    df_dir = a_trips[a_trips["direction_id"] == direction]
    if df_dir.empty:
        print(f"\nNo trips found for direction_id={direction}")
        continue

    rep = pick_representative_trip(df_dir)

    representative_trips[direction] = {
        "route_id": ROUTE_ID,
        "direction_id": direction,
        "trip_id": rep["trip_id"],
        "headsign": rep.get("trip_headsign", "N/A"),
        "shape_id": rep.get("shape_id", "N/A"),
    }

# ----------------------------
# LABEL EASTBOUND/WESTBOUND USING DESTINATION SIGN TEXT
# (Your route doc says:
#  EASTBOUND sign: "A LINE U.H. MANOA VIA DOWNTOWN HNL"
#  WESTBOUND sign: "A LINE AHUA LAGOON DRIVE SKYLINE STATION")
# ----------------------------
def bound_label(headsign: str) -> str:
    hs = (headsign or "").upper()
    # EASTBOUND → toward UH Mānoa / Sinclair, often mentions MANOA/DOWNTOWN
    if ("MANOA" in hs) or ("SINCLAIR" in hs) or ("DOWNTOWN" in hs) or ("U.H." in hs) or ("UNIVERSITY" in hs):
        return "EASTBOUND"
    # WESTBOUND → toward Ahua/Lagoon/Skyline station
    if ("AHUA" in hs) or ("LAGOON" in hs) or ("SKYLINE" in hs) or ("STATION" in hs):
        return "WESTBOUND"
    return "UNKNOWN"

for direction, info in representative_trips.items():
    info["bound"] = bound_label(info["headsign"])

# ----------------------------
# STEP 3: EXTRACT ORDERED STOPS FOR EACH DIRECTION
#   (robust to feeds that don't include stop_code)
# ----------------------------
route_stops: dict[str, pd.DataFrame] = {}

for direction, info in representative_trips.items():
    trip_id = info["trip_id"]

    st = stop_times[stop_times["trip_id"] == trip_id].copy()
    if st.empty:
        print(f"\nWARNING: stop_times has no rows for trip_id={trip_id} (direction_id={direction})")
        continue

    st["stop_sequence"] = st["stop_sequence"].astype(int)
    st = st.sort_values("stop_sequence")

    merged = st.merge(stops, on="stop_id", how="left")

    wanted = ["stop_sequence", "stop_id", "stop_code", "stop_name", "stop_lat", "stop_lon"]
    existing = [c for c in wanted if c in merged.columns]
    stops_df = merged[existing].reset_index(drop=True)

    # Attach metadata columns so each CSV is self-contained
    stops_df.insert(0, "route_id", ROUTE_ID)
    stops_df.insert(1, "route_short_name", ROUTE_SHORT_NAME)
    stops_df.insert(2, "direction_id", info["direction_id"])
    stops_df.insert(3, "bound", info["bound"])
    stops_df.insert(4, "trip_id", info["trip_id"])
    stops_df.insert(5, "headsign", info["headsign"])
    stops_df.insert(6, "shape_id", info["shape_id"])

    route_stops[direction] = stops_df

# ----------------------------
# SAVE METADATA CSV (one row per direction_id)
# ----------------------------
metadata_df = pd.DataFrame(list(representative_trips.values()))
meta_out = OUT_DIR / f"{ROUTE_SHORT_NAME}_route_metadata.csv"
metadata_df.to_csv(meta_out, index=False)
print(f"\nSaved route metadata: {meta_out}")

# ----------------------------
# OUTPUT (preview) + SAVE STOPS
# ----------------------------
for direction, stops_df in route_stops.items():
    info = representative_trips[direction]

    print("\n" + "=" * 60)
    print(f"direction_id={direction}  bound={info['bound']}")
    print("Trip ID:", info["trip_id"])
    print("Headsign:", info["headsign"])
    print("Shape ID:", info["shape_id"])
    print("-" * 60)
    print(stops_df[["stop_sequence", "stop_id", "stop_name", "stop_lat", "stop_lon"]].head(15).to_string(index=False))
    print(f"\nTotal stops in this direction: {len(stops_df)}")

    out_path = OUT_DIR / f"{ROUTE_SHORT_NAME}_{info['bound']}_direction_{direction}_stops.csv"
    stops_df.to_csv(out_path, index=False)
    print(f"\nSaved: {out_path}")

# ----------------------------
# OPTIONAL: sanity check if UNKNOWN happened
# ----------------------------
unknown = [d for d, info in representative_trips.items() if info.get("bound") == "UNKNOWN"]
if unknown:
    print("\nWARNING: Could not confidently label EASTBOUND/WESTBOUND for direction_id(s):", unknown)
    for d in unknown:
        print(f"  direction_id={d} headsign={representative_trips[d]['headsign']}")
