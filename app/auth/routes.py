from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import auth_bp
from app.auth.forms import LoginForm, RegistrationForm
from app.models import db, User, Department

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """User registration view."""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
        
    form = RegistrationForm()
    # Dynamic population of department choices from database
    form.department_id.choices = [
        (d.id, d.name) for d in db.session.query(Department).order_by(Department.name).all()
    ]
    
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            department_id=form.department_id.data,
            role="employee"  # Default role for newly registered personnel
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Kayıt işleminiz başarıyla tamamlandı! Giriş yapabilirsiniz.", "success")
        return redirect(url_for("auth.login"))
        
    return render_template("auth/register.html", form=form)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """User login view."""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
        
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.query(User).filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            # Safety check redirect to target page or home page
            next_page = request.args.get("next")
            if not next_page or not next_page.startswith('/'):
                next_page = url_for("main.index")
            flash(f"Hoş geldiniz, {user.username}!", "success")
            return redirect(next_page)
        else:
            flash("Geçersiz kullanıcı adı veya şifre.", "danger")
            
    return render_template("auth/login.html", form=form)

@auth_bp.route("/logout")
@login_required
def logout():
    """User logout view."""
    logout_user()
    flash("Başarıyla çıkış yaptınız.", "info")
    return redirect(url_for("auth.login"))
