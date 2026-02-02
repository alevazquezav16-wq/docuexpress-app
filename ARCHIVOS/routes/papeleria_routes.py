from flask import Blueprint, render_template, redirect, url_for, flash, request, make_response, send_file, current_app, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import os
import io
import json
import csv
import logging

from ..forms import PapeleriaForm, TramiteForm, EditarTramiteForm, EditarPapeleriaForm, DeleteForm
from ..utils import get_effective_user_id, check_papeleria_owner, admin_required, bump_user_data_version
from ..database import papeleria_repository, tramite_repository, gasto_repository
from ..constants import TRAMITES_PREDEFINIDOS
from ..pdf_generator import generar_pdf_papeleria
from ..logging_config import log_action, log_db_operation, log_error

papeleria_bp = Blueprint('papeleria', __name__)

@papeleria_bp.route('/papeleria/<int:papeleria_id>')
@login_required
@check_papeleria_owner
def ver_papeleria(papeleria_id):
    """Página de detalle para una papelería específica."""
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')

    form_tramite = TramiteForm(papeleria_id=papeleria_id)

    page = request.args.get('page', 1, type=int)
    per_page = 20
    effective_user_id = get_effective_user_id()
    
    detalles, total_items, total_pages = tramite_repository.get_details_for_papeleria(papeleria_id, effective_user_id, fecha_inicio, fecha_fin, page, per_page)
    totales_papeleria = papeleria_repository.total_por_papeleria(papeleria_id, effective_user_id, fecha_inicio, fecha_fin)
    nombre_papeleria = papeleria_repository.get_name(papeleria_id, effective_user_id)

    periodo_str = "Histórico"
    if fecha_inicio and fecha_fin:
        inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d')
        fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d')
        periodo_str = f"{inicio_dt.strftime('%d/%m/%Y')} al {fin_dt.strftime('%d/%m/%Y')}"
    
    delete_form = DeleteForm()
    return render_template('papeleria.html', 
                           nombre_papeleria=nombre_papeleria,
                           papeleria_id=papeleria_id,
                           detalles=detalles,
                           totales=totales_papeleria,
                           fecha_inicio=fecha_inicio,
                           fecha_fin=fecha_fin,
                           periodo_str=periodo_str,
                           current_page=page,
                           total_pages=total_pages,
                           form_tramite=form_tramite,
                           delete_form=delete_form)

@papeleria_bp.route('/papeleria/<int:papeleria_id>/precios', methods=['GET', 'POST'])
@login_required
@check_papeleria_owner
def gestionar_precios_papeleria(papeleria_id):
    effective_user_id = get_effective_user_id()
    nombre_papeleria = papeleria_repository.get_name(papeleria_id, effective_user_id)

    if request.method == 'POST':
        # Usar el método bulk para actualizar precios en una sola transacción
        form_data = {k: v for k, v in request.form.items() if k != 'csrf_token'}
        _, errors = papeleria_repository.set_precios_bulk(papeleria_id, form_data, effective_user_id)

        bump_user_data_version(effective_user_id) # Invalidar caché
        if errors:
            for error in errors:
                flash(error, 'danger')
        else:
            flash('Precios actualizados con éxito.', 'success')

        # Para peticiones HTMX, renderizar contenido del formulario + flash messages
        if request.headers.get('HX-Request'):
            precios = papeleria_repository.get_precios_para_papeleria(papeleria_id, effective_user_id)
            form_html = render_template('partials/form_precios_content.html', precios=precios, papeleria_id=papeleria_id)
            flash_html = render_template('flash_messages.html')
            
            # Retornar formulario actualizado + flash messages con OOB swap
            response = make_response(
                form_html + 
                f'<div id="flash-container" hx-swap-oob="innerHTML">{flash_html}</div>'
            )
            return response
        
        # Para peticiones normales, redirigir
        return redirect(url_for('papeleria.gestionar_precios_papeleria', papeleria_id=papeleria_id))

    # Para GET request
    precios = papeleria_repository.get_precios_para_papeleria(papeleria_id, effective_user_id)
    return render_template('gestionar_precios.html', nombre_papeleria=nombre_papeleria, papeleria_id=papeleria_id, precios=precios)

