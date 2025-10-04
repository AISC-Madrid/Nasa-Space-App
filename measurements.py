import json
import pandas as pd
from openaq import OpenAQ
from pathlib import Path

sensor_data = pd.read_csv("data/output/sensors.csv")
sensor_ids = sensor_data["id"]
API_KEY = "f0d2b3f27388d5ce43efa743fe482a5ba6606d90a1ccb425e7a3ea0f51475a57"

with OpenAQ(api_key=API_KEY) as client:
    for sensor_id in sensor_ids:
        try:
            results = client.measurements.list(
                sensors_id=sensor_id,
                datetime_from="2025-09-01",
                datetime_to="2025-09-30",
                data="hours"
            )


        except Exception as e:
            print(f"[ERROR] Sensor {sensor_id}: {e}")


