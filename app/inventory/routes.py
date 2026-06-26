from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.inventory import inventory_bp
from app.inventory.forms import InventoryItemForm
from app.models import db, InventoryItem, Category
from app.auth.decorators import role_required

@inventory_bp.route("/")
@login_required
def index():
    """List inventory items with search, category filter, and stock status filters."""
    page = request.args.get("page", 1, type=int)
    search_query = request.args.get("q", "").strip()
    category_id = request.args.get("category_id", type=int)
    stock_status = request.args.get("stock_status", "all")

    # Construct the query dynamically using SQLAlchemy select
    stmt = db.select(InventoryItem)

    if search_query:
        stmt = stmt.filter(
            (InventoryItem.name.ilike(f"%{search_query}%")) | 
            (InventoryItem.sku.ilike(f"%{search_query}%"))
        )
        
    if category_id:
        stmt = stmt.filter(InventoryItem.category_id == category_id)

    if stock_status == "critical":
        stmt = stmt.filter(InventoryItem.quantity <= InventoryItem.critical_level)

    # Sort alphabetically by name
    stmt = stmt.order_by(InventoryItem.name)

    # Apply Flask-SQLAlchemy 3.x pagination
    pagination = db.paginate(stmt, page=page, per_page=10, error_out=False)
    
    # Get all categories for filter dropdown
    categories = db.session.query(Category).order_by(Category.name).all()

    return render_template(
        "inventory/list.html",
        pagination=pagination,
        categories=categories,
        search_query=search_query,
        selected_category=category_id,
        stock_status=stock_status
    )

@inventory_bp.route("/<int:item_id>")
@login_required
def detail(item_id: int):
    """View details of a specific inventory item."""
    item = db.get_or_404(InventoryItem, item_id)
    return render_template("inventory/detail.html", item=item)

@inventory_bp.route("/add", methods=["GET", "POST"])
@login_required
@role_required("admin", "inventory_manager")
def add():
    """Add a new item to the inventory (restricted to admin & inventory_manager)."""
    form = InventoryItemForm()
    # Populate category dropdown choices dynamically
    form.category_id.choices = [
        (c.id, c.name) for c in db.session.query(Category).order_by(Category.name).all()
    ]

    if form.validate_on_submit():
        item = InventoryItem(
            name=form.name.data,
            sku=form.sku.data,
            quantity=form.quantity.data,
            critical_level=form.critical_level.data,
            category_id=form.category_id.data
        )
        db.session.add(item)
        db.session.commit()
        flash(f"'{item.name}' envantere başarıyla eklendi.", "success")
        return redirect(url_for("inventory.index"))

    return render_template("inventory/add_edit.html", form=form, title="Yeni Malzeme Ekle")

@inventory_bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin", "inventory_manager")
def edit(item_id: int):
    """Edit an existing inventory item (restricted to admin & inventory_manager)."""
    item = db.get_or_404(InventoryItem, item_id)
    
    # Instantiate form passing original SKU to skip self-uniqueness validation
    form = InventoryItemForm(original_sku=item.sku)
    form.category_id.choices = [
        (c.id, c.name) for c in db.session.query(Category).order_by(Category.name).all()
    ]

    if form.validate_on_submit():
        item.name = form.name.data
        item.sku = form.sku.data
        item.quantity = form.quantity.data
        item.critical_level = form.critical_level.data
        item.category_id = form.category_id.data
        
        db.session.commit()
        flash(f"'{item.name}' başarıyla güncellendi.", "success")
        return redirect(url_for("inventory.detail", item_id=item.id))
        
    elif request.method == "GET":
        # Pre-populate form fields
        form.name.data = item.name
        form.sku.data = item.sku
        form.quantity.data = item.quantity
        form.critical_level.data = item.critical_level
        form.category_id.data = item.category_id

    return render_template("inventory/add_edit.html", form=form, title="Malzeme Düzenle", item=item)
