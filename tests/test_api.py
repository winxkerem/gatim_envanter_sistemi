import pytest
from app import create_app
from app.models import db, User, Department, Category, InventoryItem, InventoryRequest
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
        dept = Department(name="IT")
        cat = Category(name="Hardware")
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

def test_api_v1_items_endpoint(client, db_session):
    """Verify GET /api/v1/items returns correct data structures and requires authentication."""
    # 1. Accessing unauthenticated -> redirect to login (302)
    response = client.get("/api/v1/items")
    assert response.status_code == 302

    # Setup user
    dept = db_session.query(Department).first()
    cat = db_session.query(Category).first()
    
    user = User(username="user1", email="user1@gatim.com", department=dept, role="user")
    user.set_password("pass")
    
    # Setup inventory items
    item1 = InventoryItem(name="Desktop Computer", sku="DESK-01", quantity=10, critical_level=2, category=cat)
    item2 = InventoryItem(name="Server Rack", sku="SRV-01", quantity=1, critical_level=3, category=cat)
    db_session.add_all([user, item1, item2])
    db_session.commit()


    # Log in
    client.post("/auth/login", data={"username": "user1", "password": "pass"})

    # 2. Accessing authenticated -> 200 JSON payload
    response = client.get("/api/v1/items")
    assert response.status_code == 200
    json_data = response.get_json()
    
    assert len(json_data) == 2
    # Check item details structure
    desktop = next(x for x in json_data if x["sku"] == "DESK-01")
    assert desktop["name"] == "Desktop Computer"
    assert desktop["category"] == "Hardware"
    assert desktop["quantity"] == 10
    assert desktop["critical_stock_level"] == 2
    assert desktop["is_critical"] is False

    server = next(x for x in json_data if x["sku"] == "SRV-01")
    assert server["is_critical"] is True
    
    # Verify no password hashes or user details are present in JSON response
    for entry in json_data:
        assert "password_hash" not in entry
        assert "email" not in entry

def test_api_v1_requests_my_endpoint(client, db_session):
    """Verify GET /api/v1/requests/my returns current logged-in user requests."""
    dept = db_session.query(Department).first()
    cat = db_session.query(Category).first()
    
    user = User(username="user_api", email="uapi@gatim.com", department=dept, role="user")
    user.set_password("pass")
    
    item = InventoryItem(name="Laptop Adapter", sku="ADP-01", quantity=5, critical_level=1, category=cat)
    db_session.add_all([user, item])
    db_session.commit()


    # Create request
    req = InventoryRequest(requester=user, item=item, quantity=2, status="pending")
    db_session.add(req)
    db_session.commit()

    # Log in
    client.post("/auth/login", data={"username": "user_api", "password": "pass"})

    response = client.get("/api/v1/requests/my")
    assert response.status_code == 200
    json_data = response.get_json()
    
    assert len(json_data) == 1
    my_req = json_data[0]
    assert my_req["item_name"] == "Laptop Adapter"
    assert my_req["item_sku"] == "ADP-01"
    assert my_req["quantity"] == 2
    assert my_req["status"] == "pending"
