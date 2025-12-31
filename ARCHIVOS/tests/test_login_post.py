import pytest
from ARCHIVOS.app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_login_post_invalid(client):
    # Retrieve CSRF token from the form (if present) and include it in the POST
    get_resp = client.get('/auth/login')
    html = get_resp.get_data(as_text=True)
    import re
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    csrf = m.group(1) if m else None

    response = client.post('/auth/login', data={
        'username': 'usuario_invalido',
        'password': 'clave_invalida',
        'csrf_token': csrf
    }, follow_redirects=True)
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert 'Usuario o contraseña' in text or 'error' in text
