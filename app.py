from flask import Flask, render_template, request, jsonify
from datetime import date
from scripts.backend.get_values_def import get_air_quality_summary  # <-- import your function here

app = Flask(__name__)

@app.route("/")
def index():
    today = date.today().isoformat()
    return render_template("index.html", today=today)

@app.route("/api/air_quality")
def air_quality():
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    if lat is None or lon is None:
        return jsonify({"error": "Missing lat or lon"}), 400

    # Get air quality summary (7-day default)
    summary = get_air_quality_summary(lat, lon, days_back=7)

    # Convert any DataFrame in the summary to JSON-serializable dict
    for key, value in summary.items():
        if hasattr(value, "to_dict"):  # detect DataFrame
            summary[key] = value.to_dict(orient="records")  # convert to list of dicts

    return jsonify(summary)



if __name__ == "__main__":
    app.run(debug=True)
