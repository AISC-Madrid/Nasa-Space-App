import json
import pandas as pd

# Load JSON
with open("data/output/result.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Extract locations
locations = data.get("results", [])
rows = []
for location in locations:
    row = {
        "id": location.get("id"),
        "name": location.get("name"),
        "latitude": location["coordinates"]["latitude"],
        "longitude": location["coordinates"]["longitude"],
    }
    rows.append(row)

# Create DataFrame
df_locations = pd.DataFrame(rows)

# Save to CSV
df_locations.to_csv("data/output/locations.csv", index=False, encoding="utf-8")

print("CSV saved at data/output/locations.csv")
