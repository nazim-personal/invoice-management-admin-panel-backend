from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from werkzeug.security import generate_password_hash, check_password_hash

from app.database.models.user import User
from app.database.models.activity_model import ActivityLog
from app.utils.response import success_response, error_response
from app.utils.error_messages import ERROR_MESSAGES
from app.utils.auth import require_admin, require_permission
from app.utils.pagination import get_pagination
from app.utils.helpers import validate_request, get_or_404
from app.schemas.user_schema import UserUpdateSchema, ProfileUpdateSchema, PasswordChangeSchema, BillingInfoSchema

users_blueprint = Blueprint('users', __name__)

@users_blueprint.route('/users/me', methods=['GET'])
@jwt_required()
def get_current_user_profile():
    current_user_id = get_jwt_identity()
    user = get_or_404(User, current_user_id, "User")
    if user:
        return success_response(user.to_dict(), message="User profile retrieved successfully")
    return error_response(error_code='not_found', message=ERROR_MESSAGES["not_found"]["user"], status=404)

@users_blueprint.route('/users/me', methods=['PUT'])
@jwt_required()
def update_current_user_profile():
    current_user_id = get_jwt_identity()
    return update_user_profile(current_user_id)

@users_blueprint.route('/users/<string:user_id>', methods=['PUT'])
@jwt_required()
@require_permission('users.update')
def update_user_by_id(user_id: str):
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

    try:
        validated_data = validate_request(UserUpdateSchema())
    except ValueError as err:
        return error_response(
            error_code='validation_error',
            message=ERROR_MESSAGES["validation"]["invalid_data"],
            details=err.args[0],
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

        # Log activity
        activity_details = {k: v for k, v in validated_data.items() if k != 'password_hash'}
        if 'password_hash' in validated_data:
            activity_details['password_changed'] = True

        ActivityLog.create_log(
            user_id=current_user_id,
            action='USER_PROFILE_UPDATED',
            entity_type='user',
            entity_id=user_id,
            details=activity_details,
            ip_address=request.remote_addr
        )

        updated_user = User.find_by_id(user_id)
        return success_response(updated_user.to_dict(), message="User profile updated successfully")
    except Exception as e:
        return error_response(error_code='server_error', message=ERROR_MESSAGES["server_error"]["update_user"], details=str(e), status=500)


@users_blueprint.route('/users/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update current user's profile information (name, email, phone)."""
    current_user_id = get_jwt_identity()
    user = User.find_by_id(current_user_id)

    if not user:
        return error_response(error_code='not_found', message=ERROR_MESSAGES["not_found"]["user"], status=404)

    try:
        validated_data = validate_request(ProfileUpdateSchema())
    except ValueError as err:
        return error_response(
            error_code='validation_error',
            message="Invalid data provided",
            details=err.args[0],
            status=400
        )

    # Check if email is being changed and if it's already in use
    if 'email' in validated_data and validated_data['email'] != user.email:
        existing_user = User.find_by_email(validated_data['email'])
        if existing_user and str(existing_user.id) != str(current_user_id):
            return error_response(
                error_code='conflict',
                message='Email address is already in use',
                status=409
            )

    try:
        if not User.update(current_user_id, validated_data):
            return error_response(error_code='not_found', message=ERROR_MESSAGES["not_found"]["user"], status=404)

        # Log activity
        ActivityLog.create_log(
            user_id=current_user_id,
            action='PROFILE_UPDATED',
            entity_type='user',
            entity_id=current_user_id,
            details=validated_data,
            ip_address=request.remote_addr
        )

        updated_user = User.find_by_id(current_user_id)
        return success_response(updated_user.to_dict(), message="Profile updated successfully")
    except Exception as e:
        return error_response(
            error_code='server_error',
            message="An error occurred while updating profile",
            details=str(e),
            status=500
        )


@users_blueprint.route('/users/password', methods=['PUT'])
@jwt_required()
def change_password():
    """Change current user's password."""
    current_user_id = get_jwt_identity()
    user = User.find_by_id(current_user_id)

    if not user:
        return error_response(error_code='not_found', message=ERROR_MESSAGES["not_found"]["user"], status=404)

    try:
        validated_data = validate_request(PasswordChangeSchema())
    except ValueError as err:
        return error_response(
            error_code='validation_error',
            message="Invalid data provided",
            details=err.args[0],
            status=400
        )

    # Verify old password
    if not user.check_password(validated_data['old_password']):
        return error_response(
            error_code='unauthorized',
            message="Current password is incorrect",
            status=401
        )

    # Update password
    new_password_hash = generate_password_hash(validated_data['new_password'], method='scrypt')

    try:
        if not User.update(current_user_id, {'password_hash': new_password_hash}):
            return error_response(error_code='not_found', message=ERROR_MESSAGES["not_found"]["user"], status=404)

        # Log activity (don't include password details)
        ActivityLog.create_log(
            user_id=current_user_id,
            action='PASSWORD_CHANGED',
            entity_type='user',
            entity_id=current_user_id,
            details={'changed_at': 'self-service'},
            ip_address=request.remote_addr
        )

        return success_response(message="Password changed successfully")
    except Exception as e:
        return error_response(
            error_code='server_error',
            message="An error occurred while changing password",
            details=str(e),
            status=500
        )


@users_blueprint.route('/users/billing', methods=['GET'])
@jwt_required()
def get_billing_info():
    """Get current user's billing information."""
    current_user_id = get_jwt_identity()
    user = User.find_by_id(current_user_id)

    if not user:
        return error_response(error_code='not_found', message=ERROR_MESSAGES["not_found"]["user"], status=404)

    billing_info = {
        'billing_address': user.billing_address,
        'billing_city': user.billing_city,
        'billing_state': user.billing_state,
        'billing_pin': user.billing_pin,
        'billing_gst': user.billing_gst
    }

    return success_response(billing_info, message="Billing information retrieved successfully")


@users_blueprint.route('/users/billing', methods=['PUT'])
@jwt_required()
def update_billing_info():
    """Update current user's billing information."""
    current_user_id = get_jwt_identity()
    user = User.find_by_id(current_user_id)

    if not user:
        return error_response(error_code='not_found', message=ERROR_MESSAGES["not_found"]["user"], status=404)

    try:
        validated_data = validate_request(BillingInfoSchema())
    except ValueError as err:
        return error_response(
            error_code='validation_error',
            message="Invalid data provided",
            details=err.args[0],
            status=400
        )

    try:
        if not User.update(current_user_id, validated_data):
            return error_response(error_code='not_found', message=ERROR_MESSAGES["not_found"]["user"], status=404)

        # Log activity
        ActivityLog.create_log(
            user_id=current_user_id,
            action='BILLING_UPDATED',
            entity_type='user',
            entity_id=current_user_id,
            details=validated_data,
            ip_address=request.remote_addr
        )

        updated_user = User.find_by_id(current_user_id)
        billing_info = {
            'billing_address': updated_user.billing_address,
            'billing_city': updated_user.billing_city,
            'billing_state': updated_user.billing_state,
            'billing_pin': updated_user.billing_pin,
            'billing_gst': updated_user.billing_gst
        }

        return success_response(billing_info, message="Billing information updated successfully")
    except Exception as e:
        return error_response(
            error_code='server_error',
            message="An error occurred while updating billing information",
            details=str(e),
            status=500
        )


@users_blueprint.route('/users', methods=['GET'])
@jwt_required()
@require_permission('users.list')
def get_all_users():
    page, per_page = get_pagination()
    deleted = request.args.get('deleted', 'false').lower() == 'true'
    try:
        users, total = User.find_with_pagination_and_count(page=page, per_page=per_page, deleted_only=deleted)
        message = "Deleted users retrieved successfully" if deleted else "Users retrieved successfully"
        return success_response(
            [u.to_dict() for u in users],
            message=message,
            meta={'total': total, 'page': page, 'per_page': per_page}
        )
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

@users_blueprint.route('/users/<string:user_id>', methods=['DELETE'])
@jwt_required()
@require_permission('users.delete')
def delete_user(user_id: str):
    try:
        if not User.soft_delete(user_id):
            return error_response(error_code='not_found', message=ERROR_MESSAGES["not_found"]["user"], status=404)

        return success_response(message="User soft-deleted successfully")
    except Exception as e:
        return error_response(error_code='server_error', message=ERROR_MESSAGES["server_error"]["delete_user"], details=str(e), status=500)
