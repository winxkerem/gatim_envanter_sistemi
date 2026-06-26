from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.requests import requests_bp
from app.requests.forms import RequestForm, RejectForm
from app.models import db, InventoryItem, InventoryRequest, RequestLog
from app.auth.decorators import role_required

@requests_bp.route("/create/<int:item_id>", methods=["GET", "POST"])
@login_required
def create(item_id: int):
    """Create a new inventory request for an item."""
    item = db.get_or_404(InventoryItem, item_id)
    form = RequestForm()
    
    if form.validate_on_submit():
        qty = form.quantity.data
        
        # Instantiate request with initial status 'pending'
        req = InventoryRequest(
            requester_id=current_user.id,
            item_id=item.id,
            quantity=qty,
            status="pending"
        )
        db.session.add(req)
        
        # Log the initial creation event in the RequestLog table
        log = RequestLog(
            request=req,
            status_from=None,
            status_to="pending",
            changed_by_id=current_user.id,
            remarks="Talep oluşturuldu."
        )
        db.session.add(log)
        
        # Flash warning if requested quantity exceeds current inventory stock
        if qty > item.quantity:
            flash(
                f"Uyarı: Talep ettiğiniz miktar ({qty}), mevcut envanter stok adedinden ({item.quantity}) fazladır. "
                "Talebiniz yine de beklemede (pending) olarak oluşturuldu.", 
                "warning"
            )
        else:
            flash("Talebiniz başarıyla oluşturuldu ve onay bekliyor.", "success")
            
        db.session.commit()
        return redirect(url_for("requests.my_requests"))
        
    return render_template("requests/create.html", form=form, item=item)

@requests_bp.route("/my")
@login_required
def my_requests():
    """List of requests belonging to the current user."""
    reqs = db.session.query(InventoryRequest)\
        .filter_by(requester_id=current_user.id)\
        .order_by(InventoryRequest.created_at.desc()).all()
    return render_template("requests/my.html", requests=reqs)

@requests_bp.route("/all")
@login_required
@role_required("admin", "inventory_manager")
def all_requests():
    """List of all requests in the system (restricted to admin & inventory_manager)."""
    reqs = db.session.query(InventoryRequest)\
        .order_by(InventoryRequest.created_at.desc()).all()
    return render_template("requests/all.html", requests=reqs)

@requests_bp.route("/<int:req_id>/approve", methods=["POST"])
@login_required
@role_required("admin", "inventory_manager")
def approve(req_id: int):
    """Approve a request. Crucially, stock level is NOT reduced here."""
    req = db.get_or_404(InventoryRequest, req_id)
    try:
        req.transition_to("approved", changed_by_id=current_user.id, remarks="Talep onaylandı.")
        db.session.commit()
        flash("Talep onaylandı. Teslimat için bekliyor.", "success")
    except ValueError as e:
        db.session.rollback()
        flash(str(e), "danger")
        
    return redirect(request.referrer or url_for("requests.all_requests"))

@requests_bp.route("/<int:req_id>/reject", methods=["GET", "POST"])
@login_required
@role_required("admin", "inventory_manager")
def reject(req_id: int):
    """Reject a request. Requires a manager note."""
    req = db.get_or_404(InventoryRequest, req_id)
    form = RejectForm()
    
    if form.validate_on_submit():
        try:
            req.transition_to(
                "rejected", 
                changed_by_id=current_user.id, 
                remarks=form.remarks.data
            )
            db.session.commit()
            flash("Talep reddedildi.", "info")
            return redirect(url_for("requests.all_requests"))
        except ValueError as e:
            db.session.rollback()
            flash(str(e), "danger")
            return redirect(url_for("requests.all_requests"))
            
    return render_template("requests/reject.html", form=form, request_obj=req)

@requests_bp.route("/<int:req_id>/deliver", methods=["POST"])
@login_required
@role_required("admin", "inventory_manager")
def deliver(req_id: int):
    """Deliver the item physically and perform the actual stock deduction."""
    req = db.get_or_404(InventoryRequest, req_id)
    try:
        req.transition_to("delivered", changed_by_id=current_user.id, remarks="Malzeme fiziksel olarak teslim edildi.")
        db.session.commit()
        flash("Malzeme başarıyla teslim edildi ve stoktan düşüldü.", "success")
    except ValueError as e:
        db.session.rollback()
        flash(str(e), "danger")
        
    return redirect(request.referrer or url_for("requests.all_requests"))

@requests_bp.route("/<int:req_id>/cancel", methods=["POST"])
@login_required
def cancel(req_id: int):
    """Cancel a request. Users can only cancel their own pending requests."""
    req = db.get_or_404(InventoryRequest, req_id)
    
    # Restrict users to cancelling their own requests
    if req.requester_id != current_user.id:
        abort(403)
        
    # Only pending requests can be cancelled
    if req.status != "pending":
        flash("Sadece onay bekleyen (pending) taleplerinizi iptal edebilirsiniz.", "warning")
        return redirect(url_for("requests.my_requests"))
        
    try:
        req.transition_to(
            "rejected", 
            changed_by_id=current_user.id, 
            remarks="Kullanıcı tarafından iptal edildi."
        )
        db.session.commit()
        flash("Talebiniz iptal edildi.", "info")
    except ValueError as e:
        db.session.rollback()
        flash(str(e), "danger")
        
    return redirect(url_for("requests.my_requests"))
