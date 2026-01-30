import pytest
from ARCHIVOS.app import create_app

class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    DATABASE_PATH = ':memory:'  # Para compatibilidad con backup_manager y otros módulos
    SECRET_KEY = 'test_secret'  # Necesario para sesiones Flask
    @staticmethod
    def init_app(app):
        pass

@pytest.fixture
def app():
    app = create_app(TestConfig)
    yield app
