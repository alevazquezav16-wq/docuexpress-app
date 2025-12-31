# 🔐 Guía de Seguridad - DocuExpress

## ✅ Medidas de Seguridad Implementadas

### 1. SECRET_KEY Seguro

**Estado**: ✅ **IMPLEMENTADO**

La aplicación ahora utiliza una clave secreta generada automáticamente de forma segura.

#### Configuración

El `SECRET_KEY` se carga desde el archivo `.env`:

```bash
FLASK_SECRET_KEY=29357590fef8a48df50464c391a551f97d928eaacd84c93495e81b8bf5827909
```

#### Generar Nueva Clave

Para producción, genera una clave única con:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Luego actualiza el valor en `.env`.

#### Comportamiento

- ✅ Si `FLASK_SECRET_KEY` está en `.env`: Se usa esa clave
- ✅ Si NO está en `.env`: Se genera una automáticamente (64 caracteres hex)
- ⚠️ En producción (`DEBUG=False`) sin clave configurada: Muestra advertencia

---

### 2. Rate Limiting (Límite de Peticiones)

**Estado**: ✅ **IMPLEMENTADO**

Protección contra abuso de API con Flask-Limiter.

#### Configuración (.env)

```bash
RATELIMIT_ENABLED=True
RATELIMIT_STORAGE_URL=memory://
RATELIMIT_DEFAULT=200 per day;50 per hour
RATELIMIT_API=100 per day;20 per hour
```

#### Límites Aplicados

| Ruta | Límite |
|------|--------|
| Rutas generales | 200/día, 50/hora |
| `/api/dashboard-charts` | 100/día, 20/hora |
| `/api/buscar` | 50/hora (más estricto) |

#### Cambiar a Redis (Recomendado para Producción)

Para producción con múltiples workers:

1. Instalar Redis:
   ```bash
   sudo apt install redis-server
   pip3 install redis
   ```

2. Actualizar `.env`:
   ```bash
   RATELIMIT_STORAGE_URL=redis://localhost:6379
   ```

#### Deshabilitar Rate Limiting

```bash
RATELIMIT_ENABLED=False
```

---

### 3. Backup Automático de Base de Datos

**Estado**: ✅ **IMPLEMENTADO**

Sistema de backups programados con APScheduler.

#### Configuración (.env)

```bash
BACKUP_ENABLED=True
BACKUP_DIR=backups
BACKUP_RETENTION_DAYS=30
BACKUP_SCHEDULE=daily
BACKUP_ON_START=True
```

#### Frecuencias Disponibles

- `daily` - Diario a las 2 AM (por defecto)
- `hourly` - Cada hora en punto
- `weekly` - Domingos a las 2 AM

#### Directorio de Backups

Los backups se guardan en:

```
ARCHIVOS/backups/
  ├── control_papelerias_backup_20251224_020000.db
  ├── control_papelerias_backup_20251223_020000.db
  └── ...
```

#### Retención Automática

Los backups más antiguos que `BACKUP_RETENTION_DAYS` (30 días por defecto) se eliminan automáticamente.

#### Gestión Manual de Backups

**API Endpoints (Solo Admin)**:

1. **Listar backups**:
   ```bash
   GET /configuracion/backups
   ```

2. **Crear backup manual**:
   ```bash
   POST /configuracion/backups/create
   ```

3. **Descargar backup**:
   ```bash
   GET /configuracion/backups/download/<filename>
   ```

4. **Restaurar backup**:
   ```bash
   POST /configuracion/backups/restore/<filename>
   ```

**Desde Python**:

```python
from backup_manager import backup_manager

# Crear backup
backup_path = backup_manager.create_backup(manual=True)

# Listar backups
backups = backup_manager.list_backups()

# Restaurar
backup_manager.restore_backup('control_papelerias_backup_20251224_020000.db')
```

#### Deshabilitar Backups

```bash
BACKUP_ENABLED=False
```

