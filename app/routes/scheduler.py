from flask import Blueprint
from flask_jwt_extended import jwt_required
from app.utils.auth import require_admin
from app.utils.response import success_response, error_response
from app.services.scheduler_service import scheduler_service

scheduler_blueprint = Blueprint('scheduler', __name__)

@scheduler_blueprint.route('/scheduler/check-overdue', methods=['POST'])
@jwt_required()
@require_admin
def trigger_overdue_check():
    """
    Manually trigger the overdue invoice check.
    This is useful for testing and can also be used by admins to run checks on-demand.
    """
    try:
        scheduler_service.check_overdue_invoices()
        return success_response(
            result={'message': 'Overdue invoice check completed'},
            message='Overdue invoice check triggered successfully',
            status=200
        )
    except Exception as e:
        return error_response(
            error_code='server_error',
            message='Failed to trigger overdue check',
            details=str(e),
            status=500
        )
