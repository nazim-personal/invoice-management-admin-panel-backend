from typing import Any, Dict, List
from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from marshmallow import ValidationError

from app.database.models.product import Product
from app.schemas.product_schema import ProductSchema
from app.utils.response import success_response, error_response
from app.utils.error_messages import ERROR_MESSAGES
from app.utils.auth import require_admin, require_permission
from app.utils.pagination import get_pagination

products_blueprint = Blueprint('products', __name__)

product_schema = ProductSchema()
product_update_schema = ProductSchema(partial=True)


def validate_json(schema: ProductSchema, partial: bool = False) -> Dict[str, Any]:
    """
    Helper function to validate request JSON using Marshmallow schema.
    Ensures the request JSON is a dictionary before validation.
    """
    raw_data = request.get_json()
    if not raw_data or not isinstance(raw_data, dict):
        raise ValidationError(ERROR_MESSAGES["validation"]["request_body_empty"])

    validated_data: Dict[str, Any] = schema.load(raw_data, partial=partial)
    return validated_data



@products_blueprint.route('/products/search', methods=['GET'])
@jwt_required()
def search_products():
    search_term = request.args.get('q')
    if not search_term:
        return error_response(error_code='validation_error', message="Search term 'q' is required.", status=400)

    include_deleted = request.args.get('include_deleted', 'false').lower() == 'true'
    try:
        products, _ = Product.search_product(search_term, include_deleted=include_deleted)
        return success_response(product_schema.dump(products, many=True),
                                message="Products matching the search term retrieved successfully.")
    except Exception as e:
        return error_response('server_error', "Error occurred during search.", details=str(e), status=500)


@products_blueprint.route('/products', methods=['POST'])
@jwt_required()
@require_permission('products.create')
def create_product():
    try:
        validated_data = validate_json(product_schema)
        product_id = Product.create_product(validated_data)
        product = Product.find_by_id(product_id)
        if product:
            return success_response(product_schema.dump(product),
                                    message="Product created successfully.", status=201)
        return error_response('server_error', ERROR_MESSAGES["server_error"]["create_product"], status=500)
    except ValidationError as err:
        return error_response('validation_error', message="Invalid data.", details=err.messages, status=400)
    except Exception as e:
        return error_response('server_error', ERROR_MESSAGES["server_error"]["create_product"], details=str(e), status=500)


@products_blueprint.route('/products', methods=['GET'])
@jwt_required()
@require_permission('products.view')
def get_products():
    page, per_page = get_pagination()
    include_deleted = request.args.get('include_deleted', 'false').lower() == 'true'
    try:
        products, total = Product.find_with_pagination_and_count(page=page, per_page=per_page, include_deleted=include_deleted)
        return success_response(product_schema.dump(products, many=True),
                                meta={'total': total, 'page': page, 'per_page': per_page},
                                message="Products retrieved successfully.")
    except Exception as e:
        return error_response('server_error', ERROR_MESSAGES["server_error"]["fetch_product"], details=str(e), status=500)


@products_blueprint.route('/products/<string:product_id>', methods=['GET'])
@jwt_required()
@require_permission('products.view')
def get_product(product_id):
    include_deleted = request.args.get('include_deleted', 'false').lower() == 'true'
    try:
        product = Product.find_by_id(product_id, include_deleted=include_deleted)
        if product:
            return success_response(product_schema.dump(product), message="Product retrieved successfully.")
        return error_response('not_found', ERROR_MESSAGES["not_found"]["product"], status=404)
    except Exception as e:
        return error_response('server_error', ERROR_MESSAGES["server_error"]["fetch_product"], details=str(e), status=500)


@products_blueprint.route('/products/<string:product_id>', methods=['PUT'])
@jwt_required()
@require_permission('products.update')
def update_product(product_id):
    try:
        validated_data = validate_json(product_update_schema, partial=True)
        if not Product.update_product(product_id, validated_data):
            return error_response('not_found', ERROR_MESSAGES["not_found"]["product"], status=404)
        updated_product = Product.find_by_id(product_id)
        return success_response(product_schema.dump(updated_product), message="Product updated successfully.")
    except ValidationError as err:
        return error_response('validation_error', message="Invalid data.", details=err.messages, status=400)
    except Exception as e:
        return error_response('server_error', ERROR_MESSAGES["server_error"]["update_product"], details=str(e), status=500)

def bulk_action_handler(ids: List[str], action_func, success_msg: str, not_found_msg: str):
    """
    Generic handler for bulk restore / soft-delete actions.
    """
    if not ids:  # Only check for empty list
        return error_response('validation_error', "Invalid request. 'ids' must be a non-empty list.", 400)

    try:
        affected_count = action_func(ids)
        if affected_count > 0:
            return success_response(message=f"{affected_count} product(s) {success_msg}")
        return error_response('not_found', not_found_msg, 404)
    except Exception as e:
        return error_response(
            'server_error',
            ERROR_MESSAGES["server_error"].get(success_msg.replace(" ", "_"), success_msg),
            details=str(e),
            status=500
        )


@products_blueprint.route('/products/bulk-restore', methods=['POST'])
@jwt_required()
@require_permission('products.restore')
def bulk_restore_products():
    data = request.get_json() or {}
    ids = data.get('ids', [])
    return bulk_action_handler(ids, Product.bulk_restore, "restored successfully", "No matching product found for the provided IDs.")


@products_blueprint.route('/products/bulk-delete', methods=['POST'])
@jwt_required()
@require_permission('products.delete')
def bulk_delete_products():
    data = request.get_json() or {}
    ids = data.get('ids', [])
    return bulk_action_handler(ids, Product.bulk_soft_delete, "soft-deleted successfully", "No matching products found for the provided IDs.")
