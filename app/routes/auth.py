from flask import Blueprint, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt,
    get_jwt_identity,
    get_current_user
)
from app.database.models.user import User
from app.database.token_blocklist import BLOCKLIST
from app.utils.auth import require_admin
from app.utils.error_messages import ERROR_MESSAGES
from app.utils.response import success_response, error_response

auth_blueprint = Blueprint('auth', __name__)

@auth_blueprint.route('/sign-in', methods=['POST'])
def sign_in():
    """
    Authenticates a user and returns JWT access and refresh tokens.
    Accepts: email/password, username/password, or identifier/password
    """
    data = request.get_json()
    if not data:
        return error_response(error_code='validation_error', message="Request body cannot be empty.", status=400)

    # Support multiple login formats: email, username, or identifier (backward compatible)
    login_identifier = data.get('email') or data.get('username') or data.get('identifier')
    password = data.get('password')

    if not login_identifier or not password:
        return error_response(error_code='validation_error', message=ERROR_MESSAGES["validation"]["missing_credentials"], status=400)

    user = User.find_by_username_or_email(login_identifier)

    if user and user.check_password(password):
        additional_claims = {"role": user.role}
        access_token = create_access_token(identity=str(user.id), additional_claims=additional_claims)
        refresh_token = create_refresh_token(identity=str(user.id), additional_claims=additional_claims)

        user_dict = user.to_dict()
        user_dict['permissions'] = user.get_permissions()

        return success_response({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': 3600,  # 1 hour in seconds (matches JWT_ACCESS_TOKEN_EXPIRES)
            'user': user_dict
        }, message="Authentication successful.")

    return error_response(error_code='invalid_credentials', message=ERROR_MESSAGES["auth"]["invalid_credentials"], status=401)

@auth_blueprint.route('/sign-out', methods=['POST'])
@jwt_required()
def sign_out():
    """
    Signs out the user by adding the token's JTI to the blocklist.
    """
    jti = get_jwt()["jti"]
    BLOCKLIST.add(jti)
    return success_response(message="Successfully signed out.")


@auth_blueprint.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    Refreshes the access token using a valid refresh token.
    Returns a new access token.
    """
    try:
        identity = get_jwt_identity()
        user = User.find_by_id(identity)

        if not user:
            return error_response(error_code='user_not_found', message="User not found.", status=404)

        additional_claims = {"role": user.role}
        new_access_token = create_access_token(identity=identity, additional_claims=additional_claims)

        return success_response({
            'access_token': new_access_token,
            'token_type': 'Bearer',
            'expires_in': 3600  # 1 hour in seconds
        }, message="Token refreshed successfully.")
    except Exception as e:
        return error_response(error_code='server_error', message="Failed to refresh token.", details=str(e), status=500)


@auth_blueprint.route('/me', methods=['GET'])
@jwt_required()
def get_current_user_info():
    """
    Returns the currently authenticated user's information.
    """
    try:
        current_user = get_current_user()
        if not current_user:
            return error_response(error_code='user_not_found', message="User not found.", status=404)

        user_dict = current_user.to_dict()
        user_dict['permissions'] = current_user.get_permissions()

        return success_response(user_dict, message="User data retrieved successfully.")
    except Exception as e:
        return error_response(error_code='server_error', message="Failed to retrieve user data.", details=str(e), status=500)


@auth_blueprint.route('/register', methods=['POST'])
@jwt_required()
@require_admin
def register():
    """
    Registers a new user. This is an admin-only action.
    """
    data = request.get_json()
    if not data:
        return error_response(error_code='validation_error', message=ERROR_MESSAGES["validation"]["request_body_empty"], status=400)

    required_fields = ['username', 'email', 'password', 'name']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return error_response(error_code='validation_error', message=f"Missing required fields: {', '.join(missing_fields)}", status=400)

    if User.find_by_email(data['email']):
        return error_response(error_code='conflict', message=ERROR_MESSAGES["conflict"]["user_exists"], status=409)

    try:
        user_id = User.create(data)
        if user_id:
            new_user = User.find_by_id(user_id)
            # Convert user to a dictionary for the response
            user_data = {
                'id': new_user.id,
                'username': new_user.username,
                'email': new_user.email,
                'name': new_user.name,
                'role': new_user.role
            }
            return success_response(user_data, message="User registered successfully.", status=201)
        return error_response(error_code='server_error', message=ERROR_MESSAGES["server_error"]["create_user"], status=500)
    except Exception as e:
        return error_response(error_code='server_error', message=ERROR_MESSAGES["server_error"]["create_user"], details=str(e), status=500)
