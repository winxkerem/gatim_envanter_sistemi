import pytest
from app import create_app
from app.models import db, User, Department, Category, InventoryItem
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
        cat1 = Category(name="Electronics")
        cat2 = Category(name="Office Supplies")
        db.session.add_all([dept, cat1, cat2])
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

def test_inventory_list_access_and_filters(client, db_session):
    """Verify that the inventory listing is accessible and responds to search/category filters."""
    # 1. Login user
    dept = db_session.query(Department).first()
    user = User(username="employee", email="employee@gatim.com", department=dept, role="user")
    user.set_password("pass")
    db_session.add(user)
    
    # Seed items
    cat1 = db_session.query(Category).filter_by(name="Electronics").first()
    cat2 = db_session.query(Category).filter_by(name="Office Supplies").first()
    item1 = InventoryItem(name="Dell Monitor", sku="DEL-001", quantity=10, critical_level=2, category=cat1)
    item2 = InventoryItem(name="A4 Paper Pack", sku="PAP-001", quantity=2, critical_level=5, category=cat2)  # Critical stock item
    db_session.add_all([item1, item2])
    db_session.commit()
    
    # Access without login -> redirect/401
    response = client.get("/inventory/")
    assert response.status_code == 302  # redirects to login view

    # Log in
    client.post("/auth/login", data={"username": "employee", "password": "pass"})
    
    # 2. Check full listing
    response = client.get("/inventory/")
    assert response.status_code == 200
    assert b"Dell Monitor" in response.data
    assert b"A4 Paper Pack" in response.data
    
    # 3. Check search query filter
    response = client.get("/inventory/?q=Dell")
    assert b"Dell Monitor" in response.data
    assert b"A4 Paper Pack" not in response.data
    
    # 4. Check category filter
    response = client.get(f"/inventory/?category_id={cat2.id}")
    assert b"A4 Paper Pack" in response.data
    assert b"Dell Monitor" not in response.data
    
    # 5. Check critical stock level filter
    response = client.get("/inventory/?stock_status=critical")
    assert b"A4 Paper Pack" in response.data
    assert b"Dell Monitor" not in response.data

def test_inventory_item_details(client, db_session):
    """Verify that item detail page is served correctly."""
    dept = db_session.query(Department).first()
    cat = db_session.query(Category).first()
    
    user = User(username="employee2", email="employee2@gatim.com", department=dept, role="user")
    user.set_password("pass")
    item = InventoryItem(name="Keyboard", sku="KEY-002", quantity=15, critical_level=3, category=cat)
    
    db_session.add_all([user, item])
    db_session.commit()

    
    client.post("/auth/login", data={"username": "employee2", "password": "pass"})
    
    # Valid item ID
    response = client.get(f"/inventory/{item.id}")
    assert response.status_code == 200
    assert b"Keyboard" in response.data
    assert b"KEY-002" in response.data
    
    # Invalid item ID -> 404
    response = client.get("/inventory/9999")
    assert response.status_code == 404

def test_inventory_add_edit_access_controls(client, db_session):
    """Verify that only admins/managers can create or modify inventory items."""
    dept = db_session.query(Department).first()
    cat = db_session.query(Category).first()
    
    # Roles
    emp = User(username="emp", email="emp@gatim.com", department=dept, role="employee")
    emp.set_password("pass")
    
    mgr = User(username="mgr", email="mgr@gatim.com", department=dept, role="inventory_manager")
    mgr.set_password("pass")
    
    db_session.add_all([emp, mgr])
    db_session.commit()
    
    # 1. Test employee (role 'employee') -> should get 403 on add & edit
    client.post("/auth/login", data={"username": "emp", "password": "pass"})
    
    response = client.get("/inventory/add")
    assert response.status_code == 403
    
    # Seed an item to attempt editing
    item = InventoryItem(name="Mouse", sku="MOU-003", quantity=20, critical_level=5, category=cat)
    db_session.add(item)
    db_session.commit()
    
    response = client.get(f"/inventory/{item.id}/edit")
    assert response.status_code == 403
    
    client.get("/auth/logout")

    # 2. Test inventory manager -> should get 200/302 on add & edit
    client.post("/auth/login", data={"username": "mgr", "password": "pass"})
    
    # Load add form
    response = client.get("/inventory/add")
    assert response.status_code == 200
    
    # Submit add form successfully
    response = client.post("/inventory/add", data={
        "name": "Tablet",
        "sku": "TAB-004",
        "category_id": cat.id,
        "quantity": 12,
        "critical_level": 4
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Tablet" in response.data
    
    # Load edit form
    response = client.get(f"/inventory/{item.id}/edit")
    assert response.status_code == 200
    
    # Submit edit form successfully (changing stock count)
    response = client.post(f"/inventory/{item.id}/edit", data={
        "name": "Mouse - Wireless",
        "sku": "MOU-003", # keep same SKU
        "category_id": cat.id,
        "quantity": 25,   # update stock
        "critical_level": 5
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Mouse - Wireless" in response.data
    
    # Verify DB state
    db_session.refresh(item)
    assert item.name == "Mouse - Wireless"
    assert item.quantity == 25
