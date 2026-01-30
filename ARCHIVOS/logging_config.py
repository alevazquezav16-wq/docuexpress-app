"""
Configuración centralizada de logging para DocuExpress.
Proporciona funciones auxiliares para logging estructurado con contexto.
"""
import logging
import functools
import time
from datetime import datetime
from flask import request, g
from flask_login import current_user

# Configurar formato de logs estructurado
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(module)s:%(funcName)s:%(lineno)d | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def setup_logging(app):
    """Configura el logging de la aplicación."""
    # Configurar nivel según el entorno
    log_level = logging.DEBUG if app.config.get('DEBUG') else logging.INFO
    
    # Configurar el logger raíz
    logging.basicConfig(
        level=log_level,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT
    )
    
    # Silenciar logs excesivos de librerías
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('apscheduler').setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)


def get_request_context():
    """Obtiene contexto de la petición actual para logging."""
    context = {
        'timestamp': datetime.now().isoformat(),
        'user_id': None,
        'username': None,
        'ip': None,
        'endpoint': None,
        'method': None
    }
    
    try:
        if request:
            context['ip'] = request.remote_addr or request.headers.get('X-Forwarded-For', 'unknown')
            context['endpoint'] = request.endpoint
            context['method'] = request.method
            context['path'] = request.path
        
        if current_user and current_user.is_authenticated:
            context['user_id'] = current_user.id
            context['username'] = getattr(current_user, 'username', 'unknown')
    except RuntimeError:
        # Fuera del contexto de request
        pass
    
    return context


def log_action(action: str, details: dict = None, level: str = 'info'):
    """
    Registra una acción del usuario con contexto completo.
    
    Args:
        action: Descripción de la acción (ej: "login_success", "tramite_created")
        details: Diccionario con detalles adicionales
        level: Nivel de log ('debug', 'info', 'warning', 'error', 'critical')
    """
    ctx = get_request_context()
    
    # Construir mensaje estructurado
    msg_parts = [
        f"[ACTION: {action}]",
        f"user={ctx['username'] or 'anonymous'}({ctx['user_id'] or 'N/A'})",
        f"ip={ctx['ip']}",
        f"endpoint={ctx['endpoint']}"
    ]
    
    if details:
        details_str = " ".join([f"{k}={v}" for k, v in details.items()])
        msg_parts.append(f"| {details_str}")
    
    message = " ".join(msg_parts)
    
    # Obtener función de logging según nivel
    log_func = getattr(logging, level.lower(), logging.info)
    log_func(message)


def log_security_event(event_type: str, success: bool, details: dict = None):
    """
    Registra eventos de seguridad (login, logout, cambio de password, etc.)
    
    Args:
        event_type: Tipo de evento ('login', 'logout', 'password_change', 'impersonation')
        success: Si el evento fue exitoso o no
        details: Detalles adicionales
    """
    ctx = get_request_context()
    
    status = "SUCCESS" if success else "FAILED"
    level = 'info' if success else 'warning'
    
    msg = f"[SECURITY:{event_type.upper()}] status={status} user={ctx['username']}({ctx['user_id']}) ip={ctx['ip']}"
    
    if details:
        details_str = " ".join([f"{k}={v}" for k, v in details.items()])
        msg += f" | {details_str}"
    
    log_func = getattr(logging, level.lower(), logging.info)
    log_func(msg)


def log_db_operation(operation: str, table: str, record_id=None, details: dict = None):
    """
    Registra operaciones de base de datos.
    
    Args:
        operation: Tipo de operación ('CREATE', 'READ', 'UPDATE', 'DELETE')
        table: Nombre de la tabla
        record_id: ID del registro afectado
        details: Detalles adicionales
    """
    ctx = get_request_context()
    
    msg = f"[DB:{operation}] table={table} id={record_id} user={ctx['username']}({ctx['user_id']})"
    
    if details:
        details_str = " ".join([f"{k}={v}" for k, v in details.items()])
        msg += f" | {details_str}"
    
    logging.debug(msg)


def log_error(error: Exception, context: str = None, critical: bool = False):
    """
    Registra errores con contexto completo.
    
    Args:
        error: La excepción capturada
        context: Contexto adicional sobre dónde ocurrió el error
        critical: Si es un error crítico que requiere atención inmediata
    """
    ctx = get_request_context()
    
    level = 'critical' if critical else 'error'
    
    msg = f"[ERROR] context={context or 'unknown'} type={type(error).__name__} message={str(error)}"
    msg += f" | user={ctx['username']}({ctx['user_id']}) ip={ctx['ip']} endpoint={ctx['endpoint']}"
    
    log_func = getattr(logging, level.lower(), logging.error)
    log_func(msg, exc_info=True)


def timed_operation(operation_name: str = None):
    """
    Decorador para medir y registrar el tiempo de ejecución de funciones.
    
    Args:
        operation_name: Nombre descriptivo de la operación (opcional)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation_name or func.__name__
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                elapsed = (time.time() - start_time) * 1000  # milisegundos
                
                # Log con nivel según duración
                if elapsed > 5000:  # > 5 segundos
                    logging.warning(f"[SLOW_OPERATION] {op_name} completed in {elapsed:.2f}ms (>5s threshold)")
                elif elapsed > 1000:  # > 1 segundo
                    logging.info(f"[OPERATION] {op_name} completed in {elapsed:.2f}ms")
                else:
                    logging.debug(f"[OPERATION] {op_name} completed in {elapsed:.2f}ms")
                
                return result
                
            except Exception as e:
                elapsed = (time.time() - start_time) * 1000
                logging.error(f"[OPERATION_FAILED] {op_name} failed after {elapsed:.2f}ms: {e}")
                raise
        
        return wrapper
    return decorator


def log_request_start():
    """Registra el inicio de una petición HTTP."""
    ctx = get_request_context()
    g.request_start_time = time.time()
    logging.debug(f"[REQUEST_START] {ctx['method']} {ctx.get('path', '/')} user={ctx['username']}({ctx['user_id']})")


def log_request_end(response):
    """Registra el fin de una petición HTTP."""
    if hasattr(g, 'request_start_time'):
        elapsed = (time.time() - g.request_start_time) * 1000
        ctx = get_request_context()
        
        if elapsed > 2000:  # > 2 segundos
            logging.warning(f"[SLOW_REQUEST] {ctx['method']} {ctx.get('path', '/')} {response.status_code} {elapsed:.2f}ms")
        else:
            logging.debug(f"[REQUEST_END] {ctx['method']} {ctx.get('path', '/')} {response.status_code} {elapsed:.2f}ms")
    
    return response
