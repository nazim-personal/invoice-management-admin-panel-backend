from functools import wraps
from flask_jwt_extended import get_jwt, get_current_user
from app.utils.response import error_response

def require_role(*roles):
    """
    Authorization decorator to ensure a user has one of the specified roles.
    This decorator must be placed AFTER the @jwt_required() decorator.
    It checks for a 'role' claim in the JWT.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Get the claims from the access token
            claims = get_jwt()
            user_role = claims.get('role')

            # Verify the user's role is one of the allowed roles
            if user_role not in roles:
                return error_response(
                    error_code='forbidden',
                    message=f"Access forbidden: This resource requires one of the following roles: {', '.join(roles)}.",
                    status=403
                )

            return fn(*args, **kwargs)
        return wrapper
    return decorator

# Convenience decorator for the common case of requiring an 'admin' role.
# This can be used on any endpoint that also has @jwt_required().
require_admin = require_role('admin')


def require_permission(permission: str):
    """
    Check if user has a specific permission.
    Admin role automatically has all permissions.
    Must be used after @jwt_required() decorator.

    Usage:
        @app.route('/customers', methods=['POST'])
        @jwt_required()
        @require_permission('customers.create')
        def create_customer():
            ...
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            current_user = get_current_user()

            if not current_user:
                return error_response(
                    error_code='unauthorized',
                    message='Authentication required.',
                    status=401
                )

            # Admin has all permissions automatically
            if current_user.role == 'admin':
                return fn(*args, **kwargs)

            # Check if user has the specific permission
            if not current_user.has_permission(permission):
                return error_response(
                    error_code='forbidden',
                    message=f'Permission denied. Required permission: {permission}',
                    status=403
                )

            return fn(*args, **kwargs)
        return wrapper
    return decorator
