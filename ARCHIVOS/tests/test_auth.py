from flask import url_for, session
from ARCHIVOS.models import User

def test_login_logout(client, init_database):
    """Test login and logout functionality."""
    # Test successful login
    response = client.post(url_for('auth.login'), data={
        'username': 'testuser',
        'password': 'password'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Has iniciado sesi' not in response.data # This message is for logout

    # Test that the user is logged in
    response = client.get(url_for('main.index'))
    assert response.status_code == 200

    # Test logout
    response = client.get(url_for('auth.logout'), follow_redirects=True)
    assert response.status_code == 200
    assert b'Has cerrado sesi' in response.data

    # Test that the user is logged out
    response = client.get(url_for('main.index'), follow_redirects=True)
    assert response.status_code == 200
    assert b'Por favor, inicia sesi' in response.data


def test_login_invalid_credentials(client, init_database):
    """Test login with invalid credentials."""
    response = client.post(url_for('auth.login'), data={
        'username': 'wronguser',
        'password': 'wrongpassword'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Usuario o contra' in response.data


def test_admin_impersonation(client, init_database):
    """Test the admin impersonation feature."""
    # Login as admin
    response = client.post(url_for('auth.login'), data={
        'username': 'admin',
        'password': 'password'
    })
    assert response.status_code == 302  # Should redirect after successful login

    # Get the user to impersonate
    user_to_impersonate = User.query.filter_by(username='testuser').first()
    assert user_to_impersonate is not None

    # Start impersonation
    response = client.get(url_for('auth.view_user_dashboard', user_id=user_to_impersonate.id), follow_redirects=True)
    assert response.status_code == 200
    
    # Check session variables are set
    with client.session_transaction() as sess:
        assert sess['viewing_user_id'] == user_to_impersonate.id
        assert sess['viewing_user_name'] == user_to_impersonate.username

    # Stop impersonation
    response = client.get(url_for('auth.stop_viewing'), follow_redirects=True)
    assert response.status_code == 200
    assert b'Has vuelto a tu panel de administrador' in response.data
    
    with client.session_transaction() as sess:
        assert 'viewing_user_id' not in sess
        assert 'viewing_user_name' not in sess
