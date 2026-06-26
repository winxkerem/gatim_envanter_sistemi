import pytest
from app.models import db, User, Department, Category, InventoryItem, InventoryRequest, RequestLog

def test_user_registration(client, db_session):
    """Test 1: User Registration Test (Can a user register successfully?)"""
    dept = db_session.query(Department).filter_by(name="Yazılım Geliştirme").first()
    
    response = client.post("/auth/register", data={
        "username": "user_reg",
        "email": "reg@gatim.com",
        "department_id": dept.id,
        "password": "Password123*",
        "confirm_password": "Password123*"
    }, follow_redirects=True)
    
    assert response.status_code == 200
    
    user = db_session.query(User).filter_by(username="user_reg").first()
    assert user is not None
    assert user.email == "reg@gatim.com"
    assert user.role == "employee"

def test_password_hash(db_session):
    """Test 2: Password Hash Test (Verify plain text password is not stored)"""
    dept = db_session.query(Department).first()
    
    user = User(username="user_hash", email="hash@gatim.com", department=dept)
    user.set_password("Secret123*")
    db_session.add(user)
    db_session.commit()
    
    assert user.password_hash != "Secret123*"
    assert user.check_password("Secret123*") is True
    assert user.check_password("wrong") is False

def test_user_login(client, db_session):
    """Test 3: User Login Test (Successful authentication with correct credentials)"""
    dept = db_session.query(Department).first()
    user = User(username="user_log", email="log@gatim.com", department=dept)
    user.set_password("Log123*")
    db_session.add(user)
    db_session.commit()
    
    response = client.post("/auth/login", data={
        "username": "user_log",
        "password": "Log123*"
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert "GATİM Sistem Özeti" in response.data.decode("utf-8")

def test_unauthorized_access(client, db_session):
    """Test 4: Unauthorized Access Test (Normal user blocked from admin routes, returning 403)"""
    dept = db_session.query(Department).first()
    user = User(username="user_unauth", email="unauth@gatim.com", department=dept, role="employee")
    user.set_password("pass")
    db_session.add(user)
    db_session.commit()
    
    client.post("/auth/login", data={"username": "user_unauth", "password": "pass"})
    
    # Attempting to access admin users page must yield 403 Forbidden
    response = client.get("/admin/users")
    assert response.status_code == 403
    assert "Erişim Engellendi" in response.data.decode("utf-8")

def test_item_creation(client, db_session):
    """Test 5: Item Creation Test (Authorized manager/admin can add inventory)"""
    dept = db_session.query(Department).first()
    admin = User(username="admin_user", email="admin@gatim.com", department=dept, role="admin")
    admin.set_password("pass")
    db_session.add(admin)
    db_session.commit()
    
    client.post("/auth/login", data={"username": "admin_user", "password": "pass"})
    
    cat = db_session.query(Category).first()
    response = client.post("/inventory/add", data={
        "name": "New Monitor",
        "sku": "MON-NEW-12",
        "category_id": cat.id,
        "quantity": 10,
        "critical_level": 3
    }, follow_redirects=True)
    
    assert response.status_code == 200
    item = db_session.query(InventoryItem).filter_by(sku="MON-NEW-12").first()
    assert item is not None
    assert item.name == "New Monitor"
    assert item.quantity == 10

def test_request_creation(client, db_session):
    """Test 6: Request Creation Test (User can successfully submit an inventory request)"""
    dept = db_session.query(Department).first()
    user = User(username="user_req", email="req@gatim.com", department=dept)
    user.set_password("pass")
    
def test_request_creation(client, db_session):
    """Test 6: Request Creation Test (User can successfully submit an inventory request)"""
    dept = db_session.query(Department).first()
    cat = db_session.query(Category).first()
    
    user = User(username="user_req", email="req@gatim.com", department=dept)
    user.set_password("pass")
    
    item = InventoryItem(name="Standard Keyboard", sku="KEY-STD-99", quantity=5, critical_level=1, category=cat)
    db_session.add_all([user, item])
    db_session.commit()
    
    client.post("/auth/login", data={"username": "user_req", "password": "pass"})
    
    response = client.post(f"/requests/create/{item.id}", data={"quantity": 3}, follow_redirects=True)
    assert response.status_code == 200
    
    req = db_session.query(InventoryRequest).filter_by(item_id=item.id, quantity=3).first()
    assert req is not None
    assert req.status == "pending"

def test_stock_control(client, db_session):
    """Test 7: Stock Control Test (Ensure request delivery fails if stock is insufficient)"""
    dept = db_session.query(Department).first()
    cat = db_session.query(Category).first()
    
    user = User(username="user_stock", email="stock@gatim.com", department=dept)
    user.set_password("pass")
    
    mgr = User(username="mgr_stock", email="mgr@gatim.com", department=dept, role="inventory_manager")
    mgr.set_password("pass")
    
    item = InventoryItem(name="Limited SSD", sku="SSD-LIM", quantity=2, critical_level=1, category=cat)
    db_session.add_all([user, mgr, item])
    db_session.commit()
    
    # Request 5 items (Stock is only 2)
    client.post("/auth/login", data={"username": "user_stock", "password": "pass"})
    client.post(f"/requests/create/{item.id}", data={"quantity": 5})
    client.get("/auth/logout")
    
    # Approve request
    client.post("/auth/login", data={"username": "mgr_stock", "password": "pass"})
    req = db_session.query(InventoryRequest).filter_by(item_id=item.id).first()
    client.post(f"/requests/{req.id}/approve")
    
    # Attempting to deliver SSD-LIM which has insufficient stock must fail
    response = client.post(f"/requests/{req.id}/deliver", follow_redirects=True)
    
    db_session.refresh(req)
    db_session.refresh(item)
    
    assert req.status == "approved"  # Remains approved, not delivered
    assert item.quantity == 2        # Stock unchanged
    assert "Insufficient stock" in response.data.decode("utf-8")

def test_audit_log(client, db_session):
    """Test 8: Audit Log Test (Verify a RequestLog entry is auto-generated upon status transition)"""
    dept = db_session.query(Department).first()
    cat = db_session.query(Category).first()
    
    user = User(username="user_audit", email="audit@gatim.com", department=dept)
    user.set_password("pass")
    
    mgr = User(username="mgr_audit", email="mgr_audit@gatim.com", department=dept, role="inventory_manager")
    mgr.set_password("pass")
    
    item = InventoryItem(name="Network Switch", sku="SW-NET", quantity=10, critical_level=2, category=cat)
    db_session.add_all([user, mgr, item])
    db_session.commit()
    
    req = InventoryRequest(requester=user, item=item, quantity=2, status="pending")
    db_session.add(req)
    db_session.commit()
    
    client.post("/auth/login", data={"username": "mgr_audit", "password": "pass"})
    client.post(f"/requests/{req.id}/approve")
    
    # Verify transition log entry auto-creation
    log = db_session.query(RequestLog).filter_by(request_id=req.id, status_to="approved").first()
    assert log is not None
    assert log.status_from == "pending"
    assert log.changed_by_id == mgr.id

