import pytest
from ARCHIVOS.app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_404_error(client):
    response = client.get('/ruta-que-no-existe')
    assert response.status_code == 404
    text = response.get_data(as_text=True)
    assert 'Página no encontrada' in text or '404' in text
