import json
from pathlib import Path
import pandas as pd

# ------------------------------------------------------------
# CONFIG (change these if needed)
# ------------------------------------------------------------
ALL_ROUTES_JSON = Path(r"C:\Users\1saku\Desktop\Mega Code\UHERO\Transportation\TheBus\data\routes\all_routes.json")

GTFS_DIR = Path(r"C:\Users\1saku\Desktop\Mega Code\UHERO\Transportation\TheBus\data\thebus_gtfs")
TRIPS_TXT = GTFS_DIR / "trips.txt"
STOP_TIMES_TXT = GTFS_DIR / "stop_times.txt"
STOPS_TXT = GTFS_DIR / "stops.txt"
ROUTES_TXT = GTFS_DIR / "routes.txt"

OUT_JSON = Path(r"C:\Users\1saku\Desktop\Mega Code\UHERO\Transportation\TheBus\data\routes\all_routes_stops_by_variant.json")
OUT_CSV  = Path(r"C:\Users\1saku\Desktop\Mega Code\UHERO\Transportation\TheBus\data\routes\all_routes_stops_by_variant.csv")
OUT_MISSING_JSON = Path(r"C:\Users\1saku\Desktop\Mega Code\UHERO\Transportation\TheBus\data\routes\missing_variants.json")

# How to label direction_id. GTFS does NOT guarantee 0=outbound, 1=inbound universally,
# but this is a common convention. Keep both direction_id and this label.
DIRECTION_LABEL = {"0": "outbound", "1": "inbound"}

# ------------------------------------------------------------
# LOAD INPUTS
# ------------------------------------------------------------
with open(ALL_ROUTES_JSON, "r", encoding="utf-8") as f:
    all_routes = json.load(f)

routes = pd.read_csv(ROUTES_TXT, dtype=str).fillna("")
trips = pd.read_csv(TRIPS_TXT, dtype=str).fillna("")
stop_times = pd.read_csv(STOP_TIMES_TXT, dtype=str).fillna("")
stops = pd.read_csv(STOPS_TXT, dtype=str).fillna("")

stop_times["stop_sequence"] = stop_times["stop_sequence"].astype(int)

# Quick lookup: GTFS route_id by route_short_name (just in case you want it)
route_short_to_ids = (
    routes.groupby(routes["route_short_name"].str.strip())["route_id"]
    .apply(lambda s: sorted(set(s.astype(str))))
    .to_dict()
)

# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------
def pick_representative_trip_id(df: pd.DataFrame) -> str:
    """Pick a stable trip_id for a (shape_id, direction_id) group."""
    return df.sort_values("trip_id").iloc[0]["trip_id"]

def get_ordered_stops_for_trip(trip_id: str) -> pd.DataFrame:
    """Return ordered stops for a trip_id, with stop metadata joined."""
    st = stop_times[stop_times["trip_id"] == trip_id].copy()
    st = st.sort_values("stop_sequence")
    merged = st.merge(stops, on="stop_id", how="left", suffixes=("", "_stop"))
    return merged

# ------------------------------------------------------------
# BUILD OUTPUTS
# ------------------------------------------------------------
out_json = {}
csv_rows = []
missing = []

