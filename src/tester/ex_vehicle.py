import requests
import json

API_KEY = "EADED611-1025-4670-81C4-6892A9495490"
VEHICLE = "4056"
URL = "http://api.thebus.org/vehicle.JSON/"

print(f"Getting data for vehicle {VEHICLE}")
print("=" * 60)

r = requests.get(URL, params={"key": API_KEY, "num": VEHICLE})

print("HTTP status:", r.status_code)
print("URL:", r.url)
print("\nJSON Response:")
print("=" * 60)

try:
    print(json.dumps(r.json(), indent=2))
except Exception as e:
    print("Failed to parse JSON:")
    print(r.text)