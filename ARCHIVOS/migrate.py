# ARCHIVOS/migrate.py
import sqlite3
from pathlib import Path
import sys

def migrate():
    """
    Añade la columna `is_active` a la tabla `papelerias` si no existe.
    Este script es seguro para ser ejecutado múltiples veces (idempotente).
    """
    try:
        # La base de datos está en el mismo directorio que este script
        db_path = Path(__file__).resolve().parent / 'control_papelerias.db'

        if not db_path.exists():
            print(f"Error: La base de datos no se encuentra en la ruta esperada: {db_path}", file=sys.stderr)
            sys.exit(1)

        print(f"Conectando a la base de datos en: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 1. Verificar si la columna 'is_active' ya existe
        print("Verificando la estructura de la tabla 'papelerias'...")
        cursor.execute("PRAGMA table_info(papelerias);")
        columns = [column[1] for column in cursor.fetchall()]

        if 'is_active' in columns:
            print("La columna 'is_active' ya existe en la tabla 'papelerias'. No se necesita migración.")
        else:
            # 2. Si no existe, añadir la columna
            print("La columna 'is_active' no existe. Añadiéndola...")
            # Usamos NOT NULL y DEFAULT 1 para asegurar que las filas existentes
            # se marquen como activas por defecto.
            alter_query = "ALTER TABLE papelerias ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"
            cursor.execute(alter_query)
            print("Columna 'is_active' añadida con éxito.")

        # 3. Guardar cambios y cerrar la conexión
        conn.commit()
        conn.close()
        print("Migración completada exitosamente.")

    except sqlite3.Error as e:
        print(f"Error de base de datos durante la migración: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Un error inesperado ocurrió: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    migrate()
