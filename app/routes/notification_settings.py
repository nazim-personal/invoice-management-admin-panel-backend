from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError

from app.database.models.notification_settings import NotificationSettings
from app.schemas.notification_settings_schema import notification_settings_schema
from app.utils.response import success_response, error_response

notification_settings_blueprint = Blueprint('notification_settings', __name__)

@notification_settings_blueprint.route('/notification-settings', methods=['GET'])
@jwt_required()
def get_notification_settings():
    """
    Get the current user's notification settings.
    Creates default settings if none exist.
    """
    try:
        user_id = get_jwt_identity()
        settings = NotificationSettings.get_user_settings(user_id)

        return success_response(
            result=settings.to_dict(),
            message='Notification settings retrieved successfully',
            status=200
        )
    except Exception as e:
        return error_response(
            error_code='server_error',
            message='Failed to retrieve notification settings',
            details=str(e),
            status=500
        )

@notification_settings_blueprint.route('/notification-settings', methods=['PUT'])
@jwt_required()
def update_notification_settings():
    """
    Update the current user's notification settings.
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        if not data:
            return error_response(
                error_code='validation_error',
                message='Request body is empty',
                status=400
            )

        # Validate input
        try:
            validated_data = notification_settings_schema.load(data, partial=True)
        except ValidationError as err:
            return error_response(
                error_code='validation_error',
                message='Invalid data provided',
                details=err.messages,
                status=400
            )

        # Update settings
        updated_settings = NotificationSettings.update_settings(user_id, validated_data)

        return success_response(
            result=updated_settings.to_dict(),
            message='Notification settings updated successfully',
            status=200
        )
    except Exception as e:
        return error_response(
            error_code='server_error',
            message='Failed to update notification settings',
            details=str(e),
            status=500
        )
