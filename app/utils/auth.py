from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt

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
                return jsonify(
                    message=f"Access forbidden: This resource requires one of the following roles: {', '.join(roles)}.",
                    error="forbidden"
                ), 403
            
            return fn(*args, **kwargs)
        return wrapper
    return decorator

# Convenience decorator for the common case of requiring an 'admin' role.
# This can be used on any endpoint that also has @jwt_required().
require_admin = require_role('admin')
