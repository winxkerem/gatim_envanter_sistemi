import pytest
from app import create_app
from app.models import db, User, Department
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret"
    PROPAGATE_EXCEPTIONS = False

@pytest.fixture
def app():
    """Setup app context and schema."""
    app = create_app(TestConfig)
    
    # Simple route to trigger 500 error for handler test
    @app.route("/trigger-500")
    def trigger_500():
        raise Exception("Forced server error")

    with app.app_context():
        db.create_all()
        dept = Department(name="IT")
        db.session.add(dept)
        db.session.commit()
        
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def db_session(app):
    return db.session

def test_admin_users_access_and_role_promotion(client, db_session):
    """Verify that only admins can access users management and edit roles, but cannot edit themselves."""
    dept = db_session.query(Department).first()
    
    admin = User(username="admin_user", email="admin@gatim.com", department=dept, role="admin")
    admin.set_password("pass")
    
    emp = User(username="employee_user", email="emp@gatim.com", department=dept, role="employee")
    emp.set_password("pass")
    
    db_session.add_all([admin, emp])
    db_session.commit()

    # 1. Non-admin employee access -> 403 Forbidden
    client.post("/auth/login", data={"username": "employee_user", "password": "pass"})
    response = client.get("/admin/users")
    assert response.status_code == 403
    
    response = client.post(f"/admin/users/{emp.id}/update-role", data={"role": "inventory_manager"})
    assert response.status_code == 403
    
    client.get("/auth/logout")

    # 2. Admin access -> 200 OK
    client.post("/auth/login", data={"username": "admin_user", "password": "pass"})
    response = client.get("/admin/users")
    assert response.status_code == 200
    assert "Kullanıcı Rol Yönetimi" in response.data.decode("utf-8")

    # Promote employee to inventory_manager
    response = client.post(f"/admin/users/{emp.id}/update-role", data={"role": "inventory_manager"}, follow_redirects=True)
    assert response.status_code == 200
    db_session.refresh(emp)
    assert emp.role == "inventory_manager"

    # Prevent self-demotion
    response = client.post(f"/admin/users/{admin.id}/update-role", data={"role": "employee"}, follow_redirects=True)
    assert response.status_code == 200
    db_session.refresh(admin)
    assert admin.role == "admin"  # unchanged
    assert "Kendi" in response.data.decode("utf-8") or "değiştiremezsiniz" in response.data.decode("utf-8")

def test_custom_error_handlers(client, db_session):
    """Verify that error handlers render branded HTML templates with correct status codes."""
    dept = db_session.query(Department).first()
    user = User(username="employee_user", email="emp@gatim.com", department=dept, role="employee")
    user.set_password("pass")
    db_session.add(user)
    db_session.commit()
    
    client.post("/auth/login", data={"username": "employee_user", "password": "pass"})

    # 1. Test 403 error handler (trying to access admin page as employee)
    response = client.get("/admin/users")
    assert response.status_code == 403
    assert "Erişim Engellendi (403)" in response.data.decode("utf-8")

    # 2. Test 404 error handler (non-existent route)
    response = client.get("/this-route-does-not-exist")
    assert response.status_code == 404
    assert "Sayfa Bulunamadı (404)" in response.data.decode("utf-8")

    # 3. Test 500 error handler (trigger server exception)
    response = client.get("/trigger-500")
    assert response.status_code == 500
    assert "Sistem Hatası (500)" in response.data.decode("utf-8")

