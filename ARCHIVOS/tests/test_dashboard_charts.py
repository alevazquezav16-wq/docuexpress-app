import pytest
from ARCHIVOS.app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_dashboard_charts_requires_login(client):
    response = client.get('/api/dashboard-charts')
    # Debe redirigir al login si no está autenticado
    assert response.status_code in (302, 401)
    assert b'inicia sesi' in response.data or b'login' in response.data
