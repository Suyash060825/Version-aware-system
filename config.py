"""
config.py
All configuration in one place. Copy .env.example to .env and fill in values.
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # --- Core ---
    SECRET_KEY = os.environ.get("SECRET_KEY")
    DEBUG = False
    TESTING = False
    
    # --- RAG Guardrails ---
    PII_REDACTION_ENABLED = os.environ.get("PII_REDACTION_ENABLED", "True").lower() == "true"

    # --- Database ---
    _raw_db = os.environ.get("DATABASE_URL")
    if _raw_db and "@postgres:" in _raw_db:
        import socket
        try:
            socket.gethostbyname("postgres")
            SQLALCHEMY_DATABASE_URI = _raw_db
        except Exception:
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'data', 'ledger.db')}"
    elif _raw_db and not _raw_db.startswith("sqlite:///data/"):
        SQLALCHEMY_DATABASE_URI = _raw_db
    else:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'data', 'ledger.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- JWT ---
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)

    # --- File uploads ---
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "data", "uploads")
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024  # 32 MB
    ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md"}
    # Extensions accepted by the "Import policy from file" feature
    POLICY_IMPORT_EXTENSIONS = {"pdf", "docx", "xlsx", "xls", "txt", "md"}

    # --- Email (optional — notifications) ---
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@company.com")

    # --- App-level settings ---
    APP_NAME = os.environ.get("APP_NAME", "Policy Ledger")
    COMPANY_NAME = os.environ.get("COMPANY_NAME", "Your Company")
    DEFAULT_ADMIN_EMAIL = os.environ.get("DEFAULT_ADMIN_EMAIL", "admin@company.com")
    DEFAULT_ADMIN_PASSWORD = os.environ.get("DEFAULT_ADMIN_PASSWORD")

    # --- MFA ---
    MFA_ISSUER = os.environ.get("MFA_ISSUER", "PolicyLedger")


class DevelopmentConfig(Config):
    DEBUG = True
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-secret-key-12345")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-insecure-jwt-key-12345")
    DEFAULT_ADMIN_PASSWORD = os.environ.get("DEFAULT_ADMIN_PASSWORD", "DevAdmin#2026!")


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
    SESSION_COOKIE_SAMESITE = 'Lax'

    @classmethod
    def validate_production_secrets(cls):
        secret = os.environ.get("SECRET_KEY", "")
        jwt_secret = os.environ.get("JWT_SECRET_KEY", "")
        admin_pw = os.environ.get("DEFAULT_ADMIN_PASSWORD", "")
        insecure_defaults = {
            "change-this-in-production-please",
            "dev-secret-key",
            "dev-insecure-secret-key-12345",
            "dev-insecure-jwt-key-12345",
            "Admin@1234",
            "DevAdmin#2026!",
            ""
        }
        if not secret or secret in insecure_defaults:
            raise ValueError("Insecure or missing SECRET_KEY in production environment. Set a strong SECRET_KEY.")
        if not jwt_secret or jwt_secret in insecure_defaults:
            raise ValueError("Insecure or missing JWT_SECRET_KEY in production environment. Set a strong JWT_SECRET_KEY.")
        if not admin_pw or admin_pw in insecure_defaults:
            raise ValueError("Insecure or missing DEFAULT_ADMIN_PASSWORD in production environment. Set a strong DEFAULT_ADMIN_PASSWORD.")


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "testing-secret-key-12345"
    JWT_SECRET_KEY = "testing-jwt-key-12345"
    DEFAULT_ADMIN_PASSWORD = "TestingAdmin#2026!"


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
