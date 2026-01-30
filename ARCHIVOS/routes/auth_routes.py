from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
import logging

from ..forms import LoginForm, UserForm, CambiarPasswordForm, CrearUsuarioForm, AdminResetPasswordForm, DeleteForm
from ..utils import admin_required
from ..database import user_repository
from ..models import User
from ..logging_config import log_security_event, log_action, log_error

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data.strip().lower()
        password = form.password.data
        client_ip = request.remote_addr or request.headers.get('X-Forwarded-For', 'unknown')
        
        user = user_repository.get_by_username(username)

        if user and user.check_password(password):
            login_user(user, remember=form.remember.data)
            
            # Log de seguridad: login exitoso
            log_security_event('login', True, {
                'username': username,
                'user_id': user.id,
                'remember': form.remember.data
            })
            
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                next_page = url_for('main.index')
            return redirect(next_page)
        else:
            # Log de seguridad: intento de login fallido (CRÍTICO para detectar ataques)
            log_security_event('login', False, {
                'username_attempted': username,
                'user_exists': user is not None,
                'ip': client_ip
            })
            flash('Usuario o contraseña incorrectos.', 'danger')

    return render_template('login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    username = current_user.username
    user_id = current_user.id
    logout_user()
    
    # Log de seguridad: logout
    log_security_event('logout', True, {'username': username, 'user_id': user_id})
    
    flash('Has cerrado sesión.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    form = CambiarPasswordForm()
    if form.validate_on_submit():
        user = user_repository.get_by_id(current_user.id)

        if not user.check_password(form.password_actual.data):
            # Log de seguridad: intento de cambio de password fallido
            log_security_event('password_change', False, {
                'user_id': current_user.id,
                'reason': 'incorrect_current_password'
            })
            flash('La contraseña actual es incorrecta.', 'danger')
            return render_template('perfil.html', form=form)

        user_repository.update_password(current_user.id, form.nuevo_password.data)
        
        # Log de seguridad: cambio de password exitoso
        log_security_event('password_change', True, {'user_id': current_user.id})
        
        flash('Tu contraseña ha sido actualizada con éxito.', 'success')
        return redirect(url_for('auth.perfil'))

    return render_template('perfil.html', form=form)

# --- Rutas de Administración de Usuarios (Solo Admin) ---

@auth_bp.route('/admin/usuarios')
@login_required
@admin_required
def listar_usuarios():
    log_action('admin_list_users', {'admin_id': current_user.id})
    usuarios = user_repository.get_all_except(current_user.id)
    reset_form = AdminResetPasswordForm()
    return render_template('usuarios.html', usuarios=usuarios, reset_form=reset_form)

@auth_bp.route('/admin/usuarios/crear', methods=['GET', 'POST'])
@login_required
@admin_required
def crear_usuario():
    form = CrearUsuarioForm()
    if form.validate_on_submit():
        try:
            new_user = user_repository.create(
                username=form.username.data.strip().lower(),
                password=form.password.data,
                role=form.role.data
            )
            # Log de seguridad: creación de usuario
            log_security_event('user_created', True, {
                'admin_id': current_user.id,
                'new_username': form.username.data,
                'new_user_role': form.role.data
            })
            flash(f"Usuario '{form.username.data}' creado con éxito.", 'success')
            return redirect(url_for('auth.listar_usuarios'))
        except ValueError as e:
            log_security_event('user_created', False, {
                'admin_id': current_user.id,
                'attempted_username': form.username.data,
                'error': str(e)
            })
            # FIX: Render the form again with the error message instead of leaving the request hanging.
            form.username.errors.append(str(e))
    
    return render_template('crear_usuario.html', form=form), 422 if form.errors else 200

@auth_bp.route('/admin/usuarios/editar/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_usuario(user_id):
    user = user_repository.get_by_id(user_id)
    if not user:
        log_action('admin_edit_user_not_found', {'admin_id': current_user.id, 'target_user_id': user_id}, 'warning')
        flash('Error: Usuario no encontrado.', 'danger')
        return redirect(url_for('auth.listar_usuarios'))
 
    form = UserForm(obj=user)
    if form.validate_on_submit():
        try:
            user_repository.update(
                user_id=user_id,
                username=form.username.data.strip().lower(),
                role=form.role.data,
                password=form.password.data or None
            )
            log_security_event('user_updated', True, {
                'admin_id': current_user.id,
                'target_user_id': user_id,
                'new_username': form.username.data,
                'new_role': form.role.data,
                'password_changed': bool(form.password.data)
            })
            flash(f"Usuario '{form.username.data}' actualizado con éxito.", 'success')
            return redirect(url_for('auth.listar_usuarios'))
        except ValueError as e:
            log_security_event('user_updated', False, {
                'admin_id': current_user.id,
                'target_user_id': user_id,
                'error': str(e)
            })
            flash(str(e), 'danger')
 
    return render_template('form_usuario.html', form=form, titulo=f"Editar Usuario: {user.username}")

@auth_bp.route('/admin/usuarios/eliminar/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def eliminar_usuario(user_id):
    if user_id == current_user.id:
        log_security_event('user_delete_self_attempt', False, {'admin_id': current_user.id})
        flash('Error: No puedes eliminar tu propia cuenta de administrador.', 'danger')
        return redirect(url_for('auth.listar_usuarios'))

    form = DeleteForm()
    if form.validate_on_submit():
        # Obtener info del usuario antes de eliminarlo para el log
        user_to_delete = user_repository.get_by_id(user_id)
        username_deleted = user_to_delete.username if user_to_delete else 'unknown'
        
        try:
            user_repository.delete(user_id)
            
            log_security_event('user_deleted', True, {
                'admin_id': current_user.id,
                'deleted_user_id': user_id,
                'deleted_username': username_deleted
            })
            flash('Usuario y todos sus datos asociados han sido eliminados con éxito.', 'success')
        except ValueError as e:
            log_security_event('user_deleted', False, {
                'admin_id': current_user.id,
                'target_user_id': user_id,
                'error': str(e)
            })
            flash(str(e), 'danger')
    else:
        log_action('admin_delete_user_validation_failed', {'admin_id': current_user.id, 'target_user_id': user_id}, 'warning')
        flash('Error de validación al intentar eliminar el usuario.', 'danger')

    return redirect(url_for('auth.listar_usuarios'))

@auth_bp.route('/admin/usuarios/reset-password/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def reset_password_admin(user_id):
    if user_id == current_user.id:
        log_action('admin_reset_own_password_attempt', {'admin_id': current_user.id}, 'warning')
        flash('No puedes restablecer tu propia contraseña desde esta interfaz. Ve a "Mi Perfil".', 'warning')
        return redirect(url_for('auth.listar_usuarios'))

    form = AdminResetPasswordForm()
    if form.validate_on_submit():
        user_repository.update_password(user_id, form.nuevo_password.data)
        
        log_security_event('admin_password_reset', True, {
            'admin_id': current_user.id,
            'target_user_id': user_id
        })
        flash('La contraseña del usuario ha sido restablecida con éxito.', 'success')
    else:
        log_security_event('admin_password_reset', False, {
            'admin_id': current_user.id,
            'target_user_id': user_id,
            'errors': str(form.errors)
        })
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error al restablecer: {error}", 'danger')
    return redirect(url_for('auth.listar_usuarios'))

@auth_bp.route('/admin/view_as/<int:user_id>')
@login_required
@admin_required
def view_user_dashboard(user_id):
    user_to_view = user_repository.get_by_id(user_id)
    if not user_to_view:
        log_action('admin_view_as_user_not_found', {'admin_id': current_user.id, 'target_user_id': user_id}, 'warning')
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for('auth.listar_usuarios'))

    session['viewing_user_id'] = user_id
    session['viewing_user_name'] = user_to_view.username
    
    # Log de seguridad: impersonación de usuario (CRÍTICO)
    log_security_event('impersonation_start', True, {
        'admin_id': current_user.id,
        'admin_username': current_user.username,
        'impersonated_user_id': user_id,
        'impersonated_username': user_to_view.username
    })
    
    return redirect(url_for('main.index'))

@auth_bp.route('/admin/stop_viewing')
@login_required
@admin_required
def stop_viewing():
    impersonated_user_id = session.get('viewing_user_id')
    impersonated_username = session.get('viewing_user_name')
    
    session.pop('viewing_user_id', None)
    session.pop('viewing_user_name', None)
    
    # Log de seguridad: fin de impersonación
    log_security_event('impersonation_end', True, {
        'admin_id': current_user.id,
        'impersonated_user_id': impersonated_user_id,
        'impersonated_username': impersonated_username
    })
    
    flash("Has vuelto a tu panel de administrador.", "success")
    return redirect(url_for('main.index'))
