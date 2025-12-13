from typing import Any, Dict, List, Optional
from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from marshmallow import ValidationError

from app.database.models.customer import Customer
from app.schemas.customer_schema import (
    CustomerSchema,
    CustomerSummarySchema,
    CustomerDetailSchema,
    CustomerUpdateSchema,
)
from app.utils.response import success_response, error_response
from app.utils.error_messages import ERROR_MESSAGES
from app.utils.auth import require_admin, require_permission
from app.utils.pagination import get_pagination
from app.utils.helpers import validate_request, bulk_action_handler

customers_blueprint = Blueprint('customers', __name__)

# Schemas
customer_schema = CustomerSchema()
customer_summary_schema = CustomerSummarySchema()
customer_detail_schema = CustomerDetailSchema()
customer_update_schema = CustomerUpdateSchema()





def get_existing_customer_by_email(email: str):
    """Check if customer with email exists (including soft-deleted)."""
    return Customer.find_by_email(email, include_deleted=True)


# ---------------- Create Customer ----------------
@customers_blueprint.route('/customers', methods=['POST'])
@jwt_required()
@require_permission('customers.create')
def create_customer():
    data = request.get_json() or {}
    if not data:
        return error_response('validation_error', ERROR_MESSAGES["validation"]["request_body_empty"], 400)

    try:
        validated_data: Dict[str, Any] = validate_request(customer_schema, data)

        if 'email' in validated_data and validated_data['email']:
            existing = get_existing_customer_by_email(validated_data['email'])
            if existing:
                if existing.deleted_at is None:
                    return error_response(error_code='conflict', message='A customer with this email address already exists.', status=409)
                return error_response(
                    error_code='conflict_soft_deleted',
                    message='A customer with this email was previously deleted. Do you want to restore them?',
                    details={'email': existing.email},
                    status=409
                )

        customer_id = Customer.create(validated_data)
        customer = Customer.find_by_id_with_aggregates(customer_id)
        return success_response(customer_summary_schema.dump(customer), message="Customer created successfully.", status=201)

    except ValueError as err:
        return error_response('validation_error', "Invalid data.", details=err.args[0], status=400)
    except Exception as e:
        return error_response(error_code='server_error',
                              message=ERROR_MESSAGES["server_error"]["create_customer"],
                              details=str(e),
                              status=500)


# ---------------- Get Customers ----------------
@customers_blueprint.route('/customers', methods=['GET'])
@jwt_required()
@require_permission('customers.list')
def get_customers():
    page, per_page = get_pagination()
    q = request.args.get('q')
    status = request.args.get('status')
    include_deleted = request.args.get('include_deleted', 'false').lower() == 'true'

    try:
        customers, total = Customer.list_all(
            q=q,
            status=status,
            offset=(page - 1) * per_page,
            limit=per_page,
            include_deleted=include_deleted
        )
        return success_response(
            customer_summary_schema.dump(customers, many=True),
            "Customers retrieved successfully.",
            meta={'total': total, 'page': page, 'per_page': per_page}
        )
    except Exception as e:
        return error_response('server_error', ERROR_MESSAGES["server_error"]["fetch_customer"], details=str(e), status=500)


# ---------------- Get Single Customer ----------------
@customers_blueprint.route('/customers/<string:customer_id>', methods=['GET'])
@jwt_required()
@require_permission('customers.view')
def get_customer(customer_id: str):
    include_deleted = request.args.get('include_deleted', 'false').lower() == 'true'
    try:
        customer = Customer.find_by_id_with_aggregates(customer_id, include_deleted=include_deleted)
        if not customer:
            return error_response('not_found', ERROR_MESSAGES["not_found"]["customer"], 404)
        return success_response(customer_detail_schema.dump(customer), "Customer details fetched successfully")
    except Exception as e:
        return error_response('server_error', ERROR_MESSAGES["server_error"]["fetch_customer"], details=str(e), status=500)


# ---------------- Update Customer ----------------
@customers_blueprint.route('/customers/<string:customer_id>', methods=['PUT'])
@jwt_required()
@require_permission('customers.update')
def update_customer(customer_id: str):
    data = request.get_json() or {}
    if not data:
        return error_response('validation_error', ERROR_MESSAGES["validation"]["request_body_empty"], 400)

    try:
        validated_data: Dict[str, Any] = validate_request(customer_update_schema, data)
        customer_to_update = Customer.find_by_id(customer_id)
        if not customer_to_update:
            return error_response('not_found', ERROR_MESSAGES["not_found"]["customer"], 404)

        # Check email conflicts
        if 'email' in validated_data and validated_data['email']:
            existing = get_existing_customer_by_email(validated_data['email'])
            if existing and str(existing.id) != str(customer_id):
                if existing.deleted_at is None:
                    return error_response('conflict', 'A customer with this email already exists.', 409)
                return error_response(
                    'conflict_soft_deleted',
                    'A customer with this email was previously deleted. Restore?',
                    {'customer_id': str(existing.id), 'email': existing.email},
                    409
                )

        Customer.update_customer(customer_id, validated_data)
        updated_customer = Customer.find_by_id_with_aggregates(customer_id)
        return success_response(customer_summary_schema.dump(updated_customer), "Customer updated successfully.")

    except ValueError as err:
        return error_response('validation_error', "Invalid data.", details=err.args[0], status=400)
    except Exception as e:
        return error_response('server_error', ERROR_MESSAGES["server_error"]["update_customer"], details=str(e), status=500)


# ---------------- Restore Customer ----------------
@customers_blueprint.route('/customers/bulk-restore', methods=['POST'])
@jwt_required()
@require_permission('customers.restore')
def restore_customer():
    data = request.get_json() or {}
    ids_to_restore: List[str] = data.get('ids', [])

    if not ids_to_restore or not isinstance(ids_to_restore, list):
        return error_response('validation_error', "Invalid request. 'ids' must be a list.", 400)

    return bulk_action_handler(ids_to_restore, Customer.bulk_restore, "{count} customer(s) restored successfully.", "No matching customers found for the provided IDs.")


# ---------------- Bulk Delete ----------------
@customers_blueprint.route('/customers/bulk-delete', methods=['POST'])
@jwt_required()
@require_permission('customers.delete')
def bulk_delete_customers():
    data = request.get_json() or {}
    ids_to_delete: List[str] = data.get('ids', [])

    if not ids_to_delete or not isinstance(ids_to_delete, list):
        return error_response('validation_error', "Invalid request. 'ids' must be a list.", 400)

    return bulk_action_handler(ids_to_delete, Customer.bulk_soft_delete, "{count} customer(s) soft-deleted successfully.", "No matching customers found for the provided IDs.")