for route_short_name, route_obj in all_routes.items():
    # route_short_name is the key in your all_routes.json ("1", "2", "A", etc.)
    # route_obj contains routeName, routeID, and route (variants list)
    route_id_from_api = str(route_obj.get("routeID", "")).strip()
    variants = route_obj.get("route", [])

    out_json[route_short_name] = {
        "routeName": route_obj.get("routeName"),
        "routeID": route_id_from_api,
        "variants": []
    }

    for v in variants:
        shape_id = str(v.get("shapeID", "")).strip()
        headsign = v.get("headsign", "")
        first_stop = v.get("firstStop", "")
        route_num = v.get("routeNum", route_short_name)

        if not shape_id:
            missing.append({
                "route_short_name": route_short_name,
                "routeID": route_id_from_api,
                "reason": "variant missing shapeID",
                "variant": v
            })
            continue

        # Filter trips by shape_id (and route_id if it matches; if not, fall back to shape only)
        t_shape = trips[trips["shape_id"].astype(str).str.strip() == shape_id].copy()

        if t_shape.empty:
            missing.append({
                "route_short_name": route_short_name,
                "routeID": route_id_from_api,
                "shape_id": shape_id,
                "reason": "no trips found with this shape_id",
                "variant": v
            })
            continue

        # If API routeID exists in GTFS trips route_id, enforce it; otherwise skip enforcement
        if route_id_from_api and (t_shape["route_id"] == route_id_from_api).any():
            t_shape = t_shape[t_shape["route_id"] == route_id_from_api].copy()

        if t_shape.empty:
            missing.append({
                "route_short_name": route_short_name,
                "routeID": route_id_from_api,
                "shape_id": shape_id,
                "reason": "shape_id found but none match route_id from API",
                "variant": v
            })
            continue

        # Split by direction_id (0/1)
        if "direction_id" not in t_shape.columns:
            missing.append({
                "route_short_name": route_short_name,
                "routeID": route_id_from_api,
                "shape_id": shape_id,
                "reason": "direction_id not present in trips.txt",
                "variant": v
            })
            continue

        dir_groups = t_shape.groupby("direction_id", dropna=False)

        variant_record = {
            "routeNum": route_num,
            "shapeID": shape_id,
            "headsign": headsign,
            "firstStop": first_stop,
            "by_direction": {}
        }

        for direction_id, gdir in dir_groups:
            direction_id = str(direction_id).strip()
            rep_trip_id = pick_representative_trip_id(gdir)

            merged = get_ordered_stops_for_trip(rep_trip_id)
            if merged.empty:
                missing.append({
                    "route_short_name": route_short_name,
                    "routeID": route_id_from_api,
                    "shape_id": shape_id,
                    "direction_id": direction_id,
                    "trip_id": rep_trip_id,
                    "reason": "no stop_times rows for representative trip_id",
                    "variant": v
                })
                continue

            # Build ordered stops list for JSON
            stop_list = []
            for _, row in merged.iterrows():
                stop_entry = {
                    "stop_sequence": int(row["stop_sequence"]),
                    "stop_id": row.get("stop_id", ""),
                    "stop_name": row.get("stop_name", ""),
                    "stop_lat": row.get("stop_lat", ""),
                    "stop_lon": row.get("stop_lon", "")
                }
                if "stop_code" in merged.columns:
                    stop_entry["stop_code"] = row.get("stop_code", "")
                stop_list.append(stop_entry)

                # Add CSV row
                csv_rows.append({
                    "route_short_name": route_short_name,
                    "route_id": route_id_from_api,
                    "routeNum": route_num,
                    "shape_id": shape_id,
                    "headsign": headsign,
                    "firstStop": first_stop,
                    "direction_id": direction_id,
                    "direction_label": DIRECTION_LABEL.get(direction_id, f"direction_{direction_id}"),
                    "representative_trip_id": rep_trip_id,
                    "stop_sequence": int(row["stop_sequence"]),
                    "stop_id": row.get("stop_id", ""),
                    "stop_name": row.get("stop_name", ""),
                    "stop_lat": row.get("stop_lat", ""),
                    "stop_lon": row.get("stop_lon", "")
                })

            variant_record["by_direction"][direction_id] = {
                "direction_label": DIRECTION_LABEL.get(direction_id, f"direction_{direction_id}"),
                "representative_trip_id": rep_trip_id,
                "num_trips_in_this_direction": int(len(gdir)),
                "stops_ordered": stop_list
            }

        out_json[route_short_name]["variants"].append(variant_record)

# ------------------------------------------------------------
# WRITE FILES
# ------------------------------------------------------------
OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(out_json, f, indent=2)

df_csv = pd.DataFrame(csv_rows)
df_csv.to_csv(OUT_CSV, index=False)

with open(OUT_MISSING_JSON, "w", encoding="utf-8") as f:
    json.dump(missing, f, indent=2)

print("Saved JSON:", OUT_JSON)
print("Saved CSV :", OUT_CSV)
print("Saved missing report:", OUT_MISSING_JSON)
print("Routes processed:", len(out_json))
print("CSV rows:", len(df_csv))
print("Missing items:", len(missing))
