from typing import Any, Dict, List, Optional, Callable, Type
from flask import request
from marshmallow import ValidationError, Schema
from app.utils.response import error_response, success_response
from app.utils.error_messages import ERROR_MESSAGES

def validate_request(schema: Schema, data: Optional[Dict[str, Any]] = None, partial: bool = False) -> Dict[str, Any]:
    """
    Validate request data against Marshmallow schema.
    If data is not provided, it tries to get it from request.get_json().
    """
    if data is None:
        data = request.get_json() or {}

    if not data and not partial:
         # If partial is True, empty data might be valid (though rare for updates usually)
         # But generally if we expect data, we should check.
         # However, let schema handle validation if it requires fields.
         pass

    if not isinstance(data, dict):
         raise ValidationError(ERROR_MESSAGES["validation"]["request_body_empty"])

    try:
        return schema.load(data, partial=partial)
    except ValidationError as err:
        raise ValueError(err.messages)

def get_or_404(model: Type, record_id: str, resource_name: str = "resource", include_deleted: bool = False):
    """
    Fetch a record by ID or return a 404 error response.
    Returns the record instance if found.
    """
    # Check if model has find_by_id_with_aggregates (for Customer) or just find_by_id
    if hasattr(model, 'find_by_id_with_aggregates'):
        record = model.find_by_id_with_aggregates(record_id, include_deleted=include_deleted)
    else:
        record = model.find_by_id(record_id, include_deleted=include_deleted)

    if not record:
        return None
    return record

def bulk_action_handler(ids: List[str], action_func: Callable[[List[str]], int], success_msg_template: str, not_found_msg: str):
    """
    Generic handler for bulk restore / soft-delete actions.
    """
    if not ids or not isinstance(ids, list):
        return error_response('validation_error', "Invalid request. 'ids' must be a non-empty list.", 400)

    try:
        affected_count = action_func(ids)
        if affected_count > 0:
            return success_response(message=success_msg_template.format(count=affected_count))
        return error_response('not_found', not_found_msg, 404)
    except Exception as e:
        return error_response(
            'server_error',
            f"Error performing bulk action: {str(e)}",
            details=str(e),
            status=500
        )
