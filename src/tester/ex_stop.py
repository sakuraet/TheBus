import requests
import json

API_KEY = "EADED611-1025-4670-81C4-6892A9495490"
STOP_ID = "983"  # Sinclair Circle

URL = "http://api.thebus.org/arrivalsJSON/"

params = {
    "key": API_KEY,
    "stop": STOP_ID
}

response = requests.get(URL, params=params, timeout=15)
response.raise_for_status()

data = response.json()

print(json.dumps(data, indent=2))
