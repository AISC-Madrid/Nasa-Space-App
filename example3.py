import json
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone

from openaq import OpenAQ

# Opcional: si tu SDK usa httpx por debajo, esto ayuda a capturar timeouts
try:
    import httpx
    HTTPX_TIMEOUT_EXC = (httpx.TimeoutException, httpx.ReadTimeout, httpx.ConnectTimeout)
except Exception:
    HTTPX_TIMEOUT_EXC = (Exception,)  # fallback genérico

API_KEY = "a19444b8b983c4def60c98df1010f162da2bbffbb1f494ccbffee228068cbef7"

# BBox de Los Ángeles [minLon, minLat, maxLon, maxLat]
BBOX = [-118.668153, 33.703935, -118.155358, 34.337306]

# Parámetro/molécula a filtrar. Ej.: PM2.5 -> id=2
PARAMETERS_ID = 2

# ---- Ajustes de rendimiento/robustez ----
WINDOW_HOURS = 168           # últimas horas a traer por sensor (p. ej., 7 días)
MEAS_LIMIT_PER_PAGE = 1000   # nº de horas por página (1000 >= 168, 1 página basta)
MEAS_MAX_PAGES = 1           # mantener en 1 si WINDOW_HOURS <= 1000
SLEEP_BETWEEN_CALLS = 0.15   # pequeña pausa entre llamadas
REQUEST_TIMEOUT_S = 20.0     # timeout de red por request (segundos)
MAX_RETRIES_PER_CALL = 3     # reintentos por llamada con backoff básico
SAVE_EVERY_N_SENSORS = 20    # guardado incremental cada N sensores

OUT_DIR = Path("data/output")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / "result_with_hours.json"
TMP_PATH = OUT_DIR / "result_with_hours.partial.json"


def to_serializable(obj):
    # Pydantic v2
    if hasattr(obj, "model_dump_json"):
        return json.loads(obj.model_dump_json())
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    # Pydantic v1
    if hasattr(obj, "dict"):
        return obj.dict()
    if hasattr(obj, "json"):
        j = obj.json()
        return json.loads(j) if isinstance(j, str) else j
    # Estructuras nativas
    if isinstance(obj, (list, tuple)):
        return [to_serializable(x) for x in obj]
    if isinstance(obj, dict):
        return {k: to_serializable(v) for k, v in obj.items()}
    return obj


def _now_utc():
    return datetime.now(timezone.utc)


def _fmt(dt: datetime) -> str:
    # API espera ISO8601 con 'Z' para UTC
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _with_retries(fn, *, max_retries=MAX_RETRIES_PER_CALL, base_sleep=0.5, exc_types=(Exception,)):
    attempt = 0
    while True:
        try:
            return fn()
        except exc_types as e:
            attempt += 1
            if attempt > max_retries:
                raise
            sleep = base_sleep * (2 ** (attempt - 1))
            print(f"[WARN] Retry {attempt}/{max_retries} tras error: {e}. Esperando {sleep:.1f}s…")
            time.sleep(sleep)


