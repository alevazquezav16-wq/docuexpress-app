# constants.py

"""
Módulo para almacenar constantes utilizadas en toda la aplicación DocuExpress.
Esto ayuda a evitar dependencias circulares y mantiene el código organizado.
"""

TRAMITES_PREDEFINIDOS = [
    'ACTA DE NACIMIENTO',
    'ACTA DE MATRIMONIO',
    'ACTA DE DEFUNCIÓN',
    'ACTA DIVORCIO',
    'CITA SAT (CUALQUIER ESTADO)',
    'INSCRIPCIÓN SAT',
    'EFIRMA SAT',
    'RENOVACIÓN SAT',
    'CONSTANCIA SITUACIÓN FISCAL (FÍSICA Y MORAL)',
    'EMISIÓN CUAUHTHEMOC CDMX',
    'EMISIÓN DE REGRISTO',
    'COMUNICADO RFC',
    'OPINIÓN CUMPLIMIENTO 32D',
    'NÚMERO SEGURO SOCIAL',
    'VIGENCIA IMSS',
    'SEMANAS COTIZADAS',
    'CONSTANCIA DE NO AFILIACIÓN ISSTE',
    'ESTADO DE CUENTA INFONAVIT',
    'CARTA RETENCIÓN INFONAVIT',
    'CARTA SUSPENSIÓN INFONAVIT',
    'REPORTE DE BURÓ DE CRÉDITO',
    'CITA SCT (CUALQUIER ESTADO)',
    'CITA PASAPORTE (CUALQUIER ESTADO)',
    'RECIBO DE LUZ CFE',
    'CORRECCIÓN DE CURP',
    'UNIFICACIÓN DE CURP',
    'NETFLIX',
    'HBO MAX',
    'DISNEY',
    'AMAZON PRIME',
    'BLIM',
    'CANVA',
    'YOUTUBE PREMIUM',
    'STAR',
    'VIX'
]

CATEGORIAS_GASTOS = [
    ('SERVICIOS', 'Servicios (Luz, Agua, Internet)'),
    ('RENTA', 'Renta de Local'),
    ('PAPELERIA', 'Papelería y Oficina'),
    ('SUELDOS', 'Sueldos y Salarios'),
    ('MARKETING', 'Marketing y Publicidad'),
    ('IMPUESTOS', 'Impuestos'),
    ('MANTENIMIENTO', 'Mantenimiento y Reparaciones'),
    ('OTROS', 'Otros Gastos')
]