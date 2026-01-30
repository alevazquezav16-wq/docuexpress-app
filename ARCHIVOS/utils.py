from flask import flash, redirect, url_for, session, current_app
from functools import wraps
from flask_login import current_user
from .models import Papeleria, db
import os
# Pillow es opcional (ahorra ~7MB en PythonAnywhere gratis)
try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
from werkzeug.utils import secure_filename
from datetime import datetime
import threading
import smtplib
from email.message import EmailMessage
import logging


# --- Helpers de Usuario ---
def get_effective_user_id():
    """
    Devuelve el ID del usuario que se está viendo si el admin está en modo "Ver como",
    de lo contrario, devuelve el ID del usuario actual.
    """
    if current_user.is_authenticated and current_user.role == 'admin' and 'viewing_user_id' in session:
        return session.get('viewing_user_id')
    if current_user.is_authenticated:
        return current_user.get_id()
    return None

# --- Decoradores ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('No tienes permiso para acceder a esta página.', 'danger')
            return redirect(url_for('main.index')) # Asumiendo que index estará en main_bp
        return f(*args, **kwargs)
    return decorated_function

def check_papeleria_owner(f):
    """
    Decorador para verificar que la papelería especificada en la URL
    pertenece al usuario actualmente logueado, o que el usuario es admin.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        papeleria_id = kwargs.get('papeleria_id')
        user_id = get_effective_user_id()

        # Los admins pueden acceder a cualquier papelería
        if current_user.is_authenticated and current_user.role == 'admin':
            papeleria = Papeleria.query.filter_by(id=papeleria_id, is_active=True).first()
            if not papeleria:
                flash('Papelería no encontrada.', 'danger')
                return redirect(url_for('main.index'))
        else:
            # Usuarios normales solo pueden acceder a sus propias papelerías
            papeleria = Papeleria.query.filter_by(id=papeleria_id, user_id=user_id, is_active=True).first()
            if not papeleria:
                flash('No tienes permiso para acceder a esta papelería.', 'danger')
                return redirect(url_for('main.index'))

        return f(*args, **kwargs)
    return decorated_function

def is_allowed_file(filename):
    """Verifica si la extensión del archivo es permitida."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def save_logo_image(file, user_id):
    """
    Valida, redimensiona y guarda la imagen del logo para un usuario.
    Lanza una excepción si hay un error.
    """
    if not is_allowed_file(file.filename):
        raise Exception('Tipo de archivo no permitido. Usa PNG, JPG o JPEG.')
    filename = secure_filename(f"logo_{user_id}.png")

    try:
        # Construir la ruta de guardado
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        
        if PILLOW_AVAILABLE:
            # Redimensionar y optimizar la imagen antes de guardarla
            img = Image.open(file.stream)
            img.thumbnail((300, 300))  # Redimensiona manteniendo el aspect ratio
            img.save(filepath, "PNG", optimize=True)
        else:
            # Sin Pillow, guardar directamente (sin redimensionar)
            file.save(filepath)
    except Exception as e:
        # Relanzar la excepción con un mensaje más claro.
        raise Exception(f'El archivo subido no es una imagen válida. Error: {e}')

def get_user_data_version(user_id):
    """Obtiene la versión actual de los datos del usuario para invalidación de caché."""
    cache = getattr(current_app, 'cache', None)
    if not cache:
        return None
    key = f"data_ver:{user_id}"
    version = cache.get(key)
    if not version:
        version = str(int(datetime.now().timestamp()))
        cache.set(key, version, timeout=0)
    return version

def bump_user_data_version(user_id):
    """Actualiza la versión de los datos del usuario, invalidando cachés dependientes."""
    cache = getattr(current_app, 'cache', None)
    if cache:
        key = f"data_ver:{user_id}"
        new_version = str(int(datetime.now().timestamp()))
        cache.set(key, new_version, timeout=0)

def send_error_email_async(subject, body):
    """
    Envía un email de alerta en un hilo separado para no bloquear la aplicación.
    """
    def _send():
        EMAIL_ENABLED = os.environ.get('ERROR_EMAIL_ENABLED', 'False').lower() == 'true'
        if not EMAIL_ENABLED:
            return
            
        EMAIL_TO = os.environ.get('ERROR_EMAIL_TO')
        EMAIL_FROM = os.environ.get('ERROR_EMAIL_FROM')
        EMAIL_HOST = os.environ.get('ERROR_EMAIL_HOST')
        EMAIL_PORT = int(os.environ.get('ERROR_EMAIL_PORT', 587))
        EMAIL_USER = os.environ.get('ERROR_EMAIL_USER')
        EMAIL_PASS = os.environ.get('ERROR_EMAIL_PASS')
        
        if not all([EMAIL_TO, EMAIL_FROM, EMAIL_HOST, EMAIL_USER, EMAIL_PASS]):
            logging.error("Faltan variables de entorno para email de error.")
            return
            
        try:
            msg = EmailMessage()
            msg.set_content(body)
            msg['Subject'] = subject
            msg['From'] = EMAIL_FROM
            msg['To'] = EMAIL_TO
            
            with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
                server.starttls()
                server.login(EMAIL_USER, EMAIL_PASS)
                server.send_message(msg)
            logging.info(f"Alerta de error enviada a {EMAIL_TO}")
        except Exception as e:
            logging.error(f"Error enviando email de alerta: {e}")

    # Ejecutar en un hilo demonio para que no bloquee el cierre de la app
    thread = threading.Thread(target=_send)
    thread.daemon = True
    thread.start()