@papeleria_bp.route('/agregar-papeleria', methods=['POST'])
@login_required
def agregar_papeleria():
    import logging
    logging.info(f"[DEBUG] request.form: {dict(request.form)}")
    from wtforms import Form
    form_papeleria = PapeleriaForm(formdata=request.form)
    if form_papeleria.validate_on_submit():
        nombre = form_papeleria.nombre.data
        user_id = get_effective_user_id()

        # La lógica de validación (reactivar o lanzar error) está ahora centralizada en el repositorio.
        try:
            # papeleria_repository.add se encargará de crear una nueva o reactivar una inactiva.
            # Si ya existe una activa con el mismo nombre, lanzará un ValueError.
            new_papeleria = papeleria_repository.add(nombre, user_id)
            bump_user_data_version(user_id) # Invalidar caché
            flash('Papelería agregada o reactivada con éxito.', 'success')
            
            # Crear un nuevo formulario limpio
            new_form = PapeleriaForm()
            form_html = render_template('form_agregar_papeleria.html', form_papeleria=new_form)
            
            # Renderizar mensajes flash
            flash_html = render_template('flash_messages.html')
            
            # Respuesta incluye: formulario limpio + flash messages + eventos
            response = make_response(
                form_html + 
                f'<div id="flash-container" hx-swap-oob="innerHTML">{flash_html}</div>'
            )
            
            # Disparar eventos para recargar lista de papelerías, dashboard y cerrar modal
            response.headers['HX-Trigger'] = json.dumps({
                'reload-dashboard': '',
                'refresh-papeleria-list': '',
                'closeModal': 'addPapeleriaModal'
            })
            return response
        except ValueError as e: # Capturamos el error si la papelería ya existe y está activa.
            form_papeleria.nombre.errors.append(str(e))
            # Devolvemos el formulario con el error para que HTMX lo muestre en la UI.
            form_html = render_template('form_agregar_papeleria.html', form_papeleria=form_papeleria)
            return form_html, 422
    
    # Si la validación inicial falla (p. ej. campo vacío), también devolvemos el formulario.
    form_html = render_template('form_agregar_papeleria.html', form_papeleria=form_papeleria)
    return form_html, 422

@papeleria_bp.route('/get-tramite-form', methods=['GET'])
@login_required
def get_tramite_form():
    """Devuelve el formulario de trámites actualizado (para HTMX cuando se agrega una papelería)."""
    effective_user_id = get_effective_user_id()
    papelerias = papeleria_repository.get_all(effective_user_id)
    form_tramite = TramiteForm()
    form_tramite.papeleria_id.choices = [(p.id, p.nombre) for p in papelerias]
    return render_template('form_registrar_tramite.html', form_tramite=form_tramite)

