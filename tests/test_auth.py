import pytest
from flask import abort
from flask_login import login_required, current_user
from app import create_app
from app.models import db, User, Department
from app.auth.decorators import role_required
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret"

@pytest.fixture
def app():
    """Setup app context, mock routes, and schema."""
    app = create_app(TestConfig)
    
    # Register a dummy administrative route protected by RBAC
    @app.route("/admin-only")
    @role_required("admin")
    def admin_only():
        return "Success Admin"

    @app.route("/manager-or-admin")
    @role_required("admin", "inventory_manager")
    def manager_or_admin():
        return "Success Manager or Admin"

    with app.app_context():
        db.create_all()
        # Seed departments
        dept1 = Department(name="IT")
        db.session.add(dept1)
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

def test_user_registration_route(client, db_session):
    """Verify that user registration adds a user to the DB with default 'employee' role."""
    dept = db_session.query(Department).first()
    
    response = client.post("/auth/register", data={
        "username": "newuser",
        "email": "newuser@gatim.com",
        "department_id": dept.id,
        "password": "SecurePassword123",
        "confirm_password": "SecurePassword123"
    }, follow_redirects=True)
    
    assert response.status_code == 200
    # Retrieve user
    user = db_session.query(User).filter_by(username="newuser").first()
    assert user is not None
    assert user.email == "newuser@gatim.com"
    assert user.role == "employee"  # default role
    assert user.check_password("SecurePassword123") is True

def test_login_logout_flow(client, db_session):
    """Verify login validation, session establishment, and logout."""
    dept = db_session.query(Department).first()
    user = User(username="test_login", email="login@gatim.com", department=dept, role="user")
    user.set_password("MyPassword")
    db_session.add(user)
    db_session.commit()
    
    # 1. Login with bad credentials
    response = client.post("/auth/login", data={
        "username": "test_login",
        "password": "WrongPassword"
    }, follow_redirects=True)
    assert b"Gecersiz kullanici adi veya sifre" in response.data or b"Ge\xc3\xa7ersiz kullan\xc4\xb1c\xc4\xb1 ad\xc4\xb1 veya \xc5\x9fifre" in response.data

    # 2. Login with correct credentials
    response = client.post("/auth/login", data={
        "username": "test_login",
        "password": "MyPassword"
    }, follow_redirects=True)
    assert response.status_code == 200
    
    # 3. Logged in session should access dashboard (which triggers index route /)
    # The response data will contain the dashboard content since follow_redirects=True
    assert b"GAT\xc4\xb0M Sistem \xc3\x96zeti" in response.data
    
    # 4. Logout
    response = client.get("/auth/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"Sisteme Giri\xc5\x9f" in response.data  # Should redirect back to login page

def test_rbac_access_restrictions(client, db_session):
    """Verify that the role_required decorator enforces access rules (401, 403, 200)."""
    # 1. Access without login -> should raise 401 Unauthenticated
    response = client.get("/admin-only")
    assert response.status_code == 401

    # Setup roles
    dept = db_session.query(Department).first()
    admin_user = User(username="admin_user", email="admin@gatim.com", department=dept, role="admin")
    admin_user.set_password("pass")
    
    employee_user = User(username="emp_user", email="emp@gatim.com", department=dept, role="employee")
    employee_user.set_password("pass")

    manager_user = User(username="mgr_user", email="mgr@gatim.com", department=dept, role="inventory_manager")
    manager_user.set_password("pass")

    db_session.add_all([admin_user, employee_user, manager_user])
    db_session.commit()

    # Helper function to login
    def login_client(username):
        client.post("/auth/login", data={"username": username, "password": "pass"})

    # 2. Log in as employee (unauthorized for admin routes)
    login_client("emp_user")
    
    # Try accessing admin-only route -> 403 Forbidden
    response = client.get("/admin-only")
    assert response.status_code == 403
    
    # Try accessing manager-or-admin route -> 403 Forbidden
    response = client.get("/manager-or-admin")
    assert response.status_code == 403
    
    client.get("/auth/logout")

    # 3. Log in as manager (authorized for manager-or-admin, NOT admin-only)
    login_client("mgr_user")
    
    response = client.get("/admin-only")
    assert response.status_code == 403
    
    response = client.get("/manager-or-admin")
    assert response.status_code == 200
    assert b"Success Manager or Admin" in response.data
    
    client.get("/auth/logout")

    # 4. Log in as admin (authorized for all)
    login_client("admin_user")
    
    response = client.get("/admin-only")
    assert response.status_code == 200
    assert b"Success Admin" in response.data
    
    response = client.get("/manager-or-admin")
    assert response.status_code == 200
    assert b"Success Manager or Admin" in response.data
