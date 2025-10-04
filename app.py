# from flask import Flask, render_template, request, jsonify
# import requests

# app = Flask(__name__)

# # Example function: get air quality from OpenWeatherMap API
# def get_air_quality(lat, lon):
#     API_KEY = "YOUR_API_KEY"  # Replace with OpenWeatherMap or AirVisual API key
#     url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"
#     response = requests.get(url)
#     if response.status_code == 200:
#         data = response.json()
#         return data
#     else:
#         return None

# @app.route("/")
# def index():
#     return render_template("index.html")

# @app.route("/get_air_quality", methods=["POST"])
# def air_quality():
#     data = request.json
#     lat, lon = data.get("lat"), data.get("lon")
#     air_data = get_air_quality(lat, lon)

#     if air_data:
#         aq = air_data["list"][0]["main"]["aqi"]   # Air Quality Index
#         components = air_data["list"][0]["components"]

#         return jsonify({
#             "aqi": aq,
#             "components": components
#         })
#     else:
#         return jsonify({"error": "Could not fetch air quality data"}), 500

# if __name__ == "__main__":
#     app.run(debug=True)

from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

@app.route('/')
def index():
    # Página principal con enlace y formulario
    return render_template('index.html')

@app.route('/planet/<name>')
def planet(name):
    # Aquí podrías buscar datos reales según el nombre y pasarlos al template.
    # Ejemplo de datos ficticios:
    planet_info = {
        'Mars': {'radius_km': 3389.5, 'notes': 'Planeta rojo'},
        'Jupiter': {'radius_km': 69911, 'notes': 'Gigante gaseoso'}
    }
    info = planet_info.get(name)
    return render_template('planet.html', planet_name=name, info=info)

@app.route('/search', methods=['POST'])
def search():
    # Recibimos el formulario y redirigimos a /planet/<name>
    name = request.form.get('planet_name', '').strip()
    if not name:
        return redirect(url_for('index'))
    return redirect(url_for('planet', name=name))

if __name__ == '__main__':
    app.run(debug=True)