---

## 🚀 Configuración para Producción

### Archivo `.env` de Producción

```bash
# ==================== SEGURIDAD ====================
FLASK_SECRET_KEY=<genera-una-clave-unica-aqui>

# ==================== APLICACIÓN ====================
FLASK_DEBUG=False
FLASK_ENV=production

# ==================== RATE LIMITING ====================
RATELIMIT_ENABLED=True
RATELIMIT_STORAGE_URL=redis://localhost:6379
RATELIMIT_DEFAULT=1000 per day;100 per hour
RATELIMIT_API=500 per day;50 per hour

# ==================== BACKUP AUTOMÁTICO ====================
BACKUP_ENABLED=True
BACKUP_DIR=/var/backups/docuexpress
BACKUP_RETENTION_DAYS=90
BACKUP_SCHEDULE=daily
BACKUP_ON_START=False

# ==================== SESIÓN ====================
SESSION_COOKIE_SECURE=True

# ==================== LOGGING ====================
LOG_LEVEL=WARNING
```

### Checklist de Producción

- [ ] Generar `FLASK_SECRET_KEY` único
- [ ] `FLASK_DEBUG=False`
- [ ] `SESSION_COOKIE_SECURE=True` (con HTTPS)
- [ ] Rate Limiting con Redis
- [ ] Backups en directorio externo
- [ ] `LOG_LEVEL=WARNING` o `ERROR`
- [ ] Configurar firewall
- [ ] Usar HTTPS (certificado SSL)
- [ ] Configurar servidor de producción (Gunicorn/uWSGI)
- [ ] Reverse proxy (Nginx/Apache)

---

## 📦 Dependencias Agregadas

```txt
Flask-Limiter==3.5.0      # Rate limiting
python-dotenv==1.0.0      # Variables de entorno
APScheduler==3.10.4       # Backups programados
```

Instalar con:

```bash
pip3 install -r requirements.txt
```

---

## 🔒 Archivos de Seguridad

### `.env` (NUNCA SUBIR A GIT)

Contiene configuración sensible. Ya está en `.gitignore`.

### `.env.example`

Template de ejemplo para otros desarrolladores.

### `.gitignore`

Protege archivos sensibles:

```gitignore
.env
.env.local
.env.production
backups/
*.db
*.db.backup_*
logs/
secrets.json
credentials.json
*.pem
*.key
```

---

## 📊 Monitoreo

### Verificar Configuración

```bash
cd ARCHIVOS
python3 -c "
from app import create_app
app = create_app()
with app.app_context():
    print(f'SECRET_KEY: {len(app.config[\"SECRET_KEY\"])} chars')
    print(f'Rate Limiting: {hasattr(app, \"limiter\")}')
    print(f'Backups: {app.config.get(\"BACKUP_ENABLED\")}')
"
```

### Logs

Los logs incluyen información sobre:

- ✅ Carga de SECRET_KEY
- ✅ Estado de Rate Limiting
- ✅ Backups creados/eliminados
- ✅ Programación de tareas

---

## 🆘 Troubleshooting

### Error: "No module named 'flask_limiter'"

```bash
pip3 install Flask-Limiter
```

### Error: "No module named 'dotenv'"

```bash
pip3 install python-dotenv
```

### Error: "No module named 'apscheduler'"

```bash
pip3 install APScheduler
```

### Backups no se crean

1. Verificar que `BACKUP_ENABLED=True` en `.env`
2. Verificar permisos del directorio `backups/`
3. Revisar logs de la aplicación

### Rate Limiting no funciona

1. Verificar que `RATELIMIT_ENABLED=True` en `.env`
2. Si usas Redis, verificar que esté corriendo:
   ```bash
   redis-cli ping
   ```

---

## 📞 Soporte

Para reportar problemas de seguridad, contactar al administrador del sistema.

**Última actualización**: 24 de diciembre de 2025
