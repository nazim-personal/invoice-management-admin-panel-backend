from datetime import datetime, timezone
import os
from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from app.database.db_manager import DBManager
from app.database.models.user import User
from app.utils.error_messages import ERROR_MESSAGES
from app.utils.response import error_response

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

def create_app():
    app = Flask(__name__)

    # --- Configuration ---
    app.config["JWT_SECRET_KEY"] = os.environ.get('JWT_SECRET_KEY', '773a46049339ef55babc522b64fcc25e3524fb737aa0c2da8a7ee105202a7486')
    app.config["SECRET_KEY"] = os.environ.get('SECRET_KEY', '13c8e9205aa641f5e83b3ad1738047a839ee5df3416c60d502bd4bfa0a657796')
    
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
