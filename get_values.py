from euclidean import nearest_location, euclidean_distance
from measurements import get_measurements
import pandas as pd
from openaq import OpenAQ

locations_path = "data/output/locations.csv"
sensors_path = "data/output/sensors.csv"

sensor_data = pd.read_csv(sensors_path)

coordiates = (33.793715,-118.171615)
nearest_location_id = nearest_location(coordiates, locations_path)
print(f"Nearest location ID: {nearest_location_id}")

sensor_ids = sensor_data[sensor_data["location_id"] == nearest_location_id]["id"].tolist()
datetime_from = "2025-10-04T00:00:00Z"
datetime_to = "2025-10-04T23:59:59Z"
limit = 1000
with OpenAQ(api_key="a19444b8b983c4def60c98df1010f162da2bbffbb1f494ccbffee228068cbef7") as client:
    measurements = get_measurements(sensor_ids, datetime_from, datetime_to, limit, client, sensor_data)
print(measurements)