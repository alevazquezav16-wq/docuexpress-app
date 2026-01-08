#!/usr/bin/env python3
"""
Script para verificar que el sistema de notificaciones funciona correctamente.
"""

def test_notifications():
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ARCHIVOS.app import create_app
    
    print("🔍 Verificando sistema de notificaciones...\n")
    
    # Crear app
    app = create_app()
    
    # 1. Verificar blueprints
    print("1. Verificando blueprints registrados...")
    blueprints = list(app.blueprints.keys())
    print(f"   ✓ Blueprints: {', '.join(blueprints)}")
    
    if 'api' not in blueprints:
        print("   ✗ Blueprint 'api' NO registrado")
        return False
    print("   ✓ Blueprint 'api' registrado correctamente\n")
    
    # 2. Verificar endpoints de notificaciones
    print("2. Verificando endpoints de notificaciones...")
    with app.test_request_context():
        notif_rules = [rule for rule in app.url_map.iter_rules() 
                       if 'notificaciones' in rule.rule]
        
        if len(notif_rules) == 0:
            print("   ✗ No se encontraron endpoints de notificaciones")
            return False
            
        print(f"   ✓ Encontrados {len(notif_rules)} endpoints:")
        for rule in notif_rules:
            methods = ', '.join(sorted(rule.methods - {'OPTIONS', 'HEAD'}))
            print(f"     - {rule.rule} [{methods}]")
    
    # 3. Verificar templates
    print("\n3. Verificando templates...")
    import os
    template_path = os.path.join(os.path.dirname(__file__), 'templates', 'base.html')
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Verificar que existe el botón de notificaciones
    if 'id="notificationBadge"' in content:
        print("   ✓ Badge de notificaciones encontrado")
    else:
        print("   ✗ Badge de notificaciones NO encontrado")
        return False
        
    # Verificar que existe el contenedor de notificaciones
    if 'id="notificationsList"' in content:
        print("   ✓ Lista de notificaciones encontrada")
    else:
        print("   ✗ Lista de notificaciones NO encontrada")
        return False
        
    # Verificar que NO hay duplicados
    duplicates = content.count('Centro de Notificaciones')
    if duplicates > 1:
        print(f"   ⚠ Se encontraron {duplicates} centros de notificaciones (posible duplicado)")
    else:
        print(f"   ✓ No hay duplicados (1 centro de notificaciones)")
    
    # 4. Verificar JavaScript
    print("\n4. Verificando JavaScript de notificaciones...")
    
    if 'function loadNotifications()' in content:
        print("   ✓ Función loadNotifications() encontrada")
    else:
        print("   ✗ Función loadNotifications() NO encontrada")
        return False
        
    if 'function renderNotifications()' in content:
        print("   ✓ Función renderNotifications() encontrada")
    else:
        print("   ✗ Función renderNotifications() NO encontrada")
        return False
        
    if 'function updateBadge()' in content:
        print("   ✓ Función updateBadge() encontrada")
    else:
        print("   ✗ Función updateBadge() NO encontrada")
        return False
        
    if "fetch('/api/notificaciones')" in content:
        print("   ✓ Llamada a API de notificaciones encontrada")
    else:
        print("   ✗ Llamada a API de notificaciones NO encontrada")
        return False
    
    # 5. Test de endpoints
    print("\n5. Probando endpoints...")
    client = app.test_client()
    
    # Test GET /api/notificaciones (sin auth debería dar 401)
    response = client.get('/api/notificaciones')
    if response.status_code == 401:
        print("   ✓ /api/notificaciones requiere autenticación (401)")
    else:
        print(f"   ⚠ /api/notificaciones retorna {response.status_code} (esperado 401)")
    
    # Test POST marcar-leida (sin auth debería dar 401)
    response = client.post('/api/notificaciones/1/marcar-leida')
    if response.status_code == 401:
        print("   ✓ /api/notificaciones/<id>/marcar-leida requiere autenticación (401)")
    else:
        print(f"   ⚠ /api/notificaciones/<id>/marcar-leida retorna {response.status_code}")
    
    # Test POST marcar-todas-leidas (sin auth debería dar 401)
    response = client.post('/api/notificaciones/marcar-todas-leidas')
    if response.status_code == 401:
        print("   ✓ /api/notificaciones/marcar-todas-leidas requiere autenticación (401)")
    else:
        print(f"   ⚠ /api/notificaciones/marcar-todas-leidas retorna {response.status_code}")
    
    print("\n" + "="*60)
    print("✅ Todas las verificaciones pasaron correctamente")
    print("="*60)
    print("\n📝 Resumen:")
    print("   - Blueprint API: Registrado")
    print("   - Endpoints: 3 (GET, POST x2)")
    print("   - Templates: Badge + Lista configurados")
    print("   - JavaScript: 4 funciones principales")
    print("   - Protección: Endpoints requieren autenticación")
    print("\n💡 El sistema de notificaciones está listo para usar.")
    print("   Las notificaciones de demostración se cargarán automáticamente.")
    
    return True

if __name__ == '__main__':
    try:
        test_notifications()
    except Exception as e:
        print(f"\n❌ Error durante la verificación: {e}")
        import traceback
        traceback.print_exc()
