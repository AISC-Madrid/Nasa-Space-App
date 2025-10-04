from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

# Example function: get air quality from OpenWeatherMap API
def get_air_quality(lat, lon):
    API_KEY = "427f41463f86839c7cdeef34aa7c5098"  # Replace with OpenWeatherMap or AirVisual API key
    url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        return None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/get_air_quality", methods=["POST"])
def air_quality():
    data = request.json
    lat, lon = data.get("lat"), data.get("lon")
    air_data = get_air_quality(lat, lon)

    if air_data:
        aq = air_data["list"][0]["main"]["aqi"]   # Air Quality Index
        components = air_data["list"][0]["components"]

        return jsonify({
            "aqi": aq,
            "components": components
        })
    else:
        return jsonify({"error": "Could not fetch air quality data"}), 500

if __name__ == "__main__":
    app.run(debug=True)
