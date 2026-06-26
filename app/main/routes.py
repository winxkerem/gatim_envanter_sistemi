from flask import render_template
from flask_login import login_required, current_user
from app.main import main_bp
from app.models import db, InventoryItem, InventoryRequest, RequestLog

@main_bp.route("/")
@login_required
def index():
    """Application main dashboard view representing GATİM system metrics."""
    # Fetch summary analytics
    total_items = db.session.query(InventoryItem).count()
    
    # Filter critical items where quantity <= critical_level
    critical_items_count = db.session.query(InventoryItem).filter(
        InventoryItem.quantity <= InventoryItem.critical_level
    ).count()

    total_requests = db.session.query(InventoryRequest).count()
    pending_requests = db.session.query(InventoryRequest).filter_by(status="pending").count()
    approved_requests = db.session.query(InventoryRequest).filter_by(status="approved").count()
    delivered_requests = db.session.query(InventoryRequest).filter_by(status="delivered").count()

    # Query latest audit logs
    logs = db.session.query(RequestLog).order_by(RequestLog.timestamp.desc()).limit(5).all()

    # Render dashboard passing query metrics
    return render_template(
        "index.html",
        total_items=total_items,
        critical_items_count=critical_items_count,
        total_requests=total_requests,
        pending_requests=pending_requests,
        approved_requests=approved_requests,
        delivered_requests=delivered_requests,
        logs=logs
    )
