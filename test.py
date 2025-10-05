from openaq import OpenAQ
import json
from pathlib import Path

API_KEY = "99f6eb5b9e02d83dafed5d2bf8352a22512e0066f0f7e071edb0b07cf2fe4850"
sensor_id = 1502

OUT_DIR = Path("data/output")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = OUT_DIR / f"sensor_{sensor_id}_hours.json"

with OpenAQ(api_key=API_KEY) as client:
    results = client.measurements.list(sensors_id=sensor_id, data="hours", limit=1000)

    # Convert results to a JSON-serializable dict
    data = results.json if isinstance(results.json, dict) else results.dict()  # fallback

    # Save to file
    with OUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"[LOG] Data saved to {OUT_FILE.resolve()}")
