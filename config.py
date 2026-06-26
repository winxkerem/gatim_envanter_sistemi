import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

class Config:
    """Application configuration loader."""
    SECRET_KEY = os.getenv("SECRET_KEY", "gatim-secret-key-change-in-production-998877")
    
    # Base directory of the application
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    
    # Database config (defaults to SQLite in the workspace root if DATABASE_URL is not set)
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", 
        f"sqlite:///{os.path.join(BASE_DIR, 'gatim_inventory.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Custom Corporate Parameters
    SYSTEM_TITLE = "GATİM - Envanter ve Talep Takip Sistemi"
    INSTITUTION_NAME = "Gazi Teknoloji ve İnovasyon Merkezleri A.Ş. (GATİM)"
