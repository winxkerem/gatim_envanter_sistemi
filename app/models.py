from datetime import datetime
from typing import List, Optional
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey, String, Integer, Text, DateTime, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

# Initialize Flask-SQLAlchemy db object (will be bound via app factory)
db = SQLAlchemy()

class Department(db.Model):
    """Department model grouping Users within the organization."""
    __tablename__ = "departments"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    
    # Relationships
    users: Mapped[List["User"]] = relationship("User", back_populates="department")

    def __repr__(self) -> str:
        return f"<Department {self.name}>"


class User(UserMixin, db.Model):
    """User model representing employees, managers, and admins of GATİM."""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="employee")  # e.g., admin, manager, employee
    department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id"), nullable=True)
    
    # Relationships
    department: Mapped[Optional[Department]] = relationship("Department", back_populates="users")
    requests: Mapped[List["InventoryRequest"]] = relationship(
        "InventoryRequest", 
        back_populates="requester", 
        foreign_keys="[InventoryRequest.requester_id]"
    )
    logs: Mapped[List["RequestLog"]] = relationship("RequestLog", back_populates="changed_by")

    def set_password(self, password: str) -> None:
        """Hash and set the user password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify the password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.username}>"


class Category(db.Model):
    """Category classification for inventory items."""
    __tablename__ = "categories"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    items: Mapped[List["InventoryItem"]] = relationship("InventoryItem", back_populates="category")

    def __repr__(self) -> str:
        return f"<Category {self.name}>"


class InventoryItem(db.Model):
    """Inventory Item tracking item quantities, details, and warning levels."""
    __tablename__ = "inventory_items"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="chk_inventory_item_quantity"),
        CheckConstraint("critical_level >= 0", name="chk_inventory_item_critical_level"),
    )
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    critical_level: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    
    # Relationships
    category: Mapped[Category] = relationship("Category", back_populates="items")
    requests: Mapped[List["InventoryRequest"]] = relationship("InventoryRequest", back_populates="item")

    @property
    def is_critical(self) -> bool:
        """Flags when stock level is at or below the warning threshold."""
        return self.quantity <= self.critical_level

    def __repr__(self) -> str:
        return f"<InventoryItem {self.name} (SKU: {self.sku}) Quantity: {self.quantity}>"


class InventoryRequest(db.Model):
    """Inventory request filed by Users for items."""
    __tablename__ = "inventory_requests"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="chk_inventory_request_quantity"),
    )
    
    id: Mapped[int] = mapped_column(primary_key=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    item_id: Mapped[int] = mapped_column(ForeignKey("inventory_items.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)  # pending, approved, delivered, rejected
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    requester: Mapped[User] = relationship("User", back_populates="requests", foreign_keys=[requester_id])
    item: Mapped[InventoryItem] = relationship("InventoryItem", back_populates="requests")
    logs: Mapped[List["RequestLog"]] = relationship("RequestLog", back_populates="request", cascade="all, delete-orphan")

    def transition_to(self, new_status: str, changed_by_id: int, remarks: Optional[str] = None) -> None:
        """
        Safely transitions the request status.
        CRITICAL Business Rule: Stock quantity reduction MUST occur ONLY when the status transitions to 'delivered'.
        Approving the request does NOT affect the stock levels.
        """
        if self.status == new_status:
            return
            
        allowed_statuses = {"pending", "approved", "delivered", "rejected"}
        if new_status not in allowed_statuses:
            raise ValueError(f"Invalid request status: {new_status}")
            
        # Prevent updates to already delivered requests
        if self.status == "delivered":
            raise ValueError("Cannot transition a request that has already been delivered.")

        # Deduct stock only on delivery
        if new_status == "delivered":
            if self.item.quantity < self.quantity:
                raise ValueError(
                    f"Insufficient stock for '{self.item.name}' (SKU: {self.item.sku}). "
                    f"Required: {self.quantity}, Available: {self.item.quantity}."
                )
            self.item.quantity -= self.quantity

        old_status = self.status
        self.status = new_status
        
        # Log the transition
        log = RequestLog(
            request=self,
            status_from=old_status,
            status_to=new_status,
            changed_by_id=changed_by_id,
            remarks=remarks
        )
        db.session.add(log)

    def __repr__(self) -> str:
        return f"<InventoryRequest ID: {self.id} Status: {self.status} Quantity: {self.quantity}>"


class RequestLog(db.Model):
    """Audit log tracking history of states for a request."""
    __tablename__ = "request_logs"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("inventory_requests.id"), nullable=False)
    status_from: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    status_to: Mapped[str] = mapped_column(String(20), nullable=False)
    changed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    request: Mapped[InventoryRequest] = relationship("InventoryRequest", back_populates="logs")
    changed_by: Mapped[User] = relationship("User", back_populates="logs")

    def __repr__(self) -> str:
        return f"<RequestLog Request ID: {self.request_id} {self.status_from} -> {self.status_to}>"
