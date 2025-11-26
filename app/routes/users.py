from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from werkzeug.security import generate_password_hash, check_password_hash

from app.database.models.user import User
from app.utils.response import success_response, error_response
from app.utils.error_messages import ERROR_MESSAGES
from app.utils.auth import require_admin
from app.utils.pagination import get_pagination
from app.schemas.user_schema import UserUpdateSchema

users_blueprint = Blueprint('users', __name__)

@users_blueprint.route('/users/me', methods=['GET'])
@jwt_required()
def get_current_user_profile():
    current_user_id = get_jwt_identity()
    user = User.find_by_id(current_user_id)
    if user:
        return success_response(user.to_dict(), message="User profile retrieved successfully")
    return error_response(error_code='not_found', message=ERROR_MESSAGES["not_found"]["user"], status=404)

@users_blueprint.route('/users/me', methods=['PUT'])
@jwt_required()
def update_current_user_profile():
    current_user_id = get_jwt_identity()
    return update_user_profile(current_user_id)

@users_blueprint.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
@require_admin
def update_user_profile_by_admin(user_id):
    return update_user_profile(user_id)

def update_user_profile(user_id):
    current_user_id = get_jwt_identity()
    user = User.find_by_id(current_user_id)

    # A user can update their own info, or an admin can update any user's info
    if not (user.is_admin or str(current_user_id) == str(user_id)):
        return error_response(error_code='forbidden', message=ERROR_MESSAGES["forbidden"], status=403)

    target_user = User.find_by_id(user_id)
    if not target_user:
        return error_response(error_code='not_found', message=ERROR_MESSAGES["not_found"]["user"], status=404)

    data = request.get_json()
    if not data:
        return error_response(error_code='validation_error', message=ERROR_MESSAGES["validation"]["request_body_empty"], status=400)

    try:
        validated_data = UserUpdateSchema().load(data)
    except ValidationError as err:
        return error_response(
            error_code='validation_error', 
            message=ERROR_MESSAGES["validation"]["invalid_data"], 
            details=err.messages, 
            status=400
        )

    if 'password' in validated_data:
        if 'old_password' not in validated_data:
            return error_response(error_code='validation_error', message="Old password is required to set a new password.", status=400)
        if not target_user.check_password(validated_data['old_password']):
            return error_response(error_code='unauthorized', message="Invalid old password.", status=401)
        validated_data['password_hash'] = generate_password_hash(validated_data.pop('password'), method='scrypt')
        validated_data.pop('old_password', None)

    try:
        if not User.update(user_id, validated_data):
            return error_response(error_code='not_found', message=ERROR_MESSAGES["not_found"]["user"], status=404)

        updated_user = User.find_by_id(user_id)
        return success_response(updated_user.to_dict(), message="User profile updated successfully")
    except Exception as e:
        return error_response(error_code='server_error', message=ERROR_MESSAGES["server_error"]["update_user"], details=str(e), status=500)


@users_blueprint.route('/users', methods=['GET'])
@jwt_required()
@require_admin
def get_users():
    page, per_page = get_pagination()
    include_deleted = request.args.get('include_deleted', 'false').lower() == 'true'
    try:
        users, total = User.find_with_pagination_and_count(page=page, per_page=per_page, include_deleted=include_deleted)
        return success_response({
            'users': [u.to_dict() for u in users],
            'total': total,
            'page': page,
            'per_page': per_page
        }, message="Users retrieved successfully")
    except Exception as e:
        return error_response(error_code='server_error', message=ERROR_MESSAGES["server_error"]["fetch_user"], details=str(e), status=500)

@users_blueprint.route('/users/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    current_user_id = get_jwt_identity()
    user = User.find_by_id(current_user_id)

    # A user can get their own info, or an admin can get any user's info
    if not (user.is_admin or str(current_user_id) == str(user_id)):
        return error_response(error_code='forbidden', message=ERROR_MESSAGES["forbidden"], status=403)

    include_deleted = request.args.get('include_deleted', 'false').lower() == 'true'
    try:
        target_user = User.find_by_id(user_id, include_deleted=include_deleted)
        if target_user:
            return success_response(target_user.to_dict(), message="User retrieved successfully")
        return error_response(error_code='not_found', message=ERROR_MESSAGES["not_found"]["user"], status=404)
    except Exception as e:
        return error_response(error_code='server_error', message=ERROR_MESSAGES["server_error"]["fetch_user"], details=str(e), status=500)

@users_blueprint.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
@require_admin
def delete_user(user_id):
    try:
        if not User.soft_delete(user_id):
            return error_response(error_code='not_found', message=ERROR_MESSAGES["not_found"]["user"], status=404)

        return success_response(message="User soft-deleted successfully")
    except Exception as e:
        return error_response(error_code='server_error', message=ERROR_MESSAGES["server_error"]["delete_user"], details=str(e), status=500)
