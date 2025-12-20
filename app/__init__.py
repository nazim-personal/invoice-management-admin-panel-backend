from datetime import datetime, timezone, timedelta
import os
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from app.database.db_manager import DBManager
from app.database.models.user import User
from app.utils.error_messages import ERROR_MESSAGES
from app.utils.response import error_response
from app.utils.db_init import init_db

# Import the token blocklist
from app.database.token_blocklist import BLOCKLIST

# Import blueprints from their correct locations
from .routes.auth import auth_blueprint
from .routes.users import users_blueprint
from .routes.customers import customers_blueprint
from .routes.invoices import invoices_blueprint
from .routes.products import products_blueprint
from .routes.payments import payments_blueprint
from .routes.dashboard import dashboard_bp
from .routes.permissions import permissions_blueprint
from .routes.activities import activities_bp
from .routes.reports import reports_bp
from .routes.webhooks import webhooks_bp
from .routes.scheduler import scheduler_blueprint
from .routes.notification_settings import notification_settings_blueprint

mail = Mail()

def create_app():
    app = Flask(__name__)

    # Initialize database on startup
    # We do this inside app context in case we switch to using current_app.config later
    with app.app_context():
        init_db()

    # --- CORS Configuration ---
    # Allow all origins in development, configure specific origins in production
    cors_origins = os.environ.get('CORS_ORIGINS', '*')
    CORS(app,
         resources={r"/api/*": {"origins": cors_origins}},
         supports_credentials=True,
         allow_headers=["Content-Type", "Authorization"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

    # --- Configuration ---
    app.config["JWT_SECRET_KEY"] = os.environ.get('JWT_SECRET_KEY', '773a46049339ef55babc522b64fcc25e3524fb737aa0c2da8a7ee105202a7486')
    app.config["SECRET_KEY"] = os.environ.get('SECRET_KEY', '13c8e9205aa641f5e83b3ad1738047a839ee5df3416c60d502bd4bfa0a657796')

    # --- Mail Configuration ---
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')

    mail.init_app(app)

    # --- Scheduler Configuration ---
    from app.services.scheduler_service import scheduler_service
    scheduler_service.init_app(app)

    # JWT Token Configuration
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=int(os.environ.get('JWT_ACCESS_TOKEN_HOURS', '1')))
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=int(os.environ.get('JWT_REFRESH_TOKEN_DAYS', '30')))
    app.config["JWT_TOKEN_LOCATION"] = ["headers"]  # Support Authorization header

    jwt = JWTManager(app)

    # --- JWT Blocklist Configuration ---
    def check_if_token_in_blocklist(jwt_header, jwt_payload):
        """This callback checks if a token has been revoked (logged out)."""
        jti = jwt_payload["jti"]
        return jti in BLOCKLIST

    def revoked_token_callback(jwt_header, jwt_payload):
        """This callback defines the response for a revoked token."""
        return error_response(error_code='token_revoked', message="Token has been revoked. Please sign in again.", status=401)

    # --- JWT Custom Error Handlers ---
    def handle_invalid_token(error):
        return error_response(error_code='invalid_token', message=ERROR_MESSAGES["auth"]["invalid_token"], status=401)

    def handle_missing_token(error):
        return error_response(error_code='missing_token', message=ERROR_MESSAGES["auth"]["missing_token"], status=401)

    def handle_expired_token(jwt_header, jwt_payload):
        return error_response(error_code='token_expired', message=ERROR_MESSAGES["auth"]["token_expired"], status=401)

    def handle_user_lookup_error(jwt_header, jwt_data):
        return error_response(error_code='invalid_token', message=ERROR_MESSAGES["auth"]["invalid_token"], status=401)

    # --- JWT User Claims ---
    def user_lookup_callback(_jwt_header, jwt_data):
        identity = jwt_data["sub"]
        return User.find_by_id(identity)

    # Registering all JWT handlers explicitly to avoid linter warnings
    jwt.token_in_blocklist_loader(check_if_token_in_blocklist)
    jwt.revoked_token_loader(revoked_token_callback)
    jwt.invalid_token_loader(handle_invalid_token)
    jwt.unauthorized_loader(handle_missing_token)
    jwt.expired_token_loader(handle_expired_token)
    jwt.user_lookup_error_loader(handle_user_lookup_error)
    jwt.user_lookup_loader(user_lookup_callback)

    # --- Register Blueprints ---
    app.register_blueprint(auth_blueprint, url_prefix='/api/auth')
    app.register_blueprint(users_blueprint, url_prefix='/api')
    app.register_blueprint(customers_blueprint, url_prefix='/api')
    app.register_blueprint(invoices_blueprint, url_prefix='/api')
    app.register_blueprint(products_blueprint, url_prefix='/api')
    app.register_blueprint(payments_blueprint, url_prefix='/api')
    app.register_blueprint(dashboard_bp, url_prefix='/api')
    app.register_blueprint(permissions_blueprint, url_prefix='/api')
    app.register_blueprint(activities_bp, url_prefix='/api')
    app.register_blueprint(reports_bp, url_prefix='/api')
    app.register_blueprint(webhooks_bp, url_prefix='/api')
    app.register_blueprint(scheduler_blueprint, url_prefix='/api')
    app.register_blueprint(notification_settings_blueprint, url_prefix='/api')

    # A simple health check route
    @app.route("/api/health")
    def health_check(): # type: ignore
        try:
            # Test DB connectivity
            result = DBManager.execute_query("SELECT 1", fetch="one")
            if result is None:
                raise Exception("DB returned no result")
            db_status = "connected"
            http_status = 200
        except Exception as e:
            db_status = f"error: {str(e)}"
            http_status = 500

        return jsonify({
            "status": "running" if http_status == 200 else "error",
            "message": "Project is up and running!" if http_status == 200 else "Database connection failed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": db_status
        }), http_status

    return app
