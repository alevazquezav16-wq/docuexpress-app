import os
import sys

# 1. Configurar el path para que Python encuentre el paquete 'ARCHIVOS'
current_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, current_dir)

try:
    from ARCHIVOS.app import create_app
except ImportError as e:
    print("\n❌ ERROR CRÍTICO DE IMPORTACIÓN")
    print(f"No se pudo importar la aplicación. Asegúrate de que la carpeta 'ARCHIVOS' está en: {current_dir}")
    print(f"Detalle del error: {e}\n")
    sys.exit(1)

if __name__ == "__main__":
    print("\n🚀 INICIANDO DOCUEXPRESS...")
    print(f"📂 Directorio base: {current_dir}")
    print("--------------------------------------------------")
    
    app = create_app()
    
    print("✅ Servidor activo en: http://127.0.0.1:5000")
    print("   (Presiona CTRL+C para detener)\n")
    app.run(debug=True, host="0.0.0.0", port=5000)