@papeleria_bp.route('/registrar-tramite', methods=['POST'])
@login_required
def registrar_tramite():
    try:
        form = TramiteForm(data=request.form)
        effective_user_id = get_effective_user_id()
        papelerias_data = papeleria_repository.get_papelerias_and_totals_for_user(effective_user_id)
        form.papeleria_id.choices = [(p.id, p.nombre) for p in papelerias_data['papelerias']]

        # Forzar error controlado para pruebas si el nombre del trámite es 'FORZAR_ERROR'
        if (form.tramite.data == 'OTRO' and form.tramite_manual.data and form.tramite_manual.data.strip().upper() == 'FORZAR_ERROR'):
            raise Exception('Error controlado de prueba: canal de mensajes funciona correctamente.')

        if form.validate_on_submit():
            papeleria_id = form.papeleria_id.data
            if form.tramite.data == 'OTRO':
                tramite_nombre = form.tramite_manual.data.strip().upper()
            else:
                tramite_nombre = form.tramite.data

            precio_input = form.precio.data
            precio = None
            if isinstance(precio_input, (int, float)):
                precio = precio_input
            if precio is None:
                precio_especifico = papeleria_repository.get_default_precio(papeleria_id, tramite_nombre, effective_user_id)
                if precio_especifico is not None:
                    precio = precio_especifico
                else:
                    form.precio.errors.append(f"No hay precio predefinido para '{tramite_nombre}'. Debes ingresarlo manualmente o configurarlo.")
                    if request.headers.get('HX-Request'):
                        return render_template('partials/form_registrar_tramite_content.html', form_tramite=form)
                    return render_template('partials/form_registrar_tramite_content.html', form_tramite=form)

            costo = form.costo.data
            if costo == 0:
                costo_default = tramite_repository.get_costo_for_tramite(tramite_nombre, effective_user_id)
                if costo_default is not None:
                    costo = costo_default

            cantidad = form.cantidad.data
            fecha = form.fecha.data.strftime('%Y-%m-%d')

            tramite_repository.add_bulk(papeleria_id, tramite_nombre, effective_user_id, fecha, precio, costo, cantidad)
            bump_user_data_version(effective_user_id) # Invalidar caché
            
            # Log de la operación de registro de trámite
            log_db_operation('CREATE', 'tramite', None, {
                'papeleria_id': papeleria_id,
                'tramite': tramite_nombre,
                'cantidad': cantidad,
                'precio': precio,
                'costo': costo,
                'fecha': fecha
            })
            log_action('tramite_registered', {
                'papeleria_id': papeleria_id,
                'tramite': tramite_nombre,
                'cantidad': cantidad,
                'ganancia_total': (precio - costo) * cantidad
            })
            
            flash(f"{cantidad} trámite(s) de '{tramite_nombre}' registrados correctamente.", 'success')

            # Si la petición es HTMX, devolver el mensaje flash OOB y el formulario limpio
            if request.headers.get('HX-Request'):
                flash_html = render_template('flash_messages.html')
                # Renderizar un formulario limpio pero manteniendo la papelería seleccionada
                new_form = TramiteForm()
                papelerias_data = papeleria_repository.get_papelerias_and_totals_for_user(effective_user_id)
                new_form.papeleria_id.choices = [(p.id, p.nombre) for p in papelerias_data['papelerias']]
                new_form.papeleria_id.data = papeleria_id # Mantener selección para agilizar captura
                form_html = render_template('partials/form_registrar_tramite_content.html', form_tramite=new_form, registro_exitoso=True)
                # OOB swap para actualizar el contenedor de mensajes flash y el formulario
                response = make_response(f'<div id="flash-container" hx-swap-oob="innerHTML">{flash_html}</div>{form_html}')
                # Añadir señal explícita de éxito para el frontend
                response.headers['HX-Trigger'] = json.dumps({
                    'reload-dashboard': '',
                    'refresh-papeleria-list': '',
                    'tramiteRegistrado': {'cantidad': cantidad, 'tramite': tramite_nombre}
                })
                return response
            # Si no es HTMX, redirect tradicional
            return redirect(url_for('papeleria.ver_papeleria', papeleria_id=papeleria_id))

        # Si la validación falla, renderizar el formulario con errores
        if request.headers.get('HX-Request'):
            return render_template('partials/form_registrar_tramite_content.html', form_tramite=form)
        return render_template('partials/form_registrar_tramite_content.html', form_tramite=form)
    except Exception as e:
        logging.error(f"Error inesperado en registrar_tramite: {e}", exc_info=True)
        flash(f"Error interno: {str(e)}", "danger")
        # Si es HTMX, devolver el formulario con el error y mensaje flash
        if request.headers.get('HX-Request'):
            flash_html = render_template('flash_messages.html')
            form_html = render_template('partials/form_registrar_tramite_content.html', form_tramite=form if 'form' in locals() else None)
            return make_response(f'<div id="flash-container" hx-swap-oob="innerHTML">{flash_html}</div>{form_html}')
        # Si no es HTMX, renderizar el formulario con el error
        return render_template('partials/form_registrar_tramite_content.html', form_tramite=form if 'form' in locals() else None)

