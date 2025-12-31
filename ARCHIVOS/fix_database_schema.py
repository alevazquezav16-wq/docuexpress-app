"""
Script para corregir el schema de la base de datos.
Elimina el constraint UNIQUE global en nombre y agrega UNIQUE(nombre, user_id)
"""
import sqlite3
import sys
import os

def fix_papelerias_schema():
    db_path = 'control_papelerias.db'
    
    print("=" * 70)
    print("CORRECCIÓN DEL SCHEMA DE LA TABLA papelerias")
    print("=" * 70)
    
    # Backup de la base de datos
    import shutil
    backup_path = f"{db_path}.backup_{os.getpid()}"
    shutil.copy2(db_path, backup_path)
    print(f"\n✅ Backup creado: {backup_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. Mostrar schema actual
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='papelerias'")
        old_schema = cursor.fetchone()[0]
        print(f"\n📋 Schema ACTUAL:")
        print(old_schema)
        
        # 1.5. Verificar registros con user_id NULL o inválido
        cursor.execute("SELECT COUNT(*) FROM papelerias WHERE user_id IS NULL")
        null_count = cursor.fetchone()[0]
        if null_count > 0:
            print(f"\n⚠️  Encontrados {null_count} registros con user_id NULL")
            print(f"   Estos registros serán eliminados antes de la migración")
            cursor.execute("DELETE FROM papelerias WHERE user_id IS NULL")
            print(f"✅ {null_count} registros eliminados")
        
        # Verificar user_id huérfanos (que no existen en users)
        cursor.execute("""
            SELECT COUNT(*) FROM papelerias p 
            WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = p.user_id)
        """)
        orphan_count = cursor.fetchone()[0]
        if orphan_count > 0:
            print(f"\n⚠️  Encontrados {orphan_count} registros con user_id huérfano")
            cursor.execute("""
                SELECT p.id, p.nombre, p.user_id 
                FROM papelerias p 
                WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = p.user_id)
                LIMIT 10
            """)
            orphans = cursor.fetchall()
            print("   Ejemplos:")
            for o in orphans:
                print(f"     - ID {o[0]}: '{o[1]}' (user_id={o[2]})")
            
            print(f"   Estos registros serán eliminados antes de la migración")
            cursor.execute("""
                DELETE FROM papelerias 
                WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = papelerias.user_id)
            """)
            print(f"✅ {orphan_count} registros huérfanos eliminados")
        
        # 2. Crear tabla temporal con el schema correcto
        print(f"\n🔧 Creando tabla temporal con schema correcto...")
        cursor.execute("""
            CREATE TABLE papelerias_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                UNIQUE(nombre, user_id)
            )
        """)
        
        # 3. Copiar datos de la tabla antigua a la nueva
        print(f"📦 Copiando datos...")
        cursor.execute("""
            INSERT INTO papelerias_new (id, nombre, user_id, is_active)
            SELECT id, nombre, user_id, is_active
            FROM papelerias
        """)
        
        rows_copied = cursor.rowcount
        print(f"✅ {rows_copied} registros copiados")
        
        # 4. Eliminar tabla antigua
        print(f"🗑️  Eliminando tabla antigua...")
        cursor.execute("DROP TABLE papelerias")
        
        # 5. Renombrar tabla nueva
        print(f"📝 Renombrando tabla nueva...")
        cursor.execute("ALTER TABLE papelerias_new RENAME TO papelerias")
        
        # 6. Recrear índices
        print(f"🔗 Recreando índices...")
        cursor.execute("CREATE INDEX idx_papelerias_user ON papelerias (user_id)")
        
        # 7. Verificar el nuevo schema
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='papelerias'")
        new_schema = cursor.fetchone()[0]
        print(f"\n📋 Schema NUEVO:")
        print(new_schema)
        
        # 8. Commit
        conn.commit()
        print(f"\n✅ MIGRACIÓN COMPLETADA CON ÉXITO")
        
        # 9. Verificar integridad
        cursor.execute("PRAGMA integrity_check")
        integrity = cursor.fetchone()[0]
        print(f"\n🔍 Verificación de integridad: {integrity}")
        
        # 10. Mostrar estadísticas
        cursor.execute("SELECT COUNT(*) FROM papelerias")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM papelerias WHERE is_active = 1")
        active = cursor.fetchone()[0]
        print(f"\n📊 Estadísticas:")
        print(f"   Total de papelerías: {total}")
        print(f"   Papelerías activas: {active}")
        print(f"   Papelerías eliminadas: {total - active}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR durante la migración: {e}")
        print(f"🔄 Revirtiendo cambios...")
        conn.rollback()
        print(f"💾 Restaura el backup manualmente si es necesario: {backup_path}")
        return False
        
    finally:
        conn.close()

if __name__ == '__main__':
    os.chdir('/home/vladtrix/DOCUEXPRESS PAGINA/ARCHIVOS')
    
    print("\n⚠️  ADVERTENCIA: Este script modificará el schema de la base de datos")
    print("   Se creará un backup automático antes de proceder")
    print()
    
    response = input("¿Continuar? (SI/no): ")
    if response.upper() == 'SI':
        success = fix_papelerias_schema()
        if success:
            print("\n" + "=" * 70)
            print("🎉 SOLUCIÓN IMPLEMENTADA")
            print("=" * 70)
            print("\nAhora puedes:")
            print("  ✅ Agregar papelerías con nombres duplicados entre usuarios")
            print("  ✅ Cada usuario puede tener su propia 'PAPELERIA LOPEZ'")
            print("  ✅ El constraint UNIQUE ahora es por (nombre, user_id)")
            sys.exit(0)
        else:
            print("\n❌ La migración falló. Revisa los errores arriba.")
            sys.exit(1)
    else:
        print("❌ Operación cancelada por el usuario")
        sys.exit(1)
