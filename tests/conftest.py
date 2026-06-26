import pytest
from app import create_app
from app.models import db, User, Department, Category, InventoryItem, InventoryRequest, RequestLog
from config import Config

class TestConfig(Config):
    """Test environment configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret"
    PROPAGATE_EXCEPTIONS = False

@pytest.fixture
def app():
    """Isolated Flask application context and schema setup."""
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        
        # Seed core organizational dependencies
        dept_it = Department(name="Yazılım Geliştirme")
        dept_sec = Department(name="Siber Güvenlik")
        cat_dev = Category(name="Geliştirici Ekipmanları")
        cat_srv = Category(name="Sunucu Altyapısı")
        
        db.session.add_all([dept_it, dept_sec, cat_dev, cat_srv])
        db.session.commit()
        
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Flask test client instance."""
    return app.test_client()

@pytest.fixture
def db_session(app):
    """SQLAlchemy scoped session handler."""
    return db.session