@papeleria_bp.route('/_tramite_form_papelerias')
@login_required
def get_tramite_form_papelerias_partial():
    """Endpoint HTMX para refrescar las opciones de papelería en el formulario de trámite."""
    papelerias_data = papeleria_repository.get_papelerias_and_totals_for_user(get_effective_user_id())
    papelerias = papelerias_data['papelerias']
    return render_template('partials/papeleria_select_options.html', papelerias=papelerias)

@papeleria_bp.route('/editar-tramite/<int:tramite_id>', methods=['GET', 'POST'])
@login_required
def editar_tramite(tramite_id):
    effective_user_id = get_effective_user_id()
    tramite = tramite_repository.get_by_id(tramite_id, effective_user_id)

    if not tramite:
        flash('Trámite no encontrado.', 'error')
        return redirect(url_for('main.index'))

    form = EditarTramiteForm(obj=tramite)
    
    if tramite.tramite not in TRAMITES_PREDEFINIDOS:
        form.tramite.data = 'OTRO'
        form.tramite_manual.data = tramite.tramite

    if request.method == 'GET':
        form.fecha.data = tramite.fecha
        # Si es una petición HTMX, devolvemos solo el contenido del formulario
        if request.headers.get('HX-Request'):
            return render_template('partials/editar_tramite_content.html', form=form, tramite=tramite)

    if form.validate_on_submit():
        if form.tramite.data == 'OTRO':
            tipo_tramite = form.tramite_manual.data.strip().upper()
        else:
            tipo_tramite = form.tramite.data

        fecha = form.fecha.data.strftime('%Y-%m-%d')
        precio = form.precio.data
        costo = form.costo.data

        tramite_repository.update(tramite_id, effective_user_id, fecha, tipo_tramite, precio, costo)
        bump_user_data_version(effective_user_id) # Invalidar caché
        flash('Trámite actualizado con éxito.', 'success')

        # Si es una petición HTMX, disparar evento para recargar
        if request.headers.get('HX-Request'):
            flash_html = render_template('flash_messages.html')
            response = make_response(f'<div id="flash-container" hx-swap-oob="innerHTML">{flash_html}</div>')
            # Disparar evento para recargar dashboard con datos actualizados
            response.headers['HX-Trigger'] = json.dumps({'reload-dashboard': ''})
            # Redirigir a la página de la papelería
            response.headers['HX-Redirect'] = url_for('papeleria.ver_papeleria', papeleria_id=tramite.papeleria_id)
            return response

        return redirect(url_for('papeleria.ver_papeleria', papeleria_id=tramite.papeleria_id))
    
    # Si la validación falla y es HTMX, devolvemos solo el parcial con 422
    if request.method == 'POST' and request.headers.get('HX-Request'):
        return render_template('partials/editar_tramite_content.html', form=form, tramite=tramite), 422

    return render_template('editar_tramite.html', form=form, tramite=tramite)

