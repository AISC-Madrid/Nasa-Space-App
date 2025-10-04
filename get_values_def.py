from euclidean import nearest_location, euclidean_distance
from measurements import get_measurements
import pandas as pd
from openaq import OpenAQ
from datetime import datetime, timezone

locations_path = "data/output/locations.csv"
sensors_path = "data/output/sensors.csv"

# ---------- Helpers for parameter names and % pollution ----------
def _canon(p: str) -> str:
    """
    Canonicalize parameter names to: PM25, PM10, NO2, O3, SO2, CO
    """
    if p is None:
        return ""
    s = str(p).lower().replace(".", "").replace("_", "").strip()
    if s in {"pm25", "pm2p5", "pm2-5", "pm2 5"}:
        return "PM25"
    if s in {"pm10"}:
        return "PM10"
    if s in {"no2"}:
        return "NO2"
    if s in {"o3", "ozone"}:
        return "O3"
    if s in {"so2"}:
        return "SO2"
    if s in {"co"}:
        return "CO"
    return s.upper()

# WHO 2021 short-term guideline values used for normalization:
# Units:
# - PM25/PM10/NO2/O3/SO2 in µg/m³
# - CO in mg/m³
THRESHOLDS = {
    "PM25": 15.0,   # µg/m³ (24h)
    "PM10": 45.0,   # µg/m³ (24h)
    "NO2": 25.0,    # µg/m³ (24h)
    "O3": 100.0,    # µg/m³ (8h max)
    "SO2": 40.0,    # µg/m³ (24h)
    "CO": 4.0       # mg/m³ (24h)
}

# Weights prioritizing health/exposure
BASE_WEIGHTS = {
    "PM25": 0.45,
    "NO2": 0.20,
    "O3": 0.15,
    "PM10": 0.10,
    "SO2": 0.05,
    "CO": 0.05,
}

def _renorm_weights(available_keys):
    total = sum(BASE_WEIGHTS[k] for k in available_keys)
    return {k: BASE_WEIGHTS[k] / total for k in available_keys}

def _maybe_convert_co(value):
    """
    Simple heuristic: if CO arrives in µg/m³ (rare), values will be ~1000x
    typical mg/m³. If CO > 200, assume µg/m³ and convert to mg/m³.
    """
    if value is None:
        return None
    try:
        v = float(value)
    except Exception:
        return None
    if v > 200:
        return v / 1000.0
    return v

def compute_pollution_percentage(latest_by_param):
    """
    latest_by_param: dict with keys in {"PM25","PM10","NO2","O3","SO2","CO"} and numeric values
    Returns (pc_no_cap, pc_0_100)
    """
    if "CO" in latest_by_param and latest_by_param["CO"] is not None:
        latest_by_param["CO"] = _maybe_convert_co(latest_by_param["CO"])

    present = {k: v for k, v in latest_by_param.items() if (k in THRESHOLDS and v is not None)}
    if not present:
        return None, None

    weights = _renorm_weights(list(present.keys()))
    perc = {k: 100.0 * (present[k] / THRESHOLDS[k]) for k in present}
    pc_no_cap = sum(weights[k] * perc[k] for k in present)
    pc_0_100 = min(100.0, pc_no_cap)
    return pc_no_cap, pc_0_100

# ---------- NEW: Risk category functions (WHO 2021 based) ----------
# PM2.5 (24h): WHO AQG & Interim Targets -> 5 bands
# Very Low ≤ 15; Low (15, 25]; Moderate (25, 37.5]; High (37.5, 50]; Extreme > 50  [µg/m³]
def classify_pm25_risk(pm25_value: float) -> str | None:
    if pm25_value is None:
        return None
    v = float(pm25_value)
    if v <= 15.0:
        return "Very Low"
    elif v <= 25.0:
        return "Low"
    elif v <= 37.5:
        return "Moderate"
    elif v <= 50.0:
        return "High"
    else:
        return "Extreme"

# NO2: WHO 2021 24h AQG/ITs (25, 50, 120) + WHO 1h level (200) -> 5 bands
# Very Low ≤ 25; Low (25, 50]; Moderate (50, 120]; High (120, 200]; Extreme > 200  [µg/m³]
def classify_no2_risk(no2_value: float) -> str | None:
    if no2_value is None:
        return None
    v = float(no2_value)
    if v <= 25.0:
        return "Very Low"
    elif v <= 50.0:
        return "Low"
    elif v <= 120.0:
        return "Moderate"
    elif v <= 200.0:
        return "High"
    else:
        return "Extreme"

# -------------------------------------------------------------------------------------------

sensor_data = pd.read_csv(sensors_path)

# Input coordinates (lat, lon)
coordiates = (33.793715, -118.171615)
nearest_location_id = nearest_location(coordiates, locations_path)
print(f"Nearest location ID: {nearest_location_id}")

# Sensors at the nearest location
sensor_ids = sensor_data[sensor_data["location_id"] == nearest_location_id]["id"].tolist()

# Current-day window (hourly)
datetime_from = "2025-10-04T00:00:00Z"
datetime_to = "2025-10-04T23:59:59Z"
limit = 1000

with OpenAQ(api_key="f0d2b3f27388d5ce43efa743fe482a5ba6606d90a1ccb425e7a3ea0f51475a57") as client:
    measurements = get_measurements(sensor_ids, datetime_from, datetime_to, limit, client, sensor_data)

# Show the original dataframe (unchanged)
print(measurements)

# ---------- Extract last PM2.5 / NO2 values, compute % pollution, and print risk labels ----------
if measurements is None or measurements.empty:
    print("No measurements found in the given interval.")
else:
    df = measurements.copy()
    df["parameter_std"] = df["parameter"].apply(_canon)
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True, errors="coerce")
    df = df.sort_values("datetime")

    # Last value per parameter
    latest_rows = df.groupby("parameter_std", as_index=False).tail(1)

    # Build dict parameter -> last value
    latest_by_param = {
        row["parameter_std"]: float(row["value"]) if pd.notnull(row["value"]) else None
        for _, row in latest_rows.iterrows()
    }

    # Clear prints for PM2.5 and NO2
    last_pm25 = latest_by_param.get("PM25")
    last_no2 = latest_by_param.get("NO2")

    if last_pm25 is not None:
        print(f"[LAST PM2.5] {last_pm25:.2f} µg/m³")
    else:
        print("[LAST PM2.5] Not available")

    if last_no2 is not None:
        print(f"[LAST NO2] {last_no2:.2f} µg/m³")
    else:
        print("[LAST NO2] Not available")

    # HEALTH RISK (PM2.5)
    pm25_risk = classify_pm25_risk(last_pm25) if last_pm25 is not None else None
    if pm25_risk:
        print(f"[HEALTH RISK (PM2.5)] {pm25_risk}")
    else:
        print("[HEALTH RISK (PM2.5)] Not available")

    # RISK X (NO2)
    no2_risk = classify_no2_risk(last_no2) if last_no2 is not None else None
    if no2_risk:
        print(f"[RISK X (NO2)] {no2_risk}")
    else:
        print("[RISK X (NO2)] Not available")

    # Pollution percentage (previous approach)
    pc_no_cap, pc_0_100 = compute_pollution_percentage(latest_by_param)
    if pc_no_cap is None:
        print("[POLLUTION PERCENTAGE] Cannot compute (no valid parameters).")
    else:
        print(f"[POLLUTION PERCENTAGE] {pc_no_cap:.1f}% (no cap)")
        print(f"[POLLUTION INDEX 0–100] {pc_0_100:.1f}")
# --------------------------------------------------------------------------------------------
