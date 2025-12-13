from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.database.models.permission_model import UserPermission
from app.database.models.user import User
from app.utils.auth import require_admin
from app.utils.permissions import PERMISSIONS, PERMISSION_CATEGORIES
from app.utils.response import success_response, error_response
from app.utils.error_messages import ERROR_MESSAGES

permissions_blueprint = Blueprint('permissions', __name__)


# ---------------- List All Permissions ----------------
@permissions_blueprint.route('/permissions', methods=['GET'])
@jwt_required()
def list_permissions():
    """
    List all available permissions with descriptions and categories.
    """
    return success_response({
        'permissions': PERMISSIONS,
        'categories': PERMISSION_CATEGORIES
    }, message="Permissions retrieved successfully.")


# ---------------- Get User Permissions ----------------
@permissions_blueprint.route('/users/<string:user_id>/permissions', methods=['GET'])
@jwt_required()
@require_admin
def get_user_permissions(user_id: str):
    """
    Get all permissions for a specific user.
    Admin users automatically have all permissions.
    """
    try:
        user = User.find_by_id(user_id)
        if not user:
            return error_response('not_found', ERROR_MESSAGES["not_found"]["user"], 404)

        permissions = user.get_permissions()

        return success_response({
            'user_id': user_id,
            'role': user.role,
            'permissions': permissions,
            'is_admin': user.role == 'admin'
        }, message="User permissions retrieved successfully.")

    except Exception as e:
        return error_response('server_error', 'Failed to retrieve user permissions.', details=str(e), status=500)


# ---------------- Update User Permissions (Sync) ----------------
@permissions_blueprint.route('/users/<string:user_id>/permissions', methods=['PUT'])
@jwt_required()
@require_admin
def update_user_permissions(user_id: str):
    """
    Replace all user permissions with a new set.
    Admin users cannot have their permissions modified.
    """
    data = request.get_json() or {}
    permissions = data.get('permissions', [])

    if not isinstance(permissions, list):
        return error_response('validation_error', 'Permissions must be an array.', 400)

    try:
        user = User.find_by_id(user_id)
        if not user:
            return error_response('not_found', ERROR_MESSAGES["not_found"]["user"], 404)

        if user.role == 'admin':
            return error_response('validation_error', 'Cannot modify permissions for admin users.', 400)

        # Validate all permissions exist
        invalid_perms = [p for p in permissions if p not in PERMISSIONS]
        if invalid_perms:
            return error_response('validation_error', f'Invalid permissions: {", ".join(invalid_perms)}', 400)

        admin_id = get_jwt_identity()
        count = UserPermission.sync_permissions(user_id, permissions, admin_id)

        return success_response({
            'user_id': user_id,
            'permissions_count': count,
            'permissions': permissions
        }, message=f'{count} permission(s) updated successfully.')

    except Exception as e:
        return error_response('server_error', 'Failed to update user permissions.', details=str(e), status=500)


# ---------------- Grant Single Permission ----------------
@permissions_blueprint.route('/users/<string:user_id>/permissions/<string:permission>', methods=['POST'])
@jwt_required()
@require_admin
def grant_permission(user_id: str, permission: str):
    """
    Grant a single permission to a user.
    """
    try:
        user = User.find_by_id(user_id)
        if not user:
            return error_response('not_found', ERROR_MESSAGES["not_found"]["user"], 404)

        if user.role == 'admin':
            return error_response('validation_error', 'Admin users already have all permissions.', 400)

        if permission not in PERMISSIONS:
            return error_response('validation_error', f'Invalid permission: {permission}', 400)

        admin_id = get_jwt_identity()
        UserPermission.grant_permission(user_id, permission, admin_id)

        return success_response({
            'user_id': user_id,
            'permission': permission
        }, message='Permission granted successfully.')

    except Exception as e:
        return error_response('server_error', 'Failed to grant permission.', details=str(e), status=500)


# ---------------- Revoke Single Permission ----------------
@permissions_blueprint.route('/users/<string:user_id>/permissions/<string:permission>', methods=['DELETE'])
@jwt_required()
@require_admin
def revoke_permission(user_id: str, permission: str):
    """
    Revoke a single permission from a user.
    """
    try:
        user = User.find_by_id(user_id)
        if not user:
            return error_response('not_found', ERROR_MESSAGES["not_found"]["user"], 404)

        if user.role == 'admin':
            return error_response('validation_error', 'Cannot revoke permissions from admin users.', 400)

        UserPermission.revoke_permission(user_id, permission)

        return success_response({
            'user_id': user_id,
            'permission': permission
        }, message='Permission revoked successfully.')

    except Exception as e:
        return error_response('server_error', 'Failed to revoke permission.', details=str(e), status=500)
