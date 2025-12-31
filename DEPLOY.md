DocuExpress — Guía de despliegue profesional

Resumen
- Este repositorio contiene la aplicación Flask en `ARCHIVOS/`.
- El punto WSGI es `wsgi.py` en la raíz y expone la variable `application`.

Preparación (entorno remoto: PythonAnywhere o servidor Linux)
1. Crear y activar virtualenv (ejemplo):

```bash
python3 -m venv ~/.venvs/docuexpress
source ~/.venvs/docuexpress/bin/activate
pip install -U pip
pip install -r ARCHIVOS/requirements.txt
```

2. Variables de entorno importantes (exportar o configurar en el panel del host):
- `FLASK_SECRET_KEY` — secreto de la app
- `RATELIMIT_ENABLED` — 'True' o 'False'
- `RATELIMIT_STORAGE_URL` — e.g. `redis://<host>:6379` o `memory://` para no usar Redis
- `DATABASE_PATH` — opcional si quieres usar una ubicación personalizada
- `ERROR_EMAIL_*` — si usas alertas por email

3. Archivo WSGI (PythonAnywhere)
- En PythonAnywhere, el archivo WSGI debe importar la aplicación desde `wsgi.py` en la raíz del proyecto.
- `wsgi.py` ya disponible y exporta `application = app`. Asegúrate de que la ruta del proyecto esté en `PYTHONPATH`.

Ejemplo de encabezado de WSGI (no es necesario si ya usas `wsgi.py`):
```python
import sys
path = '/home/<user>/<project_root>'
if path not in sys.path:
    sys.path.insert(0, path)
from wsgi import application
```

4. Recomendaciones específicas para PythonAnywhere
- Sube el código (git push / upload). En la configuración Web app, edita: 
  - Working directory: `/home/<user>/<project_root>`
  - Virtualenv: `/home/<user>/.virtualenvs/<env>` (si aplica)
  - WSGI file: el que edite PythonAnywhere — suele importar `wsgi.py`.
- Configura las env vars en la sección "Environment Variables".
- Reinicia la aplicación desde el panel Web.
- Revisa `error.log` y `server.log` para diagnósticos.

5. Uso de Gunicorn (servidor WSGI para producción)
- Recomendado en VPS/VM: lanzar Gunicorn con 2–4 workers (según CPU).
```bash
source ~/.venvs/docuexpress/bin/activate
cd /path/to/project
# Escoger el número de workers según CPU; ejemplo 3
gunicorn -w 3 -b 0.0.0.0:8000 wsgi:application
```
- Usar `systemd` para mantener Gunicorn en background y reiniciar si falla.

6. Notas sobre Rate Limiting y Redis
- Para desarrollo o despliegue sin Redis: `RATELIMIT_STORAGE_URL=memory://` y `RATELIMIT_ENABLED=False` para desactivar.
- En producción con Redis: configura `RATELIMIT_STORAGE_URL=redis://<redis-host>:6379` y monta/asegura Redis.

7. Logs y diagnóstico
- La app escribe en `docuexpress.log` por defecto (ver `Config.LOG_FILE`).
- En PythonAnywhere, revisa los logs de la webapp y `error.log`.

8. Cómo subir los cambios a remoto (GitHub / GitLab)
```bash
# (si no hay remote configurado)
git remote add origin git@github.com:<tu_usuario>/<repo>.git
git push -u origin master
# o si tu rama principal es 'main'
# git push -u origin main
```

9. Checklist de despliegue
- [ ] Virtualenv con dependencias instaladas
- [ ] Variables de entorno configuradas
- [ ] WSGI apuntando a `application` desde `wsgi.py`
- [ ] (Opcional) Redis configurado o `RATELIMIT_ENABLED=False`
- [ ] Logs revisados tras reinicio

Contacto y siguiente paso
- Si quieres, puedo añadir un `systemd` unit file ejemplo para Gunicorn o preparar un script de despliegue automatizado (Fabric / Ansible). Indícame si prefieres GitHub Actions para CI/CD y lo preparo.
