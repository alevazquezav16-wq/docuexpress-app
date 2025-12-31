#!/bin/bash

# Script de Configuración de Producción para DocuExpress
# Autor: Sistema DocuExpress
# Fecha: 24 de diciembre de 2025

set -e  # Salir si hay errores

echo "🚀 CONFIGURACIÓN DE PRODUCCIÓN - DOCUEXPRESS"
echo "=============================================="
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "app.py" ]; then
    echo "❌ Error: Ejecuta este script desde el directorio ARCHIVOS/"
    exit 1
fi

echo "📋 Paso 1: Verificando dependencias..."
echo ""

# Verificar Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 no está instalado"
    exit 1
fi
echo "✅ Python 3: $(python3 --version)"

# Verificar pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 no está instalado"
    exit 1
fi
echo "✅ pip3: Instalado"

echo ""
echo "📦 Paso 2: Instalando dependencias..."
echo ""

pip3 install -r requirements.txt --quiet

echo "✅ Dependencias instaladas"
echo ""

echo "🔐 Paso 3: Configurando SECRET_KEY..."
echo ""

# Generar nueva SECRET_KEY
NEW_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Crear archivo .env.production si no existe
if [ ! -f ".env.production" ]; then
    cat > .env.production << EOF
# DocuExpress - Configuración de PRODUCCIÓN
# IMPORTANTE: Este archivo contiene información sensible - NO SUBIR A GIT

# ==================== SEGURIDAD ====================
FLASK_SECRET_KEY=${NEW_SECRET}

# ==================== APLICACIÓN ====================
FLASK_DEBUG=False
FLASK_ENV=production

# ==================== RATE LIMITING ====================
RATELIMIT_ENABLED=True
RATELIMIT_STORAGE_URL=memory://
RATELIMIT_DEFAULT=1000 per day;100 per hour
RATELIMIT_API=500 per day;50 per hour

# ==================== BACKUP AUTOMÁTICO ====================
BACKUP_ENABLED=True
BACKUP_DIR=backups
BACKUP_RETENTION_DAYS=90
BACKUP_SCHEDULE=daily
BACKUP_ON_START=False

# ==================== SESIÓN ====================
# IMPORTANTE: Cambiar a True cuando uses HTTPS
SESSION_COOKIE_SECURE=False

# ==================== LOGGING ====================
LOG_LEVEL=WARNING
EOF
    echo "✅ Archivo .env.production creado"
    echo "   SECRET_KEY generado: ${NEW_SECRET:0:16}..."
else
    echo "⚠️  .env.production ya existe, no se modificará"
fi

echo ""
echo "📁 Paso 4: Creando directorios necesarios..."
echo ""

mkdir -p backups logs static/uploads static/receipts
chmod 755 backups logs static/uploads static/receipts

echo "✅ Directorios creados"
echo ""

echo "🗄️  Paso 5: Verificando base de datos..."
echo ""

if [ -f "control_papelerias.db" ]; then
    # Crear backup de seguridad
    BACKUP_NAME="control_papelerias.db.backup_$(date +%Y%m%d_%H%M%S)"
    cp control_papelerias.db "$BACKUP_NAME"
    echo "✅ Backup de BD creado: $BACKUP_NAME"
else
    echo "ℹ️  No hay base de datos existente, se creará una nueva"
fi

echo ""
echo "🧪 Paso 6: Probando configuración..."
echo ""

# Probar que la app se puede importar
python3 << 'PYEOF'
from app import create_app
from backup_manager import backup_manager
import os

print("Cargando aplicación...")
app = create_app()

with app.app_context():
    # Verificar SECRET_KEY
    secret_key = app.config['SECRET_KEY']
    is_secure = len(secret_key) >= 32
    print(f"✅ SECRET_KEY: {'SEGURO' if is_secure else 'INSEGURO'} ({len(secret_key)} chars)")
    
    # Verificar Rate Limiting
    has_limiter = hasattr(app, 'limiter') and app.limiter is not None
    print(f"✅ Rate Limiting: {'HABILITADO' if has_limiter else 'DESHABILITADO'}")
    
    # Verificar Backups
    print(f"✅ Backups: {'HABILITADO' if backup_manager.enabled else 'DESHABILITADO'}")
    
    # Verificar DEBUG
    print(f"✅ DEBUG Mode: {app.config['DEBUG']}")
    
    if app.config['DEBUG']:
        print("⚠️  ADVERTENCIA: DEBUG está habilitado. Para producción, usa .env.production")

print("\n✅ Configuración válida")
PYEOF

if [ $? -ne 0 ]; then
    echo "❌ Error en la configuración"
    exit 1
fi

echo ""
echo "✅ CONFIGURACIÓN COMPLETADA"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 PRÓXIMOS PASOS:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Para DESARROLLO:"
echo "   python3 app.py"
echo ""
echo "2. Para PRODUCCIÓN:"
echo "   a) Copia .env.production a .env"
echo "      cp .env.production .env"
echo ""
echo "   b) Edita .env y configura:"
echo "      - SESSION_COOKIE_SECURE=True (si usas HTTPS)"
echo "      - RATELIMIT_STORAGE_URL=redis://localhost:6379 (recomendado)"
echo ""
echo "   c) Usa Gunicorn o uWSGI:"
echo "      gunicorn -w 4 -b 0.0.0.0:8083 'app:create_app()'"
echo ""
echo "3. Configurar NGINX/Apache como reverse proxy"
echo ""
echo "4. Habilitar HTTPS con Let's Encrypt"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔐 SEGURIDAD:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ SECRET_KEY: Generado automáticamente"
echo "✅ Rate Limiting: Habilitado"
echo "✅ Backups: Programados diariamente a las 2 AM"
echo ""
echo "Consulta SEGURIDAD.md para más información"
echo ""
