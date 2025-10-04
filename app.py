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
