"""
app.py  —  Policy Ledger v2 (Production Hardened)
Run: python app.py
"""
import os
import logging
from flask import Flask, redirect, url_for, Response, request
from flask_login import LoginManager, current_user
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect

from config import config
from models import db, bcrypt, User

login_manager = LoginManager()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])
csrf = CSRFProtect()


def rate_limit_key_user_or_ip():
    """Key builder for Flask-Limiter: per-user when authenticated, per-IP otherwise."""
    if current_user and current_user.is_authenticated:
        return f"user:{current_user.id}"
    return get_remote_address() or "127.0.0.1"


def validate_production_env(app: Flask):
    """Fail fast if required security environment variables are missing in production."""
    env = os.environ.get("FLASK_ENV", "development").lower()
    if env == "production" or not app.debug:
        secret = app.config.get("SECRET_KEY", "")
        if not secret or "change-this" in secret.lower() or secret == "dev-secret-key-change-in-prod":
            raise RuntimeError(
                "[FATAL SECURITY ERROR] SECRET_KEY must be explicitly set to a strong random value in production!"
            )
        jwt_secret = app.config.get("JWT_SECRET_KEY", "")
        if not jwt_secret or "change-this" in jwt_secret.lower():
            raise RuntimeError(
                "[FATAL SECURITY ERROR] JWT_SECRET_KEY must be set to a secure value in production!"
            )
        default_admin_pw = app.config.get("DEFAULT_ADMIN_PASSWORD", "")
        if default_admin_pw == "Admin@1234":
            raise RuntimeError(
                "[FATAL SECURITY ERROR] DEFAULT_ADMIN_PASSWORD must be changed in production!"
            )


def create_app(env="default"):
    app = Flask(__name__)
    app.config.from_object(config[env])

    # Validate production environment
    validate_production_env(app)

    # Ensure data dirs exist
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    if "sqlite" in app.config["SQLALCHEMY_DATABASE_URI"]:
        db_path = app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", "")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Extensions
    db.init_app(app)
    bcrypt.init_app(app)
    limiter.init_app(app)
    csrf.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Blueprints
    from blueprints.auth import auth_bp
    from blueprints.admin import admin_bp
    from blueprints.employee import employee_bp
    from blueprints.meetings import meetings_bp
    from blueprints.search import search_bp
    from blueprints.policy_ai import policy_ai_bp
    from blueprints.workflow import workflow_bp
    from blueprints.bi_dashboard import bi_bp
    from blueprints.compliance import compliance_bp
    from blueprints.audit_center import audit_center_bp
    from blueprints.what_if import what_if_bp
    from blueprints.governance import governance_bp
    from blueprints.confusion_index import confusion_index_bp
    from blueprints.contradiction_radar import contradiction_radar_bp
    from blueprints.knowledge_graph import knowledge_graph_bp
    from blueprints.gamification import gamification_bp
    from blueprints.ai_analytics import ai_analytics_bp
    from blueprints.blast_radius import blast_radius_bp
    from rag.api.rag_routes import rag_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(employee_bp)
    app.register_blueprint(meetings_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(policy_ai_bp)
    app.register_blueprint(workflow_bp)
    app.register_blueprint(bi_bp)
    app.register_blueprint(compliance_bp)
    app.register_blueprint(audit_center_bp)
    app.register_blueprint(what_if_bp)
    app.register_blueprint(governance_bp)
    app.register_blueprint(confusion_index_bp)
    app.register_blueprint(contradiction_radar_bp)
    app.register_blueprint(knowledge_graph_bp)
    app.register_blueprint(gamification_bp)
    app.register_blueprint(ai_analytics_bp)
    app.register_blueprint(blast_radius_bp)
    app.register_blueprint(rag_bp)

    # Apply 20 req/min rate limit to RAG Chat endpoint
    limiter.limit("20 per minute", key_func=rate_limit_key_user_or_ip)(
        app.view_functions.get("rag.api_chat")
    )

    # Prometheus Metrics endpoint
    @app.route("/metrics")
    def metrics():
        try:
            from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
            return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
        except Exception as e:
            return f"Metrics unavailable: {str(e)}", 500

    # Root redirect
    @app.route("/")
    def index():
        return redirect(url_for("auth.login"))

    # Error pages
    @app.errorhandler(403)
    def forbidden(e):
        return "<h2>403 — You don't have permission to access this page.</h2><a href='/'>Home</a>", 403

    @app.errorhandler(404)
    def not_found(e):
        return "<h2>404 — Page not found.</h2><a href='/'>Home</a>", 404

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({"error": "Rate limit exceeded. Please wait before asking more questions."}), 429

    # Create tables on first run
    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    env = os.environ.get("FLASK_ENV", "development")
    app = create_app(env)
    print("\n" + "="*55)
    print("  Policy Ledger v2 — starting")
    print("  Open: http://127.0.0.1:5000")
    print("  Run seed.py first if this is a fresh install")
    print("="*55 + "\n")
    app.run(debug=app.config.get("DEBUG", False), port=5000)