@papeleria_bp.route('/eliminar-tramite/<int:tramite_id>', methods=['POST'])
@login_required
def eliminar_tramite(tramite_id):
    form = DeleteForm(request.form)
    papeleria_id = None  # Inicializar fuera del scope del if
    
    if form.validate_on_submit():
        effective_user_id = get_effective_user_id()
        papeleria_id = tramite_repository.delete(tramite_id, effective_user_id)
        if papeleria_id is not None:
            bump_user_data_version(effective_user_id) # Invalidar caché
            flash('Trámite eliminado correctamente.', 'success')
        else:
            flash('No se pudo eliminar el trámite (no encontrado o sin permisos).', 'error')
    else:
        flash('Error de seguridad al intentar eliminar el trámite. Por favor, recarga la página e inténtalo de nuevo.', 'danger')

    # Renderizar flash messages y redirigir
    if request.headers.get('HX-Request'):
        # Usar HX-Redirect para forzar la recarga de la página después de eliminar
        # Esto garantiza que la tabla se actualice correctamente
        if papeleria_id:
            redirect_url = url_for('papeleria.ver_papeleria', papeleria_id=papeleria_id)
        else:
            redirect_url = url_for('main.index')
        
        response = make_response('')
        response.headers['HX-Redirect'] = redirect_url
        return response
    
    # Fallback para peticiones no-HTMX
    if papeleria_id:
        return redirect(url_for('papeleria.ver_papeleria', papeleria_id=papeleria_id))
    return redirect(url_for('main.index'))

@papeleria_bp.route('/editar-papeleria/<int:papeleria_id>', methods=['GET', 'POST'])
@login_required
@check_papeleria_owner
def editar_papeleria(papeleria_id):
    effective_user_id = get_effective_user_id()
    papeleria_actual = papeleria_repository.get_name(papeleria_id, effective_user_id)
    delete_form = DeleteForm()

    form = EditarPapeleriaForm()
    if request.method == 'GET':
        form.nombre.data = papeleria_actual
        if request.headers.get('HX-Request'):
            return render_template('partials/editar_papeleria_content.html', form=form, papeleria_id=papeleria_id, nombre_actual=papeleria_actual, delete_form=delete_form)

    if form.validate_on_submit():
        nuevo_nombre = form.nombre.data
        if papeleria_repository.exists_with_name(nuevo_nombre, effective_user_id, papeleria_id_to_exclude=papeleria_id):
            form.nombre.errors.append('Ya tienes una papelería con ese nombre.')
            return render_template('editar_papeleria.html', form=form, papeleria_id=papeleria_id, nombre_actual=papeleria_actual, delete_form=delete_form)

        papeleria_repository.update_name(papeleria_id, nuevo_nombre, effective_user_id)
        bump_user_data_version(effective_user_id) # Invalidar caché
        flash(f'Nombre de papelería actualizado a "{nuevo_nombre}" con éxito.', 'success')

        # Si es una petición HTMX, disparar evento para recargar dashboard
        if request.headers.get('HX-Request'):
            flash_html = render_template('flash_messages.html')
            response = make_response(f'<div id="flash-container" hx-swap-oob="innerHTML">{flash_html}</div>')
            # Disparar evento para recargar dashboard, lista de papelerías y redirigir
            response.headers['HX-Trigger'] = json.dumps({'reload-dashboard': '', 'refresh-papeleria-list': ''})
            response.headers['HX-Redirect'] = url_for('main.index')
            return response

        return redirect(url_for('main.index'))
    
    if request.method == 'POST' and request.headers.get('HX-Request'):
        return render_template('partials/editar_papeleria_content.html', form=form, papeleria_id=papeleria_id, nombre_actual=papeleria_actual, delete_form=delete_form), 200

    return render_template('editar_papeleria.html', form=form, papeleria_id=papeleria_id, nombre_actual=papeleria_actual, delete_form=delete_form)

