from flask import Flask, render_template, request, redirect, url_for, jsonify
from biblioteca import Biblioteca, Libro, Usuario, Prestamo, Bibliotecario
from datetime import datetime
import json

app = Flask(__name__)
biblioteca = Biblioteca()
bibliotecario = Bibliotecario(1, "Juanito")

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/libros', methods=['GET', 'POST'])
def manejar_libros():
    if request.method == 'POST':
        data = request.form.to_dict()
        nuevo_libro = Libro(
            titulo=data['titulo'],
            autor=data['autor'],
            isbn=str(data['isbn']),
            editorial=data['editorial'],
            año_publicacion=data['año_publicacion']
        )
        bibliotecario.añadir_libro(biblioteca, nuevo_libro)
        guardar_datos()
        return redirect(url_for('manejar_libros'))
    elif request.method == 'GET':
        return render_template("libros.html", libros=biblioteca.libros)
    
@app.route('/usuarios', methods=['GET', 'POST'])
def manejar_usuarios():
    if request.method == 'POST':
        data = request.form.to_dict()
        nuevo_usuario = Usuario(
            id_usuario=str(data['id_usuario']),
            nombre=data['nombre'],
            email=data['email']
        )
        biblioteca.registrar_usuario(nuevo_usuario)
        guardar_datos()
        return redirect(url_for('manejar_usuarios'))
    elif request.method == 'GET':
        return render_template('usuarios.html', usuarios=biblioteca.usuarios)

@app.route('/prestamos', methods=['GET', 'POST'])
def gestionar_prestamos():
    if request.method == 'POST':
        data = request.form.to_dict()
        id_usuario = str(data['id_usuario'])
        isbn = str(data['isbn'])
        usuario = next((u for u in biblioteca.usuarios if str(u.id_usuario) == id_usuario), None)
        libro = next((l for l in biblioteca.libros if str(l.isbn) == isbn), None)
        if not usuario or not libro:
            return jsonify({'mensaje': 'Usuario o libro no encontrado'}), 404
        
        if 'fecha_prestamo' in data:
            if not libro.disponible:
                return jsonify({'mensaje': f'El libro "{libro.titulo}" ya está prestado'}), 400
            
            fecha_prestamo = datetime.strptime(data['fecha_prestamo'], '%Y-%m-%d')
            fecha_devolucion = datetime.strptime(data['fecha_devolucion'], '%Y-%m-%d')
            usuario.prestar_libro(libro)
            nuevo_prestamo = Prestamo(
                id_prestamo=len(biblioteca.prestamos) + 1,
                libro=libro,
                usuario=usuario,
                fecha_prestamo=fecha_prestamo,
                fecha_devolucion=fecha_devolucion
            )
            biblioteca.prestamos.append(nuevo_prestamo)
            resultado = f"Libro {libro.titulo} prestado a {usuario.nombre}"
        else:
            prestamo = next((p for p in biblioteca.prestamos if
                             str(p.libro.isbn) == isbn and str(p.usuario.id_usuario) == id_usuario), None)
            if not prestamo:
                return jsonify({'mensaje': f'El libro "{libro.titulo}" no está prestado por {usuario.nombre}'}), 400
            
            usuario.devolver_libro(libro)
            biblioteca.prestamos.remove(prestamo)
            resultado = f"Libro {libro.titulo} devuelto por {usuario.nombre}"
        guardar_datos()
        return jsonify({'mensaje': resultado})
        
    elif request.method == 'GET':
        return render_template('prestamos.html', usuarios=biblioteca.usuarios, libros=biblioteca.libros,
                               prestamos=biblioteca.prestamos)

def guardar_datos():
    with open('datos.json', 'w') as f:
        datos = {
            'libros': [libro.__dict__ for libro in biblioteca.libros],
            'usuarios': [usuario.__dict__ for usuario in biblioteca.usuarios],
            'prestamos': [{
                'id_prestamo': prestamo.id_prestamo,
                'libro': prestamo.libro.__dict__,
                'usuario': prestamo.usuario.__dict__,
                'fecha_prestamo': prestamo.fecha_prestamo.strftime('%Y-%m-%d'),
                'fecha_devolucion': prestamo.fecha_devolucion.strftime('%Y-%m-%d')
            } for prestamo in biblioteca.prestamos]
        }
        json.dump(datos, f, indent=4)

def cargar_datos():
    try:
        with open('datos.json', 'r') as f:
            contenido = f.read().strip()
            if not contenido:
                datos = {}
            else:
                datos = json.loads(contenido)
            
            for libro_data in datos.get('libros', []):
                disponible = libro_data.pop('disponible', True)
                libro = Libro(**libro_data)
                libro.disponible = disponible
                biblioteca.libros.append(libro)
                print(f"Libro cargado: {libro.titulo}, ISBN: {libro.isbn}")

            for usuario_data in datos.get('usuarios', []):
                usuario_data.pop('libros_prestados', None)
                usuario = Usuario(**usuario_data)
                biblioteca.usuarios.append(usuario)
                print(f"Usuario cargado: {usuario.nombre}, ID: {usuario.id_usuario}")

            for prestamo_data in datos.get('prestamos', []):
                libro_data = prestamo_data['libro']
                usuario_data = prestamo_data['usuario']
                libro = next((libro for libro in biblioteca.libros if str(libro.isbn) == str(libro_data['isbn'])), None)
                usuario = next((usuario for usuario in biblioteca.usuarios if
                                str(usuario.id_usuario) == str(usuario_data['id_usuario'])), None)
                if libro and usuario:
                    prestamo = Prestamo(
                        id_prestamo=prestamo_data['id_prestamo'],
                        libro=libro,
                        usuario=usuario,
                        fecha_prestamo=datetime.strptime(prestamo_data['fecha_prestamo'], '%Y-%m-%d'),
                        fecha_devolucion=datetime.strptime(prestamo_data['fecha_devolucion'], '%Y-%m-%d')
                    )
                    biblioteca.prestamos.append(prestamo)
                    print(f"Préstamo cargado: Libro: {libro.titulo}, Usuario: {usuario.nombre}")
    except FileNotFoundError:
        pass
    except json.JSONDecodeError:
        pass

if __name__ == '__main__':
    cargar_datos()
    app.run(debug=True)
