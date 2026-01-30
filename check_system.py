import os
import sys
from pathlib import Path

def check():
    print("\n🔍 VERIFICACIÓN DE SISTEMA DOCUEXPRESS")
    print("=======================================")
    
    base_dir = Path(__file__).parent
    archivos_dir = base_dir / 'ARCHIVOS'
    
    # 1. Verificar estructura de directorios
    print("\n[1/3] Verificando directorios...")
    required_dirs = [
        archivos_dir,
        archivos_dir / 'static',
        archivos_dir / 'static' / 'uploads',
        archivos_dir / 'static' / 'receipts',
        archivos_dir / 'templates',
        archivos_dir / 'routes',
        archivos_dir / 'backups'
    ]
    
    all_dirs_ok = True
    for d in required_dirs:
        if not d.exists():
            print(f"   ❌ Falta: {d.relative_to(base_dir)}")
            try:
                d.mkdir(parents=True, exist_ok=True)
                print(f"      ✅ Creado automáticamente.")
            except Exception as e:
                print(f"      ❌ Error al crear: {e}")
                all_dirs_ok = False
        else:
            print(f"   ✅ OK: {d.relative_to(base_dir)}")
            
    # 2. Verificar dependencias
    print("\n[2/3] Verificando librerías Python...")
    try:
        import flask
        import flask_login
        import flask_wtf
        import sqlalchemy
        import apscheduler
        import dotenv
        print("   ✅ Todas las dependencias críticas encontradas.")
    except ImportError as e:
        print(f"   ❌ Faltan dependencias: {e.name}")
        print("      Ejecuta: pip install -r ARCHIVOS/requirements.txt")
        
    # 3. Verificar base de datos
    print("\n[3/3] Verificando base de datos...")
    db_path = archivos_dir / 'control_papelerias.db'
    if db_path.exists():
        print(f"   ✅ Base de datos encontrada ({db_path.stat().st_size / 1024:.1f} KB)")
    else:
        print("   ⚠️  Base de datos no encontrada (se creará automáticamente al iniciar).")

    print("\n✅ VERIFICACIÓN COMPLETADA")
    print("   Para iniciar el programa, ejecuta: python3 run.py\n")

if __name__ == "__main__":
    check()