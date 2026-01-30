# pdf_generator.py
from pathlib import Path
from datetime import datetime, timedelta
import logging
import os

# reportlab es opcional (ahorra ~5MB en PythonAnywhere gratis)
REPORTLAB_AVAILABLE = False
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.units import mm
    REPORTLAB_AVAILABLE = True
except ImportError:
    # Placeholders para evitar errores
    A4 = (595.27, 841.89)
    mm = 2.83465
    colors = None

# Obtenemos la ruta del directorio donde se encuentra este script (ARCHIVOS/).
BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "reportes_pdf"

def _header_footer(canvas, doc, logo_path=None):
    """Función para dibujar el encabezado y pie de página en cada página del PDF."""
    canvas.saveState()
    styles = getSampleStyleSheet()
    
    # --- Encabezado ---
    header_content = []
    if logo_path and Path(logo_path).exists():
        try:
            img = Image(logo_path, width=20*mm, height=20*mm)
            img.hAlign = 'LEFT'
            title_text = Paragraph(f"<b>DOCUEXPRESS</b><br/><font size=10>Reporte de Trámites</font>", styles['Heading1'])
            header_table = Table([[img, title_text]], colWidths=[25*mm, 150*mm], rowHeights=[20*mm])
            header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
            header_content.append(header_table)
        except Exception as e:
            logging.warning(f"No se pudo cargar el logo '{logo_path}' para el PDF: {e}")
            pass
    
    if not header_content:
        header_content.append(Paragraph("<b>DOCUEXPRESS</b>", styles['Heading1']))

    for item in header_content:
        w, h = item.wrapOn(canvas, doc.width, doc.topMargin)
        item.drawOn(canvas, doc.leftMargin, doc.height + doc.topMargin - h)

    # --- Línea divisoria ---
    canvas.setStrokeColorRGB(0.8, 0.8, 0.8)
    canvas.line(doc.leftMargin, doc.height + doc.topMargin - 25*mm, doc.width + doc.leftMargin, doc.height + doc.topMargin - 25*mm)

    # --- Pie de página ---
    footer_text = f"Página {doc.page}"
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.grey)
    canvas.drawRightString(doc.width + doc.leftMargin, 10 * mm, footer_text)
    canvas.restoreState()

def generar_pdf_papeleria(papeleria_repository, tramite_repository, papeleria_id, user_id, fecha_inicio=None, fecha_fin=None, carpeta=REPORTS_DIR, logo_path=None, is_admin_view=False):
    """Genera un PDF con el reporte de trámites. Retorna None si reportlab no está instalado."""
    if not REPORTLAB_AVAILABLE:
        logging.warning("reportlab no instalado - PDFs no disponibles")
        return None
    
    pap_nombre = papeleria_repository.get_name(papeleria_id, user_id)
    if not pap_nombre:
        return None

    datos, _, _ = tramite_repository.get_details_for_papeleria(papeleria_id, user_id, fecha_inicio, fecha_fin, page=1, per_page=999999)
    
    if fecha_inicio and fecha_fin:
        inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d')
        fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d')
        periodo_str = f"{inicio_dt.strftime('%d/%m/%Y')} al {fin_dt.strftime('%d/%m/%Y')}"
        fecha_archivo_str = f"{fecha_inicio}_a_{fecha_fin}"
    else:
        periodo_str = "Histórico"
        fechas_tramites = [d.fecha for d in datos] if datos else []
        fecha_archivo_str = f"{min(fechas_tramites).strftime('%Y-%m-%d')}_a_{max(fechas_tramites).strftime('%Y-%m-%d')}" if fechas_tramites else "historico"

    total_ingresos = sum(r.precio for r in datos)
    num_tramites = len(datos)

    Path(carpeta).mkdir(parents=True, exist_ok=True)
    safe_papeleria_name = "".join(filter(str.isalnum, pap_nombre)).replace(" ", "_")
    nombre_archivo = f"reporte_{safe_papeleria_name}_{fecha_archivo_str}.pdf"
    ruta = Path(carpeta) / nombre_archivo
    
    doc = SimpleDocTemplate(str(ruta), pagesize=A4, rightMargin=20*mm, leftMargin=20*mm, topMargin=40*mm, bottomMargin=20*mm)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='RightAlign', alignment=2))
    elements = []

    resumen_data = [
        [Paragraph('<b>Papelería:</b>', styles['Normal']), pap_nombre],
        [Paragraph('<b>Periodo:</b>', styles['Normal']), periodo_str],
        [Paragraph('<b>Total Trámites:</b>', styles['Normal']), str(num_tramites)],
        [Paragraph('<b>Total Ingresos:</b>', styles['Normal']), Paragraph(f'<b>${total_ingresos:.2f}</b>', styles['RightAlign'])],
    ]

    col_widths = [40*mm, None]
    resumen_table = Table(resumen_data, colWidths=col_widths)
    resumen_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F7F9FC')),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#E0E6ED')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(resumen_table)
    elements.append(Spacer(1, 10*mm))

    if not datos:
        elements.append(Paragraph("No hay registros para esta papelería en el periodo indicado.", styles['BodyText']))
    else:
        data = [["Fecha", "Trámite", "Precio"]]
        col_widths = [30*mm, None, 30*mm]
        for r in datos:
            data.append([r.fecha.strftime('%Y-%m-%d'), Paragraph(r.tramite, styles['BodyText']), f"${r.precio:.2f}"])

        t = Table(data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2c3e50')), 
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('ALIGN', (1,1), (1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#ecf0f1')),
            ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#bdc3c7')),
            ('ALIGN', (2,1), (2,-1), 'RIGHT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,1), (-1,-1), 6),
            ('BOTTOMPADDING', (0,1), (-1,-1), 6),
        ]))
        for i, row in enumerate(datos):
            if i % 2 == 0:
                t.setStyle(TableStyle([('BACKGROUND', (0, i+1), (-1, i+1), colors.white)]))
        elements.append(t)
    on_first = lambda canvas, doc: _header_footer(canvas, doc, logo_path=logo_path)
    on_later = lambda canvas, doc: _header_footer(canvas, doc, logo_path=logo_path)
    doc.build(elements, onFirstPage=on_first, onLaterPages=on_later)
    return ruta
