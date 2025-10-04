import json
from pathlib import Path
from openaq import OpenAQ

API_KEY = "a19444b8b983c4def60c98df1010f162da2bbffbb1f494ccbffee228068cbef7"

# BBox de Los Ángeles [minLon, minLat, maxLon, maxLat]
bbox = [-118.668153, 33.703935, -118.155358, 34.337306]

def to_serializable(obj):
    """
    Convierte el objeto devuelto por el cliente (posibles modelos Pydantic)
    a un dict JSON-serializable de forma robusta para distintas versiones.
    """
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

def main():
    client = OpenAQ(api_key=API_KEY)
    try:
        result = client.locations.list(
            bbox=bbox,
            parameters_id=2,
            limit=1000
        )

        data = to_serializable(result)

        out_dir = Path("data/output")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "result.json"

        with out_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"Respuesta guardada en: {out_path.resolve()}")
    finally:
        client.close()

if __name__ == "__main__":
    main()
