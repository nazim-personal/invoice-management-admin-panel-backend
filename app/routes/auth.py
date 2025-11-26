from flask import Blueprint, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt
from app.database.models.user import User
from app.database.token_blocklist import BLOCKLIST
from app.utils.auth import require_admin
from app.utils.error_messages import ERROR_MESSAGES
from app.utils.response import success_response, error_response

auth_blueprint = Blueprint('auth', __name__)

@auth_blueprint.route('/sign-in', methods=['POST'])
def sign_in():
    """
    Authenticates a user and returns a JWT access token.
    """
    data = request.get_json()
    if not data:
        return error_response(error_code='validation_error', message="Request body cannot be empty.", status=400)

    login_identifier = data.get('identifier')
    password = data.get('password')

    if not login_identifier or not password:
        return error_response(error_code='validation_error', message=ERROR_MESSAGES["validation"]["missing_credentials"], status=400)

    user = User.find_by_username_or_email(login_identifier)

    if user and user.check_password(password):
        additional_claims = {"role": user.role}
        access_token = create_access_token(identity=str(user.id), additional_claims=additional_claims)
        return success_response({'access_token': access_token, 'user_info': user.to_dict()}, message="Authentication successful.")
    
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
