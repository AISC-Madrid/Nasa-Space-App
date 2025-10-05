import json
import pandas as pd
from openaq import OpenAQ
from pathlib import Path

def get_measurements(sensor_ids, datetime_from, datetime_to, limit=1000, client=None, sensor_data=None):
    rows = []
    for id in sensor_ids:
        try:
            results = client.measurements.list(
                sensors_id=id,
                datetime_from=datetime_from,
                datetime_to=datetime_to,
                data="hours",
                limit=limit
            )

            data = results.json if isinstance(results.json, dict) else results.dict()  

            for measurement in data["results"]:
                row = {
                    "datetime": measurement["period"]["datetime_to"]["utc"],
                    "value": measurement["value"],
                    "sensor_id": id,
                    "parameter": sensor_data[sensor_data["id"] == id]["parameter"].values[0]
                }
                rows.append(row)

            df_measurements = pd.DataFrame(rows)



        except Exception as e:
            print(f"[ERROR] Sensor {id}: {e}")
    
    return df_measurements

