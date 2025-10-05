from flask import Flask, render_template, request, jsonify
import requests
import os

app = Flask(__name__)

# Use environment variable for API key (recommended)
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "427f41463f86839c7cdeef34aa7c5098")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/air_quality")
def air_quality():
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    if lat is None or lon is None:
        return jsonify({"error": "Missing lat or lon"}), 400

    url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}"

    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()

        # Extract main pollutants
        components = data['list'][0]['components']
        aqi = data['list'][0]['main']['aqi']  # 1=Good, 5=Very Poor

        # Map AQI number to text
        aqi_map = {1: "Good", 2: "Fair", 3: "Moderate", 4: "Poor", 5: "Very Poor"}
        aqi_text = aqi_map.get(aqi, "Unknown")

        # Calculate a rough pollution percentage for the frontend
        pollution_percentage = (aqi / 5) * 100

        result = {
            "aqi": aqi,
            "aqi_text": aqi_text,
            "pollution_percentage": pollution_percentage,
            "latest_values": {k: {"value": v, "risk": aqi_text} for k, v in components.items()}
        }

        return jsonify(result)
    except Exception as e:
        print("Error fetching air quality:", e)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
