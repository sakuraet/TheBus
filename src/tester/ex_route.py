import requests
import json

API_KEY = "EADED611-1025-4670-81C4-6892A9495490"
# route_id/num is not the route_id in the gtfs instead use route_short_name
ROUTE_ID = "551"  

URL = "http://api.thebus.org/routeJSON"

r = requests.get(URL, params={"key": API_KEY, "route": ROUTE_ID})

print("HTTP status:", r.status_code)
print("URL:", r.url)

try:
    print(json.dumps(r.json(), indent=2))
except Exception:
    print(r.text)