def fetch_sensor_hours(client: OpenAQ, sensor_id: int,
                       dt_from_utc: str, dt_to_utc: str,
                       limit_per_page: int = MEAS_LIMIT_PER_PAGE,
                       max_pages: int = MEAS_MAX_PAGES,
                       sleep_s: float = SLEEP_BETWEEN_CALLS):
    """
    Devuelve [{utc_from, utc_to, local_from, local_to, value}, ...] para un sensor.
    Ventana temporal [dt_from_utc, dt_to_utc].
    """
    all_items = []
    page = 1

    while True:
        def _do_call():
            return client.measurements.list(
                sensors_id=sensor_id,
                data="hours",
                limit=limit_per_page,
                page=page,
                datetime_from=dt_from_utc,
                datetime_to=dt_to_utc,
            )

        try:
            res = _with_retries(
                _do_call,
                exc_types=HTTPX_TIMEOUT_EXC + (Exception,),
                max_retries=MAX_RETRIES_PER_CALL,
                base_sleep=0.7
            )
        except Exception as e:
            print(f"[WARN] measurements.list falló para sensor {sensor_id} (page={page}): {e}")
            break

        obj = to_serializable(res)
        batch = obj.get("results", []) or []
        all_items.extend(batch)

        headers = obj.get("headers") or {}
        remaining = headers.get("x_ratelimit_remaining")
        try:
            remaining = int(remaining) if remaining is not None else None
        except Exception:
            remaining = None

        if remaining is not None and remaining <= 1:
            time.sleep(1.0)  # respiro si estamos al límite

        # Condiciones de salida de paginado
        if len(batch) < limit_per_page:
            break
        page += 1
        if max_pages and page > max_pages:
            break

        if sleep_s:
            time.sleep(sleep_s)

    # Normaliza a serie ligera
    series = []
    for item in all_items:
        period = item.get("period") or {}
        dt_from = period.get("datetime_from") or {}
        dt_to = period.get("datetime_to") or {}
        series.append({
            "utc_from": dt_from.get("utc"),
            "utc_to": dt_to.get("utc"),
            "local_from": dt_from.get("local"),
            "local_to": dt_to.get("local"),
            "value": item.get("value")
        })

    # Ordena por utc_to/utc_from
    series.sort(key=lambda x: x.get("utc_to") or x.get("utc_from") or "")
    return series


def enrich_locations_with_hours(client: OpenAQ, locations_payload: dict) -> dict:
    """
    Añade 'hours' y 'hours_units' a cada sensor dentro del payload de locations.list,
    acotando la ventana temporal y guardando progreso incremental.
    """
    results = locations_payload.get("results", [])
    if not isinstance(results, list):
        return locations_payload

    # Ventana temporal
    dt_to = _fmt(_now_utc())
    dt_from = _fmt(_now_utc() - timedelta(hours=WINDOW_HOURS))

    processed_sensors = 0

    for loc in results:
        sensors = loc.get("sensors") or []
        if not isinstance(sensors, list):
            continue

        for sensor in sensors:
            sid = sensor.get("id")
            if sid is None:
                continue

            # Serie horaria recortada a la ventana
            hours = fetch_sensor_hours(client, sid, dt_from, dt_to)
            sensor["hours"] = hours
            sensor["hours_units"] = (sensor.get("parameter") or {}).get("units")

            processed_sensors += 1

            # Guardado incremental
            if processed_sensors % SAVE_EVERY_N_SENSORS == 0:
                try:
                    with TMP_PATH.open("w", encoding="utf-8") as f:
                        json.dump(locations_payload, f, ensure_ascii=False, indent=2)
                    print(f"[LOG] Progreso guardado ({processed_sensors} sensores) en {TMP_PATH}")
                except Exception as e:
                    print(f"[WARN] No se pudo guardar progreso parcial: {e}")

            if SLEEP_BETWEEN_CALLS:
                time.sleep(SLEEP_BETWEEN_CALLS)

    return locations_payload


def main():
    # Muchos SDKs aceptan timeout=… y lo pasan a httpx; si tu versión no lo soporta, se ignora sin romper.
    with OpenAQ(api_key="a19444b8b983c4def60c98df1010f162da2bbffbb1f494ccbffee228068cbef7") as client:
        # 1) Localizaciones y sensores (como tu código 1)
        loc_res = client.locations.list(
            bbox=BBOX,
            parameters_id=PARAMETERS_ID,
            limit=1000
        )
        loc_payload = to_serializable(loc_res)

        # 2) Enriquecer con horas (lógica de código 2 integrada y optimizada)
        loc_payload = enrich_locations_with_hours(client, loc_payload)

        # 3) Guardado definitivo
        with OUT_PATH.open("w", encoding="utf-8") as f:
            json.dump(loc_payload, f, ensure_ascii=False, indent=2)

        print(f"[OK] Respuesta enriquecida guardada en: {OUT_PATH.resolve()}")

        # Limpieza del parcial si existe
        try:
            if TMP_PATH.exists():
                TMP_PATH.unlink()
        except Exception:
            pass


if __name__ == "__main__":
    main()
