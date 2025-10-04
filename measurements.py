import json
import pandas as pd
from openaq import OpenAQ
from pathlib import Path

sensor_data = pd.read_csv("data/output/sensors_csv")
sensor_ids = sensor_data["id"]
API_KEY = "99f6eb5b9e02d83dafed5d2bf8352a22512e0066f0f7e071edb0b07cf2fe4850"

for id in sensor_ids:
    with OpenAQ(api_key=API_KEY) as client:
        results = client.measurements.list(sensors_id=id, data="hours", limit=1000)

        # Convert results to a JSON-serializable dict
        data = results.json if isinstance(results.json, dict) else results.dict()


