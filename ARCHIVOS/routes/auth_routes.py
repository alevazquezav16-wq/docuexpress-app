from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from ..forms import LoginForm, UserForm, CambiarPasswordForm, CrearUsuarioForm, AdminResetPasswordForm, DeleteForm
from ..utils import admin_required
from ..database import user_repository
from ..models import User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data.strip().lower()
        password = form.password.data
        
        user = user_repository.get_by_username(username)

        if user and user.check_password(password):
            login_user(user, remember=form.remember.data)
            return redirect(url_for('main.index'))
        else:
            flash('Usuario o contraseña incorrectos.', 'danger')

    return render_template('login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    form = CambiarPasswordForm()
    if form.validate_on_submit():
        user = user_repository.get_by_id(current_user.id)

        if not user.check_password(form.password_actual.data):
            flash('La contraseña actual es incorrecta.', 'danger')
            return render_template('perfil.html', form=form)

        user_repository.update_password(current_user.id, form.nuevo_password.data)
        flash('Tu contraseña ha sido actualizada con éxito.', 'success')
        return redirect(url_for('auth.perfil'))

    return render_template('perfil.html', form=form)

# --- Rutas de Administración de Usuarios (Solo Admin) ---

@auth_bp.route('/admin/usuarios')
@login_required
@admin_required
def listar_usuarios():
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
            user_repository.create(
                username=form.username.data.strip().lower(),
                password=form.password.data,
                role=form.role.data
            )
            flash(f"Usuario '{form.username.data}' creado con éxito.", 'success')
            return redirect(url_for('auth.listar_usuarios'))
        except ValueError as e:
            # FIX: Render the form again with the error message instead of leaving the request hanging.
            form.username.errors.append(str(e))
    
    return render_template('crear_usuario.html', form=form), 422 if form.errors else 200

@auth_bp.route('/admin/usuarios/editar/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_usuario(user_id):
    user = user_repository.get_by_id(user_id)
    if not user:
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
            flash(f"Usuario '{form.username.data}' actualizado con éxito.", 'success')
            return redirect(url_for('auth.listar_usuarios'))
        except ValueError as e:
            flash(str(e), 'danger')
 
    return render_template('form_usuario.html', form=form, titulo=f"Editar Usuario: {user.username}")

@auth_bp.route('/admin/usuarios/eliminar/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def eliminar_usuario(user_id):
    if user_id == current_user.id:
        flash('Error: No puedes eliminar tu propia cuenta de administrador.', 'danger')
        return redirect(url_for('auth.listar_usuarios'))

    form = DeleteForm()
    if form.validate_on_submit():
        user_repository.delete(user_id)
        flash('Usuario y todos sus datos asociados han sido eliminados con éxito.', 'success')
    else:
        flash('Error de validación al intentar eliminar el usuario.', 'danger')

    return redirect(url_for('auth.listar_usuarios'))

@auth_bp.route('/admin/usuarios/reset-password/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def reset_password_admin(user_id):
    if user_id == current_user.id:
        flash('No puedes restablecer tu propia contraseña desde esta interfaz. Ve a "Mi Perfil".', 'warning')
        return redirect(url_for('auth.listar_usuarios'))

    form = AdminResetPasswordForm()
    if form.validate_on_submit():
        user_repository.update_password(user_id, form.nuevo_password.data)
        flash('La contraseña del usuario ha sido restablecida con éxito.', 'success')
    else:
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
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for('auth.listar_usuarios'))

    session['viewing_user_id'] = user_id
    session['viewing_user_name'] = user_to_view.username
    return redirect(url_for('main.index'))

@auth_bp.route('/admin/stop_viewing')
@login_required
@admin_required
def stop_viewing():
    session.pop('viewing_user_id', None)
    session.pop('viewing_user_name', None)
    flash("Has vuelto a tu panel de administrador.", "success")
    return redirect(url_for('main.index'))
