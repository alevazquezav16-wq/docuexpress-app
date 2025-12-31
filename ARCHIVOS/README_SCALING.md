# Guía de Escalabilidad DocuExpress

## 1. Flask-Limiter con Redis
- Instala Redis en tu servidor o usa un servicio externo.
- Configura `.env` con:
  RATELIMIT_STORAGE_URL=redis://localhost:6379
  RATELIMIT_DEFAULT=1000 per day;200 per hour
  RATELIMIT_API=500 per day;100 per hour

## 2. Caché multicapa
- Instala Flask-Caching y Redis.
- Configura `.env`:
  CACHE_TYPE=RedisCache
  CACHE_REDIS_URL=redis://localhost:6379/0
  CACHE_DEFAULT_TIMEOUT=300
- Usa `app.cache` para cachear resultados de consultas frecuentes.

## 3. Backups y monitoreo
- Mantén backups automáticos (ya implementado).
- Revisa logs y espacio en disco regularmente.

## 4. Circuit breaker y retry
- Solo necesario si usas APIs externas o microservicios.
- Recomendado: librerías como `pybreaker` y `tenacity`.

## 5. Ejemplo de uso de caché en endpoint
```python
@app.route('/api/dashboard-charts')
@cache.cached(timeout=300)
def dashboard_charts():
    # ...tu lógica...
    return jsonify(...)
```

## 6. Comandos útiles
- Instalar Redis: `sudo apt install redis-server`
- Iniciar Redis: `sudo service redis-server start`
- Ver logs: `tail -f /tmp/docuexpress_run.log`

## 7. Monitoreo de Redis y disco
- Ver uso de memoria Redis: `redis-cli info memory`
- Ver espacio en disco: `df -h`
- Ver logs de la app: `tail -f docuexpress.log`

## 8. Pruebas de carga
- Instala locust: `pip install locust`
- Ejemplo de uso: `locust -f locustfile.py` (ver documentación)
- Alternativa simple: `ab -n 1000 -c 50 http://localhost:8083/`

## 9. Configuración de alertas por email
- Agrega en tu `.env`:
  ERROR_EMAIL_ENABLED=True
  ERROR_EMAIL_TO=tu@email.com
  ERROR_EMAIL_FROM=alertas@email.com
  ERROR_EMAIL_HOST=smtp.tuservidor.com
  ERROR_EMAIL_PORT=587
  ERROR_EMAIL_USER=usuario
  ERROR_EMAIL_PASS=contraseña
- Se enviará un email ante errores 500 críticos.
