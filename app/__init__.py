from flask import Flask, render_template
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from config import Config
from app.models import db, User, Department, Category, InventoryItem, InventoryRequest, RequestLog

# Instantiate Flask extensions (excluding SQLAlchemy, which is defined in models.py)
login_manager = LoginManager()
csrf = CSRFProtect()
migrate = Migrate()

def create_app(config_class=Config) -> Flask:
    """Application factory for the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Bind extensions to the app instance
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    
    # Configure Flask-Login parameters
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Bu sayfaya erişmek için lütfen giriş yapın."
    login_manager.login_message_category = "info"
    
    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        """User loader callback for Flask-Login."""
        return db.session.get(User, int(user_id))
        
    # Register application blueprints
    from app.auth import auth_bp
    from app.main import main_bp
    from app.inventory import inventory_bp
    from app.requests import requests_bp
    from app.admin import admin_bp
    from app.api import api_bp
    
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(main_bp, url_prefix="")
    app.register_blueprint(inventory_bp, url_prefix="/inventory")
    app.register_blueprint(requests_bp, url_prefix="/requests")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")
    
    # Context processor to inject system branding parameters
    @app.context_processor
    def inject_branding():
        return {
            "SYSTEM_TITLE": app.config.get("SYSTEM_TITLE"),
            "INSTITUTION_NAME": app.config.get("INSTITUTION_NAME")
        }

    # Custom Error Handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        db.session.rollback()
        return render_template("errors/500.html"), 500


    # Register custom Flask CLI commands
    import click
    from flask.cli import with_appcontext

    @app.cli.command("seed-db")
    @with_appcontext
    def seed_db():
        """Seeds the database with GATİM corporate data."""
        click.echo("Seeding database...")
        
        # 1. Departments
        depts_data = [
            "Yazılım Geliştirme ve Ar-Ge",
            "Siber Güvenlik ve Ağ Yönetimi",
            "Donanım Destek ve Teknik Servis",
            "İdari İşler ve Lojistik"
        ]
        departments = {}
        for d_name in depts_data:
            dept = db.session.query(Department).filter_by(name=d_name).first()
            if not dept:
                dept = Department(name=d_name)
                db.session.add(dept)
            departments[d_name] = dept
        
        db.session.flush()

        # 2. Categories
        cats_data = [
            "Geliştirici Ekipmanları",
            "Ağ ve Altyapı Bileşenleri",
            "Ofis ve Sarf Malzemeleri"
        ]
        categories = {}
        for c_name in cats_data:
            cat = db.session.query(Category).filter_by(name=c_name).first()
            if not cat:
                cat = Category(name=c_name)
                db.session.add(cat)
            categories[c_name] = cat
            
        db.session.flush()

        # 3. Inventory Items
        items_data = [
            ("24\" Oyuncu Monitörü", "MON-24-PLAY", 1, 3, "Geliştirici Ekipmanları"),
            ("Yazılımcı Mekanik Klavyesi (RGB)", "KEY-MECH-RGB", 15, 5, "Geliştirici Ekipmanları"),
            ("CAT6 Ağ Kablosu (100m)", "CAB-CAT6-100", 8, 2, "Ağ ve Altyapı Bileşenleri"),
            ("A4 Fotokopi Kağıdı (5'li Paket)", "PAP-A4-5PACK", 40, 10, "Ofis ve Sarf Malzemeleri")
        ]
        for name, sku, quantity, critical_level, cat_name in items_data:
            item = db.session.query(InventoryItem).filter_by(sku=sku).first()
            if not item:
                item = InventoryItem(
                    name=name,
                    sku=sku,
                    quantity=quantity,
                    critical_level=critical_level,
                    category=categories[cat_name]
                )
                db.session.add(item)

        # 4. Users
        users_data = [
            ("admin_kerem", "admin_kerem@gatim.com", "Admin123*", "admin", "Yazılım Geliştirme ve Ar-Ge"),
            ("sorumlu_ahmet", "sorumlu_ahmet@gatim.com", "Manager123*", "inventory_manager", "Donanım Destek ve Teknik Servis"),
            ("personel_mehmet", "personel_mehmet@gatim.com", "User123*", "user", "Siber Güvenlik ve Ağ Yönetimi")
        ]
        for username, email, password, role, dept_name in users_data:
            user = db.session.query(User).filter_by(username=username).first()
            if not user:
                user = User(
                    username=username,
                    email=email,
                    role=role,
                    department=departments[dept_name]
                )
                user.set_password(password)
                db.session.add(user)

        try:
            db.session.commit()
            click.echo("Database successfully seeded with GATİM corporate data!")
        except Exception as e:
            db.session.rollback()
            click.echo(f"Seeding failed: {str(e)}")
    
    return app

