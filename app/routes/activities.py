
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.database.models.activity_model import ActivityLog
from app.utils.response import success_response, error_response
from app.utils.pagination import get_pagination
from app.utils.auth import require_permission

activities_bp = Blueprint('activities', __name__)

@activities_bp.route('/activities/', methods=['GET'])
@jwt_required()
@require_permission('activities.view_all') # Assuming we might want a permission for this
def list_all_activities():
    """
    List all system activities (Admin/Manager only).
    """
    try:
        page, per_page = get_pagination()
        offset = (page - 1) * per_page

        logs, total = ActivityLog.list_logs(limit=per_page, offset=offset)

        result = []
        for log in logs:
            data = log.to_dict()
            data['user_name'] = getattr(log, 'user_name', 'Unknown')
            result.append(data)

        return success_response(
            result=result,
            meta={'total': total, 'page': page, 'per_page': per_page}
        )
    except Exception as e:
        return error_response('server_error', 'Failed to fetch activities.', str(e), 500)

@activities_bp.route('/activities/me/', methods=['GET'])
@jwt_required()
def list_my_activities():
    """
    List activities for the current user.
    """
    try:
        current_user_id = get_jwt_identity()
        page, per_page = get_pagination()
        offset = (page - 1) * per_page

        logs, total = ActivityLog.list_logs(user_id=current_user_id, limit=per_page, offset=offset)

        result = []
        for log in logs:
            data = log.to_dict()
            data['user_name'] = getattr(log, 'user_name', 'You')
            result.append(data)

        return success_response(
            result=result,
            meta={'total': total, 'page': page, 'per_page': per_page}
        )
    except Exception as e:
        return error_response('server_error', 'Failed to fetch your activities.', str(e), 500)

@activities_bp.route('/invoices/<string:invoice_id>/activities/', methods=['GET'])
@jwt_required()
@require_permission('invoices.view')
def list_invoice_activities(invoice_id):
    """
    List activities for a specific invoice.
    """
    try:
        page, per_page = get_pagination()
        offset = (page - 1) * per_page

        logs, total = ActivityLog.list_logs(entity_type='invoice', entity_id=invoice_id, limit=per_page, offset=offset)

        result = []
        for log in logs:
            data = log.to_dict()
            data['user_name'] = getattr(log, 'user_name', 'Unknown')
            result.append(data)

        return success_response(
            result=result,
            meta={'total': total, 'page': page, 'per_page': per_page}
        )
    except Exception as e:
        return error_response('server_error', 'Failed to fetch invoice activities.', str(e), 500)

@activities_bp.route('/customers/<string:customer_id>/activities/', methods=['GET'])
@jwt_required()
@require_permission('customers.view')
def list_customer_activities(customer_id):
    """
    List activities for a specific customer.
    """
    try:
        page, per_page = get_pagination()
        offset = (page - 1) * per_page

        logs, total = ActivityLog.list_logs(entity_type='customer', entity_id=customer_id, limit=per_page, offset=offset)

        result = []
        for log in logs:
            data = log.to_dict()
            data['user_name'] = getattr(log, 'user_name', 'Unknown')
            result.append(data)

        return success_response(
            result=result,
            meta={'total': total, 'page': page, 'per_page': per_page}
        )
    except Exception as e:
        return error_response('server_error', 'Failed to fetch customer activities.', str(e), 500)


@activities_bp.route('/products/<string:product_id>/activities/', methods=['GET'])
@jwt_required()
@require_permission('products.view')
def list_product_activities(product_id):
    """
    List activities for a specific product.
    """
    try:
        page, per_page = get_pagination()
        offset = (page - 1) * per_page

        logs, total = ActivityLog.list_logs(entity_type='product', entity_id=product_id, limit=per_page, offset=offset)

        result = []
        for log in logs:
            data = log.to_dict()
            data['user_name'] = getattr(log, 'user_name', 'Unknown')
            result.append(data)

        return success_response(
            result=result,
            meta={'total': total, 'page': page, 'per_page': per_page}
        )
    except Exception as e:
        return error_response('server_error', 'Failed to fetch product activities.', str(e), 500)
