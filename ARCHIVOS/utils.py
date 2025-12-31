from flask import flash, redirect, url_for, session, current_app
from functools import wraps
from flask_login import current_user
from .models import Papeleria, db
import os
from PIL import Image
from werkzeug.utils import secure_filename


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
        # Redimensionar y optimizar la imagen antes de guardarla
        img = Image.open(file.stream)
        img.thumbnail((300, 300))  # Redimensiona manteniendo el aspect ratio

        # Construir la ruta de guardado
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

        img.save(filepath, "PNG", optimize=True)
    except Exception as e:
        # Relanzar la excepción con un mensaje más claro.
        raise Exception(f'El archivo subido no es una imagen válida. Error: {e}')
