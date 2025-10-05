from euclidean import nearest_location, euclidean_distance
from measurements import get_measurements
import pandas as pd
from openaq import OpenAQ
from datetime import datetime, timezone
from typing import Dict, Tuple, Optional
import time

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


def compute_pollution_percentage(latest_by_param: Dict[str, float]) -> Tuple[Optional[float], Optional[float]]:
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


# ---------- Risk category functions (WHO 2021 based) ----------
# PM2.5 (24h): WHO AQG & Interim Targets -> 5 bands
# Very Low ≤ 15; Low (15, 25]; Moderate (25, 37.5]; High (37.5, 50]; Extreme > 50  [µg/m³]

def classify_pm25_risk(pm25_value: float) -> Optional[str]:
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

def classify_no2_risk(no2_value: float) -> Optional[str]:
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


# ---------- Public function to call from your web backend ----------
# Returns a dict with the three values for your frontend, and the measurements dataframe for charts.

def get_air_quality_payload(
    lat: float,
    lon: float,
    date_from_iso: str,
    date_to_iso: str,
    limit: int = 1000,
    api_key: Optional[str] = None,
):
    """Fetch measurements from nearest location and prepare frontend payload.

    Returns
    -------
    payload: dict
        {
          "pc_no_cap": float | None,
          "pm25_risk": str | None,
          "no2_risk": str | None,
          "dataframe": pd.DataFrame (the full measurements df)
        }
    """
    sensor_data = pd.read_csv(sensors_path)
    nearest_location_id = nearest_location((lat, lon), locations_path)

    sensor_ids = sensor_data[sensor_data["location_id"] == nearest_location_id]["id"].tolist()

    with OpenAQ(api_key=api_key) as client:
        measurements = get_measurements(sensor_ids, date_from_iso, date_to_iso, limit, client, sensor_data)

    if measurements is None or measurements.empty:
        return {"pc_no_cap": None, "pm25_risk": None, "no2_risk": None, "dataframe": pd.DataFrame()}

    df = measurements.copy()
    df["parameter_std"] = df["parameter"].apply(_canon)
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True, errors="coerce")
    df = df.sort_values("datetime")

    latest_rows = df.groupby("parameter_std", as_index=False).tail(1)
    latest_by_param = {
        row["parameter_std"]: float(row["value"]) if pd.notnull(row["value"]) else None
        for _, row in latest_rows.iterrows()
    }

    last_pm25 = latest_by_param.get("PM25")
    last_no2 = latest_by_param.get("NO2")

    pm25_risk = classify_pm25_risk(last_pm25) if last_pm25 is not None else None
    no2_risk = classify_no2_risk(last_no2) if last_no2 is not None else None

    pc_no_cap, pc_0_100 = compute_pollution_percentage(latest_by_param)

    return {
        "pc_no_cap": pc_no_cap,
        "pm25_risk": pm25_risk,
        "no2_risk": no2_risk,
        "dataframe": df,
    }


# ---------- Example CLI usage (kept for local testing; optional to call) ----------
if __name__ == "__main__":
    # Input coordinates (lat, lon)
    lat, lon = 33.793715, -118.171615

    # Current-day window
    date_from = "2025-10-04T00:00:00Z"
    date_to = time.time()

    payload = get_air_quality_payload(lat, lon, date_from, date_to, api_key="a19444b8b983c4def60c98df1010f162da2bbffbb1f494ccbffee228068cbef7")

    df = payload["dataframe"]
    # Ensure the dataframe is stably sorted and index reset before printing/sending to frontend
    if df is not None and not df.empty:
        df = df.sort_values(["datetime", "parameter_std", "sensor_id"], kind="mergesort").reset_index(drop=True)

    print(df)

    print(f"[POLLUTION PERCENTAGE] {payload['pc_no_cap'] if payload['pc_no_cap'] is not None else 'N/A'}")
    print(f"[HEALTH RISK (PM2.5)] {payload['pm25_risk'] if payload['pm25_risk'] else 'N/A'}")
    print(f"[RISK X (NO2)] {payload['no2_risk'] if payload['no2_risk'] else 'N/A'}")
