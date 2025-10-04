import json
import pandas as pd

# Load JSON
with open("data/output/result.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Extract locations
locations = data.get("results", [])
rows = []
for location in locations:
    location_id = location["id"]
    for sensor in location["sensors"]:
        row = {
            "id": sensor["id"],
            "location_id": location_id,
            "parameter": sensor["parameter"]["name"]
        }
        rows.append(row)

# Create DataFrame
df_locations = pd.DataFrame(rows)

# Save to CSV
df_locations.to_csv("data/output/sensors.csv", index=False, encoding="utf-8")

print("CSV saved at data/output/locations.csv")
