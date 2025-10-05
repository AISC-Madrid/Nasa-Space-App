import requests

def get_air_quality_summary(lat, lon):
    """
    Fetch air quality data from OpenAQ for given latitude and longitude.
    Returns latest measurements for all pollutants.
    """
    url = "https://api.openaq.org/v2/latest"
    params = {
        "coordinates": f"{lat},{lon}",
        "radius": 10000,  # 10 km radius
        "limit": 100
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        return {"error": "Failed to fetch data from OpenAQ"}

    data = response.json()
    results = data.get("results", [])

    latest_values = {}
    for station in results:
        for measurement in station.get("measurements", []):
            param = measurement.get("parameter").upper()
            value = measurement.get("value")
            unit = measurement.get("unit")
            latest_values[param] = f"{value} {unit}"

    # Optional: simple "pollution percentage" estimate
    # For demo purposes, we'll just use PM2.5 if available
    pm25_value = None
    if "PM25" in latest_values:
        pm25_value = float(latest_values["PM25"].split()[0])
        pollution_percentage = min(pm25_value / 150 * 100, 100)  # crude scaling
    else:
        pollution_percentage = None

    return {
        "latest_values": latest_values,
        "pollution_percentage": pollution_percentage,
        "pm25_risk": pm25_risk_level(pm25_value) if pm25_value is not None else None
    }


def pm25_risk_level(pm25):
    """Return simple risk category based on PM2.5 value (µg/m³)"""
    if pm25 <= 12:
        return "GOOD"
    elif pm25 <= 35.4:
        return "MODERATE"
    elif pm25 <= 55.4:
        return "UNHEALTHY FOR SENSITIVE GROUPS"
    elif pm25 <= 150.4:
        return "UNHEALTHY"
    elif pm25 <= 250.4:
        return "VERYUNHEALTHY"
    else:
        return "HAZARDOUS"
