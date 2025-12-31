from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, session
from flask_login import login_required
from datetime import datetime
import io
import csv
import logging

from ..forms import PapeleriaForm, TramiteForm, DismissNotificationForm
from ..utils import get_effective_user_id, admin_required
from ..database import papeleria_repository, tramite_repository, gasto_repository, analytics_repository
from ..constants import TRAMITES_PREDEFINIDOS

main_bp = Blueprint('main', __name__)

def _get_dashboard_context(search_term=None):
    """Función auxiliar que obtiene y devuelve todo el contexto para el dashboard."""
    effective_user_id = get_effective_user_id()
    
    # Esta función ahora devuelve tanto las papelerías como los totales.
    dashboard_data = papeleria_repository.get_papelerias_and_totals_for_user(effective_user_id, search_term)
    papelerias = dashboard_data['papelerias']
    totales = dashboard_data['totales']
    
    # Obtener comparativas
    totales_comparativa = papeleria_repository.get_totales_comparativa(effective_user_id)
    tramites_comparativa = tramite_repository.get_tramites_comparativa(effective_user_id)
    
    # Obtener analytics avanzados
    meta_progress = analytics_repository.get_meta_mensual_progress(effective_user_id)
    mejor_mes = analytics_repository.get_mejor_mes_historico(effective_user_id)
    dia_productivo = analytics_repository.get_dias_mas_productivos(effective_user_id)
    margen_promedio = analytics_repository.get_margen_promedio(effective_user_id)
    rentabilidad_tramites = analytics_repository.get_rentabilidad_por_tramite(effective_user_id)
    
    tramites_hoy = tramites_comparativa['hoy']
    total_gastos = gasto_repository.get_total_gastos(effective_user_id)

    context = {
        'papelerias': papelerias,
        'totales': totales,
        'totales_comparativa': totales_comparativa,
        'tramites_de_hoy': tramites_hoy,
        'tramites_comparativa': tramites_comparativa,
        'meta_progress': meta_progress,
        'mejor_mes': mejor_mes,
        'dia_productivo': dia_productivo,
        'margen_promedio': margen_promedio,
        'rentabilidad_tramites': rentabilidad_tramites[:5],  # Top 5
        'num_papelerias': len(papelerias),
        'total_gastos_operativos': total_gastos,
        'search_term': search_term,
        'tramites_predefinidos': TRAMITES_PREDEFINIDOS
    }
    return context

@main_bp.route('/test-chart')
def test_chart():
    """Página de prueba para verificar Chart.js"""
    return render_template('test_chart_simple.html')

@main_bp.route('/test-papeleria-chart')
def test_papeleria_chart():
    """Página de prueba para el gráfico de papelería"""
    return render_template('test_papeleria_chart.html')

@main_bp.route('/')
@login_required
def index():
    """
    Página principal que muestra el dashboard.
    Optimizada con HTMX para devolver solo el fragmento del dashboard si es necesario.
    """
    search_term = request.args.get('q')
    context = _get_dashboard_context(search_term)
    form_papeleria = PapeleriaForm()
    form_tramite = TramiteForm()
    form_tramite.papeleria_id.choices = [(p.id, p.nombre) for p in context['papelerias']]
 
    if request.headers.get('HX-Request'):
        # Si la petición viene del contenedor del dashboard, devolvemos solo el contenido del dashboard
        if request.headers.get('HX-Target') == 'dashboard-container':
            return render_template('dashboard_content.html', **context)
        
        return render_template('partials/lista_papelerias.html', **context)

    final_context = {**context, 'form_papeleria': form_papeleria, 'form_tramite': form_tramite}

    return render_template('index.html', **final_context)

@main_bp.route('/_papeleria_list_partial')
@login_required
def get_papeleria_list_partial():
    """Endpoint HTMX para obtener solo el fragmento de la lista de papelerías."""
    search_term = request.args.get('q')
    context = _get_dashboard_context(search_term)
    return render_template('lista_papelerias.html', **context)

@main_bp.route('/exportar-csv/general')
@login_required
@admin_required
def exportar_csv_general():
    """Exporta todos los trámites del usuario a un archivo CSV."""
    effective_user_id = get_effective_user_id()
    data = tramite_repository.export_all_as_csv(effective_user_id)
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Papelería', 'Trámite', 'Fecha', 'Precio', 'Costo', 'Ganancia'])
    for row in data:
        writer.writerow([row.papeleria, row.tramite, row.fecha.strftime('%Y-%m-%d'), row.precio, row.costo, row.ganancia])

    output.seek(0)
    
    return send_file(
        io.BytesIO(output.read().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f"reporte_general_{datetime.now().strftime('%Y-%m-%d')}.csv"
    )

@main_bp.route('/dismiss-notification', methods=['POST'])
@login_required
def dismiss_notification():
    """Descarta una notificación para la sesión actual."""
    form = DismissNotificationForm()
    if form.validate_on_submit():
        notification_text = request.form.get('text')
        if 'dismissed_notifications' not in session:
            session['dismissed_notifications'] = []
        session['dismissed_notifications'].append(notification_text)
        session.modified = True
        return '', 204
    else:
        flash('Error de validación al descartar la notificación.', 'danger')
        return '', 400
