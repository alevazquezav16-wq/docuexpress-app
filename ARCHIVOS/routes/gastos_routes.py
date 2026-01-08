from flask import Blueprint, render_template, redirect, url_for, flash, request, make_response, send_from_directory, current_app
from flask_login import login_required, current_user
from datetime import datetime
import os
import logging
from werkzeug.utils import secure_filename

from ..forms import GastoForm, EditarGastoForm, ProveedorForm, EditarProveedorForm, CATEGORIAS_GASTOS, DeleteForm
from ..utils import get_effective_user_id, bump_user_data_version
from ..database import gasto_repository, proveedor_repository

gastos_bp = Blueprint('gastos', __name__)

def _save_receipt(file):
    """Guarda el archivo de recibo de forma segura y devuelve el nombre del archivo."""
    if not file:
        return None
    filename = secure_filename(file.filename)
    unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
    
    receipts_folder = current_app.config.get('RECEIPTS_FOLDER')
    
    # Asegurarse de que el directorio exista
    if not receipts_folder.exists():
        os.makedirs(receipts_folder)

    file.save(os.path.join(receipts_folder, unique_filename))
    return unique_filename

@gastos_bp.route('/gastos', methods=['GET', 'POST'])
@login_required
def gestion_gastos():
    effective_user_id = get_effective_user_id()

    gasto_original = None
    if 'duplicar' in request.args and request.method == 'GET':
        gasto_original_id = request.args.get('duplicar')
        gasto_original = gasto_repository.get_by_id(gasto_original_id, effective_user_id)

    form = GastoForm(obj=gasto_original) if gasto_original else GastoForm()
    form.proveedor_id.choices = [(p.id, p.nombre) for p in proveedor_repository.get_all(effective_user_id)]

    if form.validate_on_submit():
        receipt_filename = _save_receipt(form.recibo.data)
        gasto_repository.add(
            proveedor_id=form.proveedor_id.data,
            descripcion=form.descripcion.data,
            monto=form.monto.data,
            fecha=form.fecha.data.strftime('%Y-%m-%d'),
            categoria=form.categoria.data,
            user_id=effective_user_id,
            receipt_filename=receipt_filename
        )
        bump_user_data_version(effective_user_id) # Invalidar caché
        flash('Gasto registrado con éxito.', 'success')

        if request.headers.get('HX-Request'):
            new_form = GastoForm()
            new_form.proveedor_id.choices = [(p.id, p.nombre) for p in proveedor_repository.get_all(effective_user_id)]
            response_html = render_template('form_gasto.html', form=new_form)
            response = make_response(response_html)
            response.headers['HX-Trigger'] = 'reload-gastos-table, reload-charts, new-flash-message'
            return response
        
        return redirect(url_for('gastos.gestion_gastos'))

    if request.method == 'POST' and request.headers.get('HX-Request'):
        return render_template('form_gasto.html', form=form), 422

    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    categoria_filtro = request.args.get('categoria')
    page = request.args.get('page', 1, type=int)
    per_page = 15

    gastos, total_items = gasto_repository.get_all(
        effective_user_id, page, per_page, fecha_inicio, fecha_fin, categoria_filtro
    )
    total_pages = (total_items + per_page - 1) // per_page if total_items > 0 else 1

    delete_form = DeleteForm()
    context = {
        'form': form,
        'gastos': gastos,
        'current_page': page,
        'total_pages': total_pages,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'categoria_filtro': categoria_filtro,
        'categorias_gastos': CATEGORIAS_GASTOS,
        'delete_form': delete_form
    }

    if request.headers.get('HX-Request'):
        return render_template('tabla_gastos.html', **context)

    return render_template('gastos.html', **context)

@gastos_bp.route('/gastos/editar/<int:gasto_id>', methods=['GET', 'POST'])
@login_required
def editar_gasto(gasto_id):
    effective_user_id = get_effective_user_id()
    gasto = gasto_repository.get_by_id(gasto_id, effective_user_id)
    if not gasto:
        flash('Gasto no encontrado.', 'danger')
        return redirect(url_for('gastos.gestion_gastos'))

    form = EditarGastoForm(obj=gasto)
    form.proveedor_id.choices = [(p.id, p.nombre) for p in proveedor_repository.get_all(effective_user_id)]

    if form.validate_on_submit():
        receipt_filename = gasto.receipt_filename
        if form.recibo.data and form.recibo.data.filename:
            receipt_filename = _save_receipt(form.recibo.data)

        gasto_repository.update(
            gasto_id, effective_user_id,
            proveedor_id=form.proveedor_id.data,
            descripcion=form.descripcion.data,
            monto=form.monto.data,
            fecha=form.fecha.data.strftime('%Y-%m-%d'),
            categoria=form.categoria.data,
            receipt_filename=receipt_filename
        )
        bump_user_data_version(effective_user_id) # Invalidar caché
        flash('Gasto actualizado con éxito.', 'success')
        return redirect(url_for('gastos.gestion_gastos'))

    if request.method == 'GET':
        form.fecha.data = gasto.fecha

    return render_template('editar_gasto.html', form=form, gasto_id=gasto_id)

