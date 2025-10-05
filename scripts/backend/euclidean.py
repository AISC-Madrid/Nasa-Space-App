import pandas as pd

def euclidean_distance(point1, point2):
    return ((point1[0] - point2[0]) ** 2 + (point1[1] - point2[1]) ** 2) ** 0.5


def nearest_location(input_location, location_csv):
    min_distance = float("inf")
    nearest_location = None
    locations_df = pd.read_csv(location_csv)
    locations = list(zip(locations_df["latitude"], locations_df["longitude"]))

    for latitude, longitude in locations:
        distance = euclidean_distance(input_location, (latitude, longitude))
        if distance < min_distance:
            min_distance = distance
            nearest_location = (latitude, longitude)
            nearest_location_id = locations_df[(locations_df["latitude"] == latitude) & (locations_df["longitude"] == longitude)]["id"].values[0]
    
    return nearest_location_id


