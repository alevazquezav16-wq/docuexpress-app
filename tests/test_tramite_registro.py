import pytest
from flask import url_for
from ARCHIVOS.models import User, Papeleria, PapeleriaPrecio, Tramite, TramiteCosto
from ARCHIVOS.database import db
from datetime import datetime

@pytest.fixture
def client(app):
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.drop_all()

def login(client, username, password):
    return client.post(url_for('auth.login'), data={
        'username': username,
        'password': password
    }, follow_redirects=True)

def create_user_and_papeleria(db):
    user = User(username='testuser', role='employee')
    user.set_password('testpass')
    db.session.add(user)
    db.session.commit()
    papeleria = Papeleria(nombre='Papelería Test', user_id=user.id, is_active=True)
    db.session.add(papeleria)
    db.session.commit()
    return user, papeleria

def test_registro_tramite_con_precio_costo(client):
    user, papeleria = create_user_and_papeleria(db)
    db.session.add(PapeleriaPrecio(papeleria_id=papeleria.id, tramite='ACTA DE NACIMIENTO', precio=100))
    db.session.add(TramiteCosto(tramite='ACTA DE NACIMIENTO', costo=50, user_id=user.id))
    db.session.commit()
    login(client, 'testuser', 'testpass')
    data = {
        'papeleria_id': papeleria.id,
        'tramite': 'ACTA DE NACIMIENTO',
        'precio': 100,  # Enviar explícitamente
        'costo': 50,    # Enviar explícitamente
        'cantidad': 1,
        'fecha': datetime.today().strftime('%Y-%m-%d')
    }
    response = client.post(url_for('papeleria.registrar_tramite'), data=data, follow_redirects=True)
    tramite = Tramite.query.filter_by(papeleria_id=papeleria.id, tramite='ACTA DE NACIMIENTO').first()
    if tramite is None:
        print(response.data.decode())
    assert tramite is not None
    assert tramite.precio == 100
    assert tramite.costo == 50

def test_registro_tramite_sin_precio(client):
    user, papeleria = create_user_and_papeleria(db)
    login(client, 'testuser', 'testpass')
    data = {
        'papeleria_id': papeleria.id,
        'tramite': 'ACTA DE NACIMIENTO',
        'precio': '',
        'costo': 50,
        'cantidad': 1,
        'fecha': datetime.today().strftime('%Y-%m-%d')
    }
    response = client.post(url_for('papeleria.registrar_tramite'), data=data)
    assert b'No hay precio predefinido' in response.data

def test_precio_negativo(client):
    user, papeleria = create_user_and_papeleria(db)
    login(client, 'testuser', 'testpass')
    data = {
        'papeleria_id': papeleria.id,
        'tramite': 'ACTA DE NACIMIENTO',
        'precio': -10,
        'costo': 50,
        'cantidad': 1,
        'fecha': datetime.today().strftime('%Y-%m-%d')
    }
    response = client.post(url_for('papeleria.registrar_tramite'), data=data)
    # Buscar el mensaje real de error de WTForms
    assert b'Number must be at least 0' in response.data or b'no puede ser negativo' in response.data

def test_edicion_masiva_precios(client):
    user, papeleria = create_user_and_papeleria(db)
    login(client, 'testuser', 'testpass')
    precios_data = {
        'ACTA DE NACIMIENTO': 120,
        'ACTA DE MATRIMONIO': 130,
        'csrf_token': 'dummy'  # Para evitar error de CSRF en template
    }
    response = client.post(url_for('papeleria.gestionar_precios_papeleria', papeleria_id=papeleria.id), data=precios_data, follow_redirects=True)
    assert b'Precios actualizados' in response.data
    precio = PapeleriaPrecio.query.filter_by(papeleria_id=papeleria.id, tramite='ACTA DE NACIMIENTO').first()
    assert precio is not None
    assert precio.precio == 120

def test_seguridad_modificacion_ajena(client):
    user, papeleria = create_user_and_papeleria(db)
    # Crear precio original
    precio_original = PapeleriaPrecio(papeleria_id=papeleria.id, tramite='ACTA DE NACIMIENTO', precio=100)
    db.session.add(precio_original)
    db.session.commit()
    # Crear otro usuario real
    otro_user = User(username='otro', role='employee')
    otro_user.set_password('pass')
    db.session.add(otro_user)
    db.session.commit()
    login(client, 'otro', 'pass')
    precios_data = {'ACTA DE NACIMIENTO': 999, 'csrf_token': 'dummy'}
    response = client.post(url_for('papeleria.gestionar_precios_papeleria', papeleria_id=papeleria.id), data=precios_data, follow_redirects=True)
    # Refrescar el precio desde la base de datos
    db.session.refresh(precio_original)
    assert precio_original.precio == 100  # El precio no debe cambiar
