import pytest
import os
from ARCHIVOS.app import create_app
from ARCHIVOS.models import db, User, Papeleria, Tramite, Gasto

class TestConfig:
    """Test configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret-key'
    # Ensure the app knows where to find the templates, etc.
    # As the tests are in a subdirectory, the root path might need adjustment.
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    # Provide a DATABASE_PATH so backup_manager can initialize without errors
    DATABASE_PATH = os.path.join(BASE_DIR, 'test_database.sqlite')
    # Disable rate limiting during tests to avoid Redis dependency
    RATELIMIT_ENABLED = False
    # You might not need this if your app structure handles it, but it's a common pattern.
    # For instance, if your create_app uses instance_relative_config.

    @staticmethod
    def init_app(app):
        """Initialize test app - minimal setup for tests."""
        pass

@pytest.fixture(scope='module')
def app():
    """Create and configure a new app instance for each test module."""
    app = create_app(config_class=TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture(scope='module')
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture(scope='function')
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()

@pytest.fixture(scope='function')
def init_database(app):
    """Seed the database with some test data."""
    with app.app_context():
        # Clean up all tables before seeding
        db.session.query(Gasto).delete()
        db.session.query(Tramite).delete()
        db.session.query(Papeleria).delete()
        db.session.query(User).delete()
        db.session.commit()

        # Seed users
        user = User(id=1, username='testuser', role='employee')
        user.set_password('password')
        admin = User(id=2, username='admin', role='admin')
        admin.set_password('password')
        db.session.add(user)
        db.session.add(admin)
        db.session.commit()

        # Seed papeleria for the test user
        papeleria = Papeleria(id=1, nombre='Test Papeleria', user_id=user.id)
        db.session.add(papeleria)
        db.session.commit()
        
        yield db

        # Clean up after the test function
        db.session.remove()
