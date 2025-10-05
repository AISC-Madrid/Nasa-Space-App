from .euclidean import nearest_location, euclidean_distance
from .measurements import get_measurements
import pandas as pd
from openaq import OpenAQ
from datetime import datetime, timezone
from typing import Dict, Tuple, Optional
import time
import csv 
from pathlib import Path

sensors_path = Path(__file__).parent / "sensors.csv"
locations_path =  Path(__file__).parent / "locations.csv"

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

def classify_pm25_quality(pm25_value: float) -> Optional[str]:
    if pm25_value is None:
        return None
    v = float(pm25_value)
    if v <= 9.0:
        return "GOOD"
    elif v <= 35.4:
        return "MODERATE"
    elif v <= 55.4:
        return "UNHEALTHY FOR SENSITIVE GROUPS"
    elif v <= 125.4:
        return "UNHEALTHY"
    elif v <= 225.4:
        return "VERYUNHEALTHY"
    else:
        return "HAZARDOUS"


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
          "latest_params": list[dict] | None,
          "dataframe": pd.DataFrame (the full measurements df)
        }
    """
    sensor_data = pd.read_csv(sensors_path)
    nearest_location_id = nearest_location((lat, lon), locations_path)

    sensor_ids = sensor_data[sensor_data["location_id"] == nearest_location_id]["id"].tolist()

    with OpenAQ(api_key=api_key) as client:
        measurements = get_measurements(sensor_ids, date_from_iso, date_to_iso, limit, client, sensor_data)

    if measurements is None or measurements.empty:
        return {"pc_no_cap": None, "pm25_risk": None, "no2_risk": None, "latest_params": None, "dataframe": pd.DataFrame()}

    df = measurements.copy()
    df["parameter_std"] = df["parameter"].apply(_canon)
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True, errors="coerce")
    df = df.sort_values("datetime")

    latest_rows = df.groupby("parameter_std", as_index=False).tail(1)
    latest_by_param = {
        row["parameter_std"]: float(row["value"]) if pd.notnull(row["value"]) else None
        for _, row in latest_rows.iterrows()
    }

    # --- NEW: print and collect latest value per parameter (for console + frontend) ---
    latest_pairs = []
    for k in sorted(latest_by_param.keys()):
        v = latest_by_param[k]
        if v is None:
            continue
        value_str = f"{v:.3f}".rstrip("0").rstrip(".")
        print(f"{k}: {value_str}")
        latest_pairs.append({"parameter": k, "value": v, "value_str": value_str})

    last_pm25 = latest_by_param.get("PM25")
    last_no2 = latest_by_param.get("NO2")

    pm25_risk = classify_pm25_quality(last_pm25) if last_pm25 is not None else None
    no2_risk = classify_no2_risk(last_no2) if last_no2 is not None else None

    pc_no_cap, pc_0_100 = compute_pollution_percentage(latest_by_param)

    return {
        "pc_no_cap": pc_no_cap,
        "pm25_risk": pm25_risk,
        "no2_risk": no2_risk,
        "latest_params": latest_pairs,   # <-- NEW
        "dataframe": df,
    }

def params_dict(df):
    """Returns a nested dictionary with the parameters and inside the datetime and value"""
    params_dict = {}
    for param in df["parameter_std"].unique():
        dictionary = {}
        param_df = df[df["parameter_std"] == param]["datetime", "value"].reset_index(drop=True)
        for i in range(len(param_df)):
            dictionary[param_df.loc[i, "datetime"]] = param_df.loc[i, "value"]
        params_dict[param] = dictionary
    return params_dict


def get_air_quality_summary(lat: float, lon: float, days_back: int = 7, limit: int = 1000, api_key: Optional[str] = None):
    """
    Returns air quality summary for a given latitude and longitude.

    Parameters
    ----------
    lat : float
        Latitude of the location.
    lon : float
        Longitude of the location.
    days_back : int
        How many days back to fetch data (default 7).
    limit : int
        Max number of measurements to fetch (default 1000).
    api_key : str, optional
        OpenAQ API key, if required.

    Returns
    -------
    dict
        {
            "pc_no_cap": float | None,
            "pm25_risk": str | None,
            "no2_risk": str | None, 
            "latest_params": list[dict] | None,
            "dataframe": pd.DataFrame
        }
    """
    # Compute time window
    
    date_to_ts = time.time()
    date_from_ts = date_to_ts - days_back * 24 * 60 * 60
    date_from_iso = datetime.fromtimestamp(date_from_ts, timezone.utc).isoformat()
    date_to_iso = datetime.fromtimestamp(date_to_ts, timezone.utc).isoformat()

    # Get payload
    payload = get_air_quality_payload(lat, lon, date_from_iso, date_to_iso, limit, _key)

    # Prepare summary for printing or return
    summary = {
        "pollution_percentage": payload.get("pc_no_cap"),
        "pm25_risk": payload.get("pm25_risk"),
        "no2_risk": payload.get("no2_risk"),
        "latest_values": {item["parameter"]: item["value_str"] for item in (payload.get("latest_params") or [])},
        "dataframe": payload.get("dataframe")
    }

    return summary

def get_air_quality_summary(lat: float, lon: float, days_back: int = 7, limit: int = 1000):
    """
    Returns air quality summary for a given latitude and longitude.api

    Parameters
    ----------
    lat : float
        Latitude of the location.
    lon : float
        Longitude of the location.
    days_back : int
        How many days back to fetch data (default 7).
    limit : int
        Max number of measurements to fetch (default 1000).
    api_key : str, optional
        OpenAQ API key, if required.

    Returns
    -------
    dict
        {
            "pc_no_cap": float | None,
            "pm25_risk": str | None,
            "no2_risk": str | None,
            "latest_params": list[dict] | None,
            "dataframe": pd.DataFrame
        }
    """
    # Compute time window
    date_to_ts = time.time()
    date_from_ts = date_to_ts - days_back * 24 * 60 * 60
    date_from_iso = datetime.fromtimestamp(date_from_ts, timezone.utc).isoformat()
    date_to_iso = datetime.fromtimestamp(date_to_ts, timezone.utc).isoformat()

    # Get payload
    payload = get_air_quality_payload(lat, lon, date_from_iso, date_to_iso, limit,  api_key="a19444b8b983c4def60c98df1010f162da2bbffbb1f494ccbffee228068cbef7")

    # Prepare summary for printing or return
    summary = {
        "pollution_percentage": payload.get("pc_no_cap"),
        "pm25_risk": payload.get("pm25_risk"),
        "no2_risk": payload.get("no2_risk"),
        "latest_values": {item["parameter"]: item["value_str"] for item in (payload.get("latest_params") or [])},
        "dataframe": payload.get("dataframe")
    }

    return summary

    


# ---------- Example CLI usage (kept for local testing; optional to call) ----------
if __name__ == "__main__":
    # Input coordinates (lat, lon)
    lat, lon = 33.793715, -118.171615

    # Current-day window
    date_from_last_week = time.time() - 7 * 24 * 60 * 60  # I want to get the data from the last week
    date_to = time.time()

    payload = get_air_quality_payload(lat, lon, date_from_last_week, date_to, api_key="a19444b8b983c4def60c98df1010f162da2bbffbb1f494ccbffee228068cbef7")

    df = payload["dataframe"]
    if df is not None and not df.empty:
        df = df.sort_values(["datetime", "parameter_std", "sensor_id"], kind="mergesort").reset_index(drop=True)

    print(df)

    print(f"[POLLUTION PERCENTAGE] {payload['pc_no_cap'] if payload['pc_no_cap'] is not None else 'N/A'}")
    print(f"[HEALTH QUALITY (PM2.5)] {payload['pm25_risk'] if payload['pm25_risk'] else 'N/A'}")
    print(f"[RISK X (NO2)] {payload['no2_risk'] if payload['no2_risk'] else 'N/A'}")

    # Also print the per-parameter latest values collected for the frontend
    if payload.get("latest_params"):
        print("Latest per-parameter values:")
        for item in payload["latest_params"]:
            print(f" - {item['parameter']}: {item['value_str']} µg/m³")

    



