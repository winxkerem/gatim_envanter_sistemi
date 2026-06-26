from flask import jsonify
from flask_login import login_required, current_user
from app.api import api_bp
from app.models import db, InventoryItem, InventoryRequest

@api_bp.route("/v1/items", methods=["GET"])
@login_required
def get_items():
    """API endpoint to get list of all inventory items in JSON format."""
    items = db.session.query(InventoryItem).order_by(InventoryItem.name).all()
    result = [
        {
            "id": item.id,
            "name": item.name,
            "sku": item.sku,
            "category": item.category.name,
            "quantity": item.quantity,
            "critical_stock_level": item.critical_level,
            "is_critical": item.is_critical
        }
        for item in items
    ]
    return jsonify(result)

@api_bp.route("/v1/requests/my", methods=["GET"])
@login_required
def get_my_requests():
    """API endpoint to get list of requests for the logged-in user in JSON format."""
    requests = db.session.query(InventoryRequest)\
        .filter_by(requester_id=current_user.id)\
        .order_by(InventoryRequest.created_at.desc()).all()
    result = [
        {
            "id": req.id,
            "item_id": req.item_id,
            "item_name": req.item.name,
            "item_sku": req.item.sku,
            "quantity": req.quantity,
            "status": req.status,
            "created_at": req.created_at.isoformat(),
            "updated_at": req.updated_at.isoformat()
        }
        for req in requests
    ]
    return jsonify(result)
