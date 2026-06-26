import pytest
from app import create_app
from app.models import db, User, Department, Category, InventoryItem, InventoryRequest, RequestLog
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret"

@pytest.fixture
def app():
    """Setup app context and schema."""
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        # Seed departments & categories
        dept = Department(name="IT")
        cat = Category(name="Electronics")
        db.session.add_all([dept, cat])
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

def test_request_creation_scenarios(client, db_session):
    """Verify request creation rules (positive quantities, warnings on excess stock)."""
    # 1. Login user
    dept = db_session.query(Department).first()
    cat = db_session.query(Category).first()
    
    user = User(username="employee", email="employee@gatim.com", department=dept, role="user")
    user.set_password("pass")
    item = InventoryItem(name="Monitor", sku="MON-001", quantity=3, critical_level=1, category=cat)
    db_session.add_all([user, item])
    db_session.commit()

    client.post("/auth/login", data={"username": "employee", "password": "pass"})

    # Scenario A: Valid request within stock limits
    response = client.post(f"/requests/create/{item.id}", data={"quantity": 2}, follow_redirects=True)
    assert response.status_code == 200
    
    # Assert DB State
    req = db_session.query(InventoryRequest).filter_by(item_id=item.id, quantity=2).first()
    assert req is not None
    assert req.status == "pending"
    assert req.requester_id == user.id
    
    # Assert initial creation log is generated
    initial_log = db_session.query(RequestLog).filter_by(request_id=req.id, status_to="pending").first()
    assert initial_log is not None
    assert initial_log.remarks == "Talep oluşturuldu."

    # Scenario B: Request exceeding current stock (allowed with warning message)
    response = client.post(f"/requests/create/{item.id}", data={"quantity": 10}, follow_redirects=True)
    assert response.status_code == 200
    assert b"mevcut envanter stok adedinden (3) fazladir" in response.data or b"mevcut envanter stok adedinden" in response.data
    
    req_excess = db_session.query(InventoryRequest).filter_by(item_id=item.id, quantity=10).first()
    assert req_excess is not None
    assert req_excess.status == "pending"

def test_request_management_listings(client, db_session):
    """Verify who can see which lists (all requests vs my requests)."""
    dept = db_session.query(Department).first()
    cat = db_session.query(Category).first()
    
    emp = User(username="employee1", email="emp1@gatim.com", department=dept, role="employee")
    emp.set_password("pass")
    
    mgr = User(username="manager1", email="mgr1@gatim.com", department=dept, role="inventory_manager")
    mgr.set_password("pass")

    db_session.add_all([emp, mgr])
    db_session.commit()

    # Log in as normal employee
    client.post("/auth/login", data={"username": "employee1", "password": "pass"})
    
    # Can access own requests
    response = client.get("/requests/my")
    assert response.status_code == 200
    
    # CANNOT access all requests (gets 403)
    response = client.get("/requests/all")
    assert response.status_code == 403
    
    client.get("/auth/logout")

    # Log in as manager
    client.post("/auth/login", data={"username": "manager1", "password": "pass"})
    
    # Can access all requests list
    response = client.get("/requests/all")
    assert response.status_code == 200

def test_request_decision_lifecycle_and_audit(client, db_session):
    """Verify approval, rejection, delivery, and cancellation rules."""
    dept = db_session.query(Department).first()
    cat = db_session.query(Category).first()
    
    emp = User(username="emp", email="emp@gatim.com", department=dept, role="employee")
    emp.set_password("pass")
    
    mgr = User(username="mgr", email="mgr@gatim.com", department=dept, role="inventory_manager")
    mgr.set_password("pass")
    
    item = InventoryItem(name="Desk", sku="DSK-01", quantity=5, critical_level=1, category=cat)
    db_session.add_all([emp, mgr, item])
    db_session.commit()

    # Create request
    req = InventoryRequest(requester=emp, item=item, quantity=3, status="pending")
    db_session.add(req)
    db_session.commit()

    # 1. Rejecting requires role 'inventory_manager' or 'admin'
    # Try with employee session first
    client.post("/auth/login", data={"username": "emp", "password": "pass"})
    response = client.post(f"/requests/{req.id}/approve")
    assert response.status_code == 403
    
    client.get("/auth/logout")

    # Log in as manager
    client.post("/auth/login", data={"username": "mgr", "password": "pass"})
    
    # Approve request (does NOT deduct stock)
    response = client.post(f"/requests/{req.id}/approve", follow_redirects=True)
    assert response.status_code == 200
    assert req.status == "approved"
    assert item.quantity == 5 # Stock unchanged

    # Deliver request (deducts stock)
    response = client.post(f"/requests/{req.id}/deliver", follow_redirects=True)
    assert response.status_code == 200
    assert req.status == "delivered"
    assert item.quantity == 2 # 5 - 3 = 2

    # Verify logs exist for transitions
    log_app = db_session.query(RequestLog).filter_by(request_id=req.id, status_to="approved").first()
    assert log_app is not None
    
    log_del = db_session.query(RequestLog).filter_by(request_id=req.id, status_to="delivered").first()
    assert log_del is not None

def test_request_cancellation(client, db_session):
    """Verify cancellation permissions and state conditions."""
    dept = db_session.query(Department).first()
    cat = db_session.query(Category).first()
    
    emp1 = User(username="emp1", email="emp1@gatim.com", department=dept, role="employee")
    emp1.set_password("pass")
    
    emp2 = User(username="emp2", email="emp2@gatim.com", department=dept, role="employee")
    emp2.set_password("pass")
    
    item = InventoryItem(name="Chair", sku="CHR-01", quantity=10, critical_level=1, category=cat)
    db_session.add_all([emp1, emp2, item])
    db_session.commit()

    # Emp1 request
    req1 = InventoryRequest(requester=emp1, item=item, quantity=2, status="pending")
    db_session.add(req1)
    db_session.commit()

    # Login as Emp2
    client.post("/auth/login", data={"username": "emp2", "password": "pass"})
    
    # Attempting to cancel Emp1 request -> 403 Forbidden
    response = client.post(f"/requests/{req1.id}/cancel")
    assert response.status_code == 403
    
    client.get("/auth/logout")

    # Login as Emp1
    client.post("/auth/login", data={"username": "emp1", "password": "pass"})
    
    # Cancel own pending request -> Success (Transitions to rejected/cancelled)
    response = client.post(f"/requests/{req1.id}/cancel", follow_redirects=True)
    assert response.status_code == 200
    assert req1.status == "rejected"
    
    # Verify cancellation log note
    log = db_session.query(RequestLog).filter_by(request_id=req1.id, status_to="rejected").first()
    assert log is not None
    assert log.remarks == "Kullanıcı tarafından iptal edildi."