@papeleria_bp.route('/eliminar-papeleria/<int:papeleria_id>', methods=['POST'])
@login_required
@admin_required
def eliminar_papeleria(papeleria_id):
    effective_user_id = get_effective_user_id()
    form = DeleteForm()
    
    if form.validate_on_submit():
        nombre_papeleria = papeleria_repository.get_name(papeleria_id, effective_user_id)
        papeleria_repository.delete(papeleria_id, effective_user_id)
        bump_user_data_version(effective_user_id) # Invalidar caché
        flash(f'La papelería "{nombre_papeleria}" y todos sus datos han sido eliminados con éxito.', 'success')
    else:
        flash('Error de validación al intentar eliminar la papeleria.', 'danger')
    
    if request.headers.get('HX-Request'):
        # Renderizar mensajes flash y disparar eventos para recargar dashboard
        flash_html = render_template('flash_messages.html')
        response = make_response(f'<div id="flash-container" hx-swap-oob="innerHTML">{flash_html}</div>')
        # Trigger eventos para recargar dashboard, lista y redirigir al index
        response.headers['HX-Trigger'] = json.dumps({
            'reload-dashboard': '',  # Recarga el dashboard con gráficos
            'refresh-papeleria-list': '',  # Recarga la lista de papelerías
            'papeleria-deleted': ''  # Evento custom por si se necesita en el futuro
        })
        # Después de recargar, navegar al index
        response.headers['HX-Redirect'] = url_for('main.index')
        return response
    
    return redirect(url_for('main.index'))

@papeleria_bp.route('/descargar-pdf/<int:papeleria_id>')
@login_required
@check_papeleria_owner
def descargar_pdf(papeleria_id):
    from ..pdf_generator import REPORTLAB_AVAILABLE
    
    logging.info(f"Downloading PDF for papeleria with id: {papeleria_id} by user: {current_user.id}")
    
    # Verificar si reportlab está disponible
    if not REPORTLAB_AVAILABLE:
        flash('La generación de PDFs no está disponible en este servidor. Por favor, usa la opción de exportar a CSV.', 'warning')
        return redirect(url_for('papeleria.ver_papeleria', papeleria_id=papeleria_id))
    
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    effective_user_id = get_effective_user_id()

    datos, _, _ = tramite_repository.get_details_for_papeleria(papeleria_id, effective_user_id, fecha_inicio, fecha_fin, page=1, per_page=1)
    if not datos:
        flash('No hay trámites para generar un PDF con los filtros seleccionados.', 'warning')
        return redirect(url_for('papeleria.ver_papeleria', papeleria_id=papeleria_id, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin))
    
    try:
        is_admin_view = current_user.role == 'admin'
        logo_filename = f"logo_{effective_user_id}.png"
        logo_path = os.path.join(current_app.config['UPLOAD_FOLDER'], logo_filename)
        if not os.path.exists(logo_path):
            logo_path = None
        ruta_pdf = generar_pdf_papeleria(papeleria_repository, tramite_repository, papeleria_id, effective_user_id, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, is_admin_view=is_admin_view, logo_path=logo_path)
        if ruta_pdf and os.path.exists(ruta_pdf):
            return send_file(ruta_pdf, as_attachment=True)
        else:
            flash('No se pudo generar o encontrar el archivo PDF.', 'error')
            return redirect(url_for('papeleria.ver_papeleria', papeleria_id=papeleria_id))
    except Exception as e:
        flash(f'Ocurrió un error al generar el PDF: {e}', 'error')
        return redirect(url_for('papeleria.ver_papeleria', papeleria_id=papeleria_id))

@papeleria_bp.route('/exportar-csv/papeleria/<int:papeleria_id>')
@login_required
@admin_required
@check_papeleria_owner
def exportar_csv_papeleria(papeleria_id):
    effective_user_id = get_effective_user_id()
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    
    tramites, _, _ = tramite_repository.get_details_for_papeleria(
        papeleria_id, effective_user_id, fecha_inicio, fecha_fin, page=1, per_page=99999
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Trámite', 'Fecha', 'Precio', 'Costo', 'Ganancia'])
    for tramite in tramites:
        ganancia = tramite.precio - tramite.costo
        writer.writerow([tramite.tramite, tramite.fecha.strftime('%Y-%m-%d'), tramite.precio, tramite.costo, ganancia])
    
    output.seek(0)
    return send_file(io.BytesIO(output.read().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name=f"reporte_papeleria_{papeleria_id}_{datetime.now().strftime('%Y-%m-%d')}.csv")
