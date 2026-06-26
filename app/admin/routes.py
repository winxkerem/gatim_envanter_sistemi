from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.admin import admin_bp
from app.models import db, User
from app.auth.decorators import role_required

@admin_bp.route("/users", methods=["GET"])
@login_required
@role_required("admin")
def list_users():
    """List all registered users in the system."""
    users = db.session.query(User).order_by(User.username).all()
    return render_template("admin/users.html", users=users)

@admin_bp.route("/users/<int:user_id>/update-role", methods=["POST"])
@login_required
@role_required("admin")
def update_role(user_id: int):
    """Update a user's organizational role."""
    user = db.get_or_404(User, user_id)
    new_role = request.form.get("role")
    
    allowed_roles = {"admin", "inventory_manager", "employee"}
    if new_role not in allowed_roles:
        flash("Geçersiz rol seçimi.", "danger")
        return redirect(url_for("admin.list_users"))
        
    # Security check: Prevent self-demotion
    if user.id == current_user.id:
        flash("Kendi rolünüzü değiştiremezsiniz.", "warning")
        return redirect(url_for("admin.list_users"))
        
    user.role = new_role
    db.session.commit()
    flash(f"'{user.username}' kullanıcısının rolü '{new_role}' olarak güncellendi.", "success")
    return redirect(url_for("admin.list_users"))
