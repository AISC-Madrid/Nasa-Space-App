import pandas as pd

def get_measurements(sensor_ids, datetime_from, datetime_to, limit=1000, client=None, sensor_data=None):
    rows = []
    
    if not sensor_ids:
        return pd.DataFrame()  # early return if no sensors

    for sensor_id in sensor_ids:
        try:
            results = client.measurements.list(
                sensors_id=sensor_id,
                datetime_from=datetime_from,
                datetime_to=datetime_to,
                data="hours",
                limit=limit
            )

            # Make sure we get a dict from the results
            if hasattr(results, "json"):
                data = results.json if isinstance(results.json, dict) else results.json()
            else:
                data = results.dict() if hasattr(results, "dict") else {}

            for measurement in data.get("results", []):
                row = {
                    "datetime": measurement["period"]["datetime_to"]["utc"],
                    "value": measurement["value"],
                    "sensor_id": sensor_id,
                    "parameter": sensor_data[sensor_data["id"] == sensor_id]["parameter"].values[0]
                }
                rows.append(row)

        except Exception as e:
            print(f"[ERROR] Sensor {sensor_id}: {e}")

    # Always return a DataFrame, even if empty
    df_measurements = pd.DataFrame(rows)
    return df_measurements
