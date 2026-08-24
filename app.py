import os
from dotenv import load_dotenv
load_dotenv()

"""
app.py  —  Policy Ledger v2 (Production Hardened)
Run: python app.py
"""
import os
from flask import Flask, redirect, url_for, Response, jsonify, render_template
from flask_login import current_user, login_required
from flask_limiter.util import get_remote_address

from config import config
from extensions import db, bcrypt, login_manager, limiter, csrf
from models import User, UserRole
from utils import role_required


def validate_production_env(app: Flask):
    """Fail fast if required security environment variables are missing in production."""
    env = os.environ.get("FLASK_ENV", "development").lower()
    if (env == "production" or not app.debug) and not app.testing:
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
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    # Extensions
    db.init_app(app)
    bcrypt.init_app(app)
    
    # Configure rate limiter storage URI dynamically
    if app.config.get("TESTING"):
        app.config["RATELIMIT_STORAGE_URI"] = "memory://"
        app.config["RATELIMIT_ENABLED"] = False
    else:
        redis_url = os.environ.get("REDIS_URL")
        if (os.environ.get("FLASK_ENV") == "production" or not app.debug) and not redis_url:
            redis_url = "redis://localhost:6379/0"
        if redis_url:
            app.config["RATELIMIT_STORAGE_URI"] = redis_url
        
    limiter.init_app(app)
    csrf.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

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

    # Prometheus Metrics endpoint (Protected - Admin only)
    @app.route("/metrics")
    @login_required
    @role_required(UserRole.ADMIN)
    def metrics():
        try:
            from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
            return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
        except Exception as e:
            logging.getLogger("app.metrics").error(f"Metrics collection failed: {e}")
            return "Metrics unavailable", 500

    @app.route("/health/live")
    def health_live():
        """Kubernetes liveness probe — checks if application process is alive."""
        return jsonify({"status": "ok", "service": "policy-ledger"}), 200

    @app.route("/health/ready")
    def health_ready():
        """Kubernetes readiness probe — checks database and core service connectivity."""
        try:
            db.session.execute(db.text("SELECT 1"))
            return jsonify({"status": "ready", "database": "connected"}), 200
        except Exception as e:
            logging.getLogger("app.health").error(f"Readiness check failed: {e}")
            return jsonify({"status": "unhealthy", "service": "database_unavailable"}), 503

    # Root redirect
    @app.route("/")
    def index():
        return redirect(url_for("auth.login"))

    # Error pages
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({"error": "Rate limit exceeded. Please wait before asking more questions."}), 429

    # Create tables on first run in development/testing only
    if app.config.get("DEBUG") or app.config.get("TESTING") or os.environ.get("FLASK_ENV", "development").lower() in ("development", "testing"):
        with app.app_context():
            try:
                db.create_all()
            except Exception as e:
                logging.getLogger("app.init").error(f"Development schema creation encountered an error: {e}")
                if app.config.get("TESTING"):
                    raise
    else:
        # In production verify database connection
        with app.app_context():
            try:
                db.session.execute(db.text("SELECT 1"))
            except Exception as e:
                raise RuntimeError(f"[FATAL DATABASE ERROR] Production database connection failed: {e}")

    # Safe model configuration diagnostic logging
    import logging
    diag_logger = logging.getLogger("app.diagnostics")
    diag_logger.info(
        "AI Diagnostic State: "
        f"Embedding Engine={os.environ.get('EMBEDDING_ENGINE', 'fastembed')}, "
        f"Embedding Model={os.environ.get('EMBEDDING_MODEL', 'BAAI/bge-small-en-v1.5')}, "
        f"Reranker Engine={os.environ.get('RERANKER_ENGINE', 'flashrank')}, "
        f"Reranker Model={os.environ.get('RERANKER_MODEL', 'ms-marco-TinyBERT-L-2-v2')}, "
        f"LLM Backend={os.environ.get('LLM_BACKEND', 'ollama')}, "
        f"LLM Model={os.environ.get('LOCAL_LLM_MODEL', 'qwen3:4b-q4_K_M')}"
    )

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
