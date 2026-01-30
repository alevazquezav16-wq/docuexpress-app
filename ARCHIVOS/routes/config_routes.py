from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify, send_file
from flask_login import login_required, current_user
import os
from datetime import datetime

from ..utils import get_effective_user_id, admin_required, save_logo_image
from ..forms import ConfigForm
from ..database import tramite_repository
from ..constants import TRAMITES_PREDEFINIDOS

# backup_manager es opcional (no funciona sin APScheduler)
try:
    from ..backup_manager import backup_manager, APSCHEDULER_AVAILABLE
except ImportError:
    backup_manager = None
    APSCHEDULER_AVAILABLE = False

config_bp = Blueprint('config', __name__, url_prefix='/configuracion')

def _get_all_tramites(user_id):
    """Función auxiliar para obtener una lista única y ordenada de todos los trámites."""
    tramites_usuario = tramite_repository.get_distinct_tramites(user_id)
    todos_los_tramites = sorted(list(set(TRAMITES_PREDEFINIDOS + tramites_usuario)))
    return todos_los_tramites

@config_bp.route('/', methods=['GET'])
@login_required
@admin_required
def configuracion():
    """Página para configurar costos por defecto de trámites."""
    form = ConfigForm()
    effective_user_id = get_effective_user_id()
    todos_los_tramites = _get_all_tramites(effective_user_id)
    
    costos_actuales = tramite_repository.get_all_costos(effective_user_id)
    for tramite in todos_los_tramites:
        if tramite not in costos_actuales:
            costos_actuales[tramite] = ''

    return render_template('configuracion.html', form=form, costos=costos_actuales, tramites=todos_los_tramites)

@config_bp.route('/guardar-costos', methods=['POST'])
@login_required
@admin_required
def guardar_costos():
    """Guarda los costos por defecto de los trámites de forma segura."""
    form = ConfigForm()
    if form.validate_on_submit():
        effective_user_id = get_effective_user_id()
        todos_los_tramites = _get_all_tramites(effective_user_id)
        
        for tramite in todos_los_tramites:
            costo_str = request.form.get(tramite)
            if costo_str:
                try:
                    tramite_repository.set_costo(tramite, float(costo_str), effective_user_id)
                except ValueError:
                    flash(f'El costo para "{tramite}" debe ser un número válido.', 'danger')
        flash('Costos por defecto actualizados correctamente.', 'success')
    else:
        flash('Error de validación al guardar los costos. Inténtalo de nuevo.', 'danger')
    
    return redirect(url_for('config.configuracion'))

@config_bp.route('/manage-logo', methods=['POST'])
@login_required
@admin_required
def manage_logo():
    """Gestiona la subida y eliminación del logo de la empresa."""
    form = ConfigForm()
    if form.validate_on_submit():
        action = request.form.get('action')
        user_id = get_effective_user_id()
        logo_filename = f"logo_{user_id}.png"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], logo_filename)

        if action == 'upload':
            if 'logo' not in request.files or not request.files['logo'].filename:
                flash('No se seleccionó ningún archivo para subir.', 'danger')
                return redirect(url_for('config.configuracion'))

            file = request.files['logo']

            try:
                save_logo_image(file, user_id)
                flash('Logo actualizado y optimizado con éxito.', 'success')
            except Exception as e:
                current_app.logger.error(f"Error al procesar el logo para el usuario {user_id}: {e}")
                flash(str(e), 'danger')

        elif action == 'delete':
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    flash('Logo eliminado con éxito.', 'success')
                except OSError as e:
                    current_app.logger.error(f"Error al eliminar el logo {filepath}: {e}")
                    flash(f'Error al eliminar el logo: {e}', 'danger')
            else:
                flash('No se encontró ningún logo para eliminar.', 'warning')
        else:
            flash('Acción no reconocida.', 'danger')
    else:
        flash('Error de validación al gestionar el logo.', 'danger')

    return redirect(url_for('config.configuracion'))

@config_bp.route('/actualizar-costos-viejos', methods=['POST'])
@login_required
@admin_required
def actualizar_costos_viejos():
    form = ConfigForm()
    if form.validate_on_submit():
        num_actualizados = tramite_repository.update_old_costos(get_effective_user_id())
        if num_actualizados > 0:
            flash(f'¡Proceso completado! Se actualizaron los costos de {num_actualizados} trámites anteriores.', 'success')
        else:
            flash('No se encontraron trámites con costo cero para actualizar.', 'info')
    else:
        flash('Error de validación al actualizar los costos.', 'danger')
    return redirect(url_for('config.configuracion'))


