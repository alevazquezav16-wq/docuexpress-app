import pytest
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:5001"  # Puerto actualizado para Flask
USERNAME = "admin"  # Cambia por usuario válido
PASSWORD = "admin123"  # Cambia por contraseña válida

@pytest.mark.e2e
def test_registro_papeleria_y_tramite():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        # 1. Login
        page.goto(f"{BASE_URL}/auth/login")
        page.fill('input[name="username"]', USERNAME)
        page.fill('input[name="password"]', PASSWORD)
        page.click('button[type="submit"]')
        page.wait_for_selector('#dashboard-container')
        # 2. Registrar papelería
        page.click('button[data-bs-target="#addPapeleriaModal"]')
        page.fill('input[name="nombre"]', "Papelería E2E Test")
        page.click('#add-papeleria-form button[type="submit"]')
        try:
            page.wait_for_selector('#flash-container:has-text("Papelería agregada o reactivada con éxito.")', timeout=10000)
        except Exception:
            # Captura el contenido del modal tras el error
            modal_content = page.inner_html('#add-papeleria-form-container')
            print("[E2E DEBUG] Modal tras error:")
            print(modal_content)
            raise
        # 3. Verificar que aparece en la lista sin refrescar
        assert page.is_visible('text=Papelería E2E Test')
        # 4. Registrar trámite
        # Esperar a que la opción esté disponible en el select
        page.wait_for_selector('select[name="papeleria_id"] >> text=Papelería E2E Test', timeout=10000)
        page.select_option('select[name="papeleria_id"]', label="Papelería E2E Test")
        page.select_option('select[name="tramite"]', label="ACTA DE NACIMIENTO")
        page.fill('input[name="precio"]', "50.00")
        page.fill('input[name="costo"]', "25.00")
        page.fill('input[name="cantidad"]', "1")
        page.fill('input[name="fecha"]', page.locator('input[name="fecha"]').input_value())
        page.click('#form-registrar-tramite button[type="submit"]')
        page.wait_for_selector('text=registrados correctamente')
        # 5. Verificar métricas y estadísticas
        assert page.is_visible('text=Ganancia Total')
        assert page.is_visible('text=Total de Trámites')
        # 6. Probar filtros de fecha
        page.click('label[for="range7d"]')
        page.wait_for_timeout(500)
        page.click('label[for="range30d"]')
        page.wait_for_timeout(500)
        # 7. Verificar que no hay errores visibles
        assert not page.is_visible('text=Error')
        browser.close()
