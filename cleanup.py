import os

obsolete_files = [
    "ARCHIVOS/api_routes.py",
    "ARCHIVOS/config_routes.py",
    "ARCHIVOS/app_improved.py",
    "ARCHIVOS/docuexpressoficial.py",
    "ARCHIVOS/debug_templates.py",
    "ARCHIVOS/update_templates.py",
    "ARCHIVOS/migrate_to_database.py",
    "ARCHIVOS/init_db.py",
    "ARCHIVOS/crear_admin.py",
]

for file_path in obsolete_files:
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"Removed {file_path}")
    else:
        print(f"{file_path} not found.")