# ==================== GESTIÓN DE BACKUPS ====================

@config_bp.route('/backups')
@login_required
@admin_required
def list_backups():
    """Lista todos los backups disponibles."""
    if not backup_manager or not APSCHEDULER_AVAILABLE:
        return jsonify({
            'success': False,
            'message': 'Sistema de backups no disponible (APScheduler no instalado)',
            'backups': [],
            'count': 0,
            'enabled': False
        })
    backups = backup_manager.list_backups()
    return jsonify({
        'success': True,
        'backups': backups,
        'count': len(backups),
        'enabled': backup_manager.enabled
    })

@config_bp.route('/backups/create', methods=['POST'])
@login_required
@admin_required
def create_backup():
    """Crea un backup manual de la base de datos."""
    if not backup_manager or not APSCHEDULER_AVAILABLE:
        return jsonify({
            'success': False,
            'message': 'Sistema de backups no disponible'
        }), 503
    backup_path = backup_manager.create_backup(manual=True)
    
    if backup_path:
        return jsonify({
            'success': True,
            'message': 'Backup creado exitosamente',
            'filename': backup_path.name,
            'size': backup_path.stat().st_size
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Error al crear el backup'
        }), 500

@config_bp.route('/backups/download/<filename>')
@login_required
@admin_required
def download_backup(filename):
    """Descarga un backup específico."""
    if not backup_manager or not APSCHEDULER_AVAILABLE:
        flash('Sistema de backups no disponible', 'warning')
        return redirect(url_for('config.configuracion'))
    backup_path = backup_manager.backup_dir / filename
    
    if not backup_path.exists() or not backup_path.is_file():
        flash('Backup no encontrado', 'danger')
        return redirect(url_for('config.configuracion'))
    
    return send_file(
        backup_path,
        as_attachment=True,
        download_name=filename,
        mimetype='application/x-sqlite3'
    )

@config_bp.route('/backups/restore/<filename>', methods=['POST'])
@login_required
@admin_required
def restore_backup(filename):
    """Restaura la base de datos desde un backup."""
    if not backup_manager or not APSCHEDULER_AVAILABLE:
        return jsonify({
            'success': False,
            'message': 'Sistema de backups no disponible'
        }), 503
    success = backup_manager.restore_backup(filename)
    
    if success:
        flash('Base de datos restaurada exitosamente. Por favor, reinicia la aplicación.', 'success')
        return jsonify({
            'success': True,
            'message': 'Base de datos restaurada. Reinicia la aplicación.'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Error al restaurar el backup'
        }), 500


# ==================== GESTIÓN DE LOGS ====================

@config_bp.route('/logs')
@login_required
@admin_required
def view_logs():
    """Muestra los últimos registros del log del sistema."""
    level = request.args.get('level')
    log_file = current_app.config.get('LOG_FILE', 'docuexpress.log')
    
    # Intentar resolver la ruta absoluta si no lo es
    if not os.path.isabs(log_file):
        log_file = os.path.abspath(log_file)
        
    logs = []
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                # Leer todo el archivo y tomar las últimas 1000 líneas
                lines = f.readlines()
                
                # Filtrar si se solicita un nivel específico
                if level and level != 'ALL':
                    lines = [line for line in lines if level.upper() in line.upper()]
                
                logs = lines[-1000:]
                logs.reverse() # Lo más reciente arriba
        except Exception as e:
            logs = [f"Error leyendo el archivo de logs: {str(e)}"]
    else:
        logs = [f"Archivo de log no encontrado en: {log_file}"]
        
    return render_template('logs.html', logs=logs, log_path=log_file, current_level=level)

@config_bp.route('/logs/download')
@login_required
@admin_required
def download_logs():
    """Descarga el archivo de logs."""
    log_file = current_app.config.get('LOG_FILE', 'docuexpress.log')
    if not os.path.isabs(log_file):
        log_file = os.path.abspath(log_file)
        
    if os.path.exists(log_file):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return send_file(
            log_file,
            as_attachment=True,
            download_name=f"docuexpress_logs_{timestamp}.log",
            mimetype='text/plain'
        )
    else:
        flash('El archivo de logs no existe.', 'danger')
        return redirect(url_for('config.view_logs'))