@gastos_bp.route('/gastos/eliminar/<int:gasto_id>', methods=['POST'])
@login_required
def eliminar_gasto(gasto_id):
    form = DeleteForm()
    if form.validate_on_submit():
        effective_user_id = get_effective_user_id()
        gasto_repository.delete(gasto_id, effective_user_id)
        bump_user_data_version(effective_user_id) # Invalidar caché
        flash('Gasto eliminado con éxito.', 'success')
    else:
        flash('Error de validación al intentar eliminar el gasto.', 'danger')

    return redirect(url_for('gastos.gestion_gastos'))

@gastos_bp.route('/recibo/<filename>')
@login_required
def ver_recibo(filename):
    """Ruta segura para servir los archivos de recibos."""
    if not gasto_repository.does_receipt_belong_to_user(filename, get_effective_user_id()):
        flash('No tienes permiso para ver este archivo.', 'danger')
        return redirect(url_for('gastos.gestion_gastos'))

    receipts_folder = current_app.config.get('RECEIPTS_FOLDER')
    if not receipts_folder:
         receipts_folder = os.path.join(current_app.root_path, 'static/receipts')
         
    return send_from_directory(receipts_folder, filename)

@gastos_bp.route('/proveedores', methods=['GET', 'POST'])
@login_required
def gestion_proveedores():
    effective_user_id = get_effective_user_id()
    form = ProveedorForm()
    if form.validate_on_submit():
        proveedor_repository.add(form.nombre.data, effective_user_id)
        bump_user_data_version(effective_user_id) # Invalidar caché
        flash(f'Proveedor "{form.nombre.data}" agregado con éxito.', 'success')
        return redirect(url_for('gastos.gestion_proveedores'))

    delete_form = DeleteForm()
    proveedores = proveedor_repository.get_all(effective_user_id)
    return render_template('proveedores.html', proveedores=proveedores, form=form, delete_form=delete_form)

@gastos_bp.route('/proveedores/editar/<int:proveedor_id>', methods=['GET', 'POST'])
@login_required
def editar_proveedor(proveedor_id):
    effective_user_id = get_effective_user_id()
    proveedor = proveedor_repository.get_by_id(proveedor_id, effective_user_id)
    if not proveedor:
        flash('Proveedor no encontrado.', 'danger')
        return redirect(url_for('gastos.gestion_proveedores'))

    form = EditarProveedorForm(obj=proveedor)
    if form.validate_on_submit():
        proveedor_repository.update(proveedor_id, form.nombre.data, effective_user_id)
        bump_user_data_version(effective_user_id) # Invalidar caché
        flash('Proveedor actualizado con éxito.', 'success')
        return redirect(url_for('gastos.gestion_proveedores'))

    return render_template('editar_proveedor.html', form=form, proveedor_id=proveedor_id)

@gastos_bp.route('/proveedores/eliminar/<int:proveedor_id>', methods=['POST'])
@login_required
def eliminar_proveedor(proveedor_id):
    form = DeleteForm()
    if form.validate_on_submit():
        effective_user_id = get_effective_user_id()
        if proveedor_repository.is_in_use(proveedor_id, effective_user_id):
            flash('No se puede eliminar el proveedor porque tiene gastos asociados. Elimine o reasigne los gastos primero.', 'danger')
            if request.headers.get('HX-Request'):
                response = make_response()
                response.headers['HX-Redirect'] = url_for('gastos.gestion_proveedores')
                return response
            return redirect(url_for('gastos.gestion_proveedores'))

        proveedor_repository.delete(proveedor_id, effective_user_id)
        bump_user_data_version(effective_user_id) # Invalidar caché
        flash('Proveedor eliminado con éxito.', 'success')
    else:
        flash('Error de validación al intentar eliminar el proveedor.', 'danger')
    if request.headers.get('HX-Request'):
        response = make_response()
        response.headers['HX-Redirect'] = url_for('gastos.gestion_proveedores')
        return response
    return redirect(url_for('gastos.gestion_proveedores'))
