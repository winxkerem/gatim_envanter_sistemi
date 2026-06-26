import pytest
from app import create_app
from app.models import db, User, Department, Category, InventoryItem, InventoryRequest, RequestLog
from config import Config

class TestConfig(Config):
    """Test configuration setting SQLite in memory and disabling CSRF."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False

@pytest.fixture
def app():
    """Setup app context and schema."""
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def db_session(app):
    """Provide db session object."""
    return db.session

def test_user_password_hashing(app, db_session):
    """Verify password hashing and check password mechanism."""
    user = User(username="testuser", email="test@gatim.com")
    user.set_password("securepassword")
    assert user.password_hash != "securepassword"
    assert user.check_password("securepassword") is True
    assert user.check_password("wrongpassword") is False

def test_department_relationship(app, db_session):
    """Verify users and departments relationship."""
    dept = Department(name="IT Department")
    user = User(username="it_user", email="it@gatim.com")
    user.set_password("pass")
    user.department = dept
    
    db_session.add_all([dept, user])
    db_session.commit()
    
    assert user.department_id == dept.id
    assert len(dept.users) == 1
    assert dept.users[0].username == "it_user"

def test_inventory_item_critical_level(app, db_session):
    """Verify is_critical property logic flag."""
    cat = Category(name="Electronics")
    item = InventoryItem(name="Laptop", sku="LAP-001", quantity=10, critical_level=5, category=cat)
    db_session.add_all([cat, item])
    db_session.commit()
    
    assert item.is_critical is False
    
    item.quantity = 4
    db_session.commit()
    assert item.is_critical is True

def test_physical_stock_deduction_flow(app, db_session):
    """Verify the physical stock deduction rules:
    - Status 'approved': stock remains unchanged.
    - Status 'delivered': stock is deducted.
    - Status transition logs are recorded.
    """
    dept = Department(name="R&D")
    requester = User(username="requester", email="req@gatim.com", department=dept)
    approver = User(username="approver", email="app@gatim.com", department=dept, role="manager")
    requester.set_password("pass")
    approver.set_password("pass")
    
    cat = Category(name="Office Supplies")
    item = InventoryItem(name="Notebook", sku="NOTE-001", quantity=20, critical_level=5, category=cat)
    
    db_session.add_all([dept, requester, approver, cat, item])
    db_session.commit()
    
    # Create request
    req = InventoryRequest(requester=requester, item=item, quantity=5, status="pending")
    db_session.add(req)
    db_session.commit()
    
    assert item.quantity == 20
    assert req.status == "pending"
    
    # Transition to 'approved'
    req.transition_to("approved", changed_by_id=approver.id, remarks="Request is valid")
    db_session.commit()
    
    assert req.status == "approved"
    assert item.quantity == 20  # CRITICAL: Stock does NOT change!
    
    # Verify transition log
    log_app = db_session.query(RequestLog).filter_by(status_to="approved").first()
    assert log_app is not None
    assert log_app.status_from == "pending"
    assert log_app.changed_by_id == approver.id
    
    # Transition to 'delivered'
    req.transition_to("delivered", changed_by_id=approver.id, remarks="Physical hand-off done")
    db_session.commit()
    
    assert req.status == "delivered"
    assert item.quantity == 15  # CRITICAL: Stock is deducted!
    
    # Verify transition log
    log_del = db_session.query(RequestLog).filter_by(status_to="delivered").first()
    assert log_del is not None
    assert log_del.status_from == "approved"
    assert log_del.changed_by_id == approver.id

def test_insufficient_stock_failure(app, db_session):
    """Verify that delivering a request with insufficient stock fails."""
    dept = Department(name="Sales")
    requester = User(username="requester2", email="req2@gatim.com", department=dept)
    approver = User(username="approver2", email="app2@gatim.com", department=dept, role="manager")
    requester.set_password("pass")
    approver.set_password("pass")
    
    cat = Category(name="Hardware")
    item = InventoryItem(name="Monitor", sku="MON-001", quantity=3, critical_level=1, category=cat)
    
    db_session.add_all([dept, requester, approver, cat, item])
    db_session.commit()
    
    # Requesting 5 monitors (Only 3 in stock)
    req = InventoryRequest(requester=requester, item=item, quantity=5, status="pending")
    db_session.add(req)
    db_session.commit()
    
    # Can approve
    req.transition_to("approved", changed_by_id=approver.id)
    db_session.commit()
    assert req.status == "approved"
    assert item.quantity == 3
    
    # Transition to delivered must raise ValueError
    with pytest.raises(ValueError, match="Insufficient stock"):
        req.transition_to("delivered", changed_by_id=approver.id)
        
    assert req.status == "approved"
    assert item.quantity == 3

def test_negative_quantity_constraints(app, db_session):
    """Verify database constraints block invalid quantities."""
    cat = Category(name="Tools")
    item = InventoryItem(name="Hammer", sku="HAM-001", quantity=-1, category=cat)
    db_session.add_all([cat, item])
    
    # DB integrity check constraint should trigger failure on commit
    with pytest.raises(Exception):
        db_session.commit()
    db_session.rollback()
    db_session.remove()
    
    # Get a fresh session reference
    db_session = db.session

    cat = Category(name="Tools")
    dept = Department(name="Operations")
    user = User(username="user3", email="user3@gatim.com", department=dept)
    user.set_password("pass")
    item2 = InventoryItem(name="Screwdriver", sku="SCR-001", quantity=10, category=cat)
    db_session.add_all([dept, user, item2])
    db_session.commit()
    
    # Request cannot have quantity <= 0
    req = InventoryRequest(requester=user, item=item2, quantity=0)
    db_session.add(req)
    with pytest.raises(Exception):
        db_session.commit()
    db_session.rollback()
    db_session.remove()

