import requests
import json

API_KEY = "EADED611-1025-4670-81C4-6892A9495490"
VEHICLES = ["892", "4056", "4050"]

URL = "http://api.thebus.org/vehicleJSON/"  # correct JSON endpoint

for v in VEHICLES:
    print("\n" + "=" * 60)
    print(f"Vehicle {v}")

    r = requests.get(URL, params={"key": API_KEY, "num": v})
    print("HTTP status:", r.status_code)
    print("URL:", r.url)

    # dump raw response body
    try:
        print(json.dumps(r.json(), indent=2))
    except Exception:
        print(r.text)
