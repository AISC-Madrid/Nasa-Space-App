from flask import Flask, render_template, request, jsonify
import folium
from datetime import date

app = Flask(__name__)

@app.route("/")
def index():
    # Pass today's date to the template
    today = date.today().isoformat()
    return render_template("index.html", today=today)



if __name__ == "__main__":
    app.run(debug=True)
