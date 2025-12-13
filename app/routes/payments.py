from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from marshmallow import ValidationError

from app.database.models.invoice import Invoice
from app.database.models.payment import Payment
from app.schemas.payment_schema import PaymentSchema
from app.utils.response import success_response, error_response
from app.utils.error_messages import ERROR_MESSAGES
from app.utils.auth import require_admin, require_permission
from app.utils.pagination import get_pagination
from app.utils.utils import update_invoice_status

payments_blueprint = Blueprint('payments', __name__)

# Instantiate schema
payment_schema = PaymentSchema()

@payments_blueprint.route('/payments/search', methods=['GET'])
@jwt_required()
def search_payments():
    search_term = request.args.get('q')
    if not search_term:
        return error_response(error_code='validation_error', message="Search term 'q' is required.", status=400)

    try:
        payments = Payment.search(search_term)
        serialized_payments = payment_schema.dump(payments, many=True)
        return success_response(serialized_payments, message="Payments matching the search term retrieved successfully.")
    except Exception as e:
        return error_response(error_code='server_error', message="An error occurred during the search.", details=str(e), status=500)


@payments_blueprint.route('/invoices/<string:invoice_id>/pay', methods=['POST'])
@jwt_required()
@require_permission('payments.create')
def record_payment(invoice_id):
    data = request.get_json()
    if not data:
        return error_response(error_code='validation_error', message=ERROR_MESSAGES["validation"]["request_body_empty"], status=400)

    try:
        validated_data = payment_schema.load(data)
    except ValidationError as err:
        return error_response(error_code='validation_error', message="The provided payment data is invalid.", details=err.messages, status=400)

    try:
        invoice = Invoice.find_by_id(invoice_id)
        if not invoice:
            return error_response(error_code='not_found', message=ERROR_MESSAGES["not_found"]["invoice"], status=404)

        # Ensure the invoice_id from the URL is used for the payment
        validated_data['invoice_id'] = invoice_id

        payment_id = Payment.create(validated_data)

        if payment_id:
            # Update invoice status based on new total paid
            update_invoice_status(invoice_id, invoice.total_amount)

            new_payment = Payment.find_by_id(payment_id)
            return success_response(payment_schema.dump(new_payment), message="Payment recorded successfully.", status=201)
        return error_response(error_code='server_error', message="Failed to record payment.", status=500)
    except Exception as e:
        return error_response(error_code='server_error', message="An error occurred while recording the payment.", details=str(e), status=500)


@payments_blueprint.route('/payments', methods=['GET'])
@jwt_required()
@require_permission('payments.view')
def get_all_payments():
    page, per_page = get_pagination()
    try:
        payments, total = Payment.find_with_pagination_and_count(page=page, per_page=per_page)
        serialized_payments = payment_schema.dump(payments, many=True)
        return success_response(
            serialized_payments,
            message="Payments retrieved successfully.",
            meta={'total': total, 'page': page, 'per_page': per_page}
        )
    except Exception as e:
        return error_response(error_code='server_error', message=ERROR_MESSAGES["server_error"]["fetch_payment"], details=str(e), status=500)

@payments_blueprint.route('/invoices/<string:invoice_id>/payments', methods=['GET'])
@jwt_required()
@require_permission('payments.view')
def get_payments_for_invoice(invoice_id):
    page, per_page = get_pagination()
    try:
        invoice = Invoice.find_by_id(invoice_id)
        if not invoice:
            return error_response(error_code='not_found', message=ERROR_MESSAGES["not_found"]["invoice"], status=404)

        # Get payments for this invoice - using find_with_pagination if available
        # For now, return all payments filtered by invoice_id
        try:
            payments, total = Payment.find_by_invoice_id_with_pagination_and_count(invoice_id, page=page, per_page=per_page)
        except AttributeError:
            # Fallback if the method doesn't exist
            all_payments = Payment.find_all()
            filtered = [p for p in all_payments if str(p.invoice_id) == str(invoice_id)]
            start = (page - 1) * per_page
            end = start + per_page
            payments = filtered[start:end]
            total = len(filtered)

        serialized_payments = payment_schema.dump(payments, many=True)
        return success_response(
            serialized_payments,
            message=f"Payments for invoice {invoice_id} retrieved successfully.",
            meta={'total': total, 'page': page, 'per_page': per_page}
        )
    except Exception as e:
        return error_response(error_code='server_error', message=ERROR_MESSAGES["server_error"]["fetch_payment"], details=str(e), status=500)


@payments_blueprint.route('/payments/<int:payment_id>', methods=['GET'])
@jwt_required()
@require_permission('payments.view')
def get_payment(payment_id):
    try:
        payment = Payment.find_by_id(payment_id)
        if payment:
            return success_response(payment_schema.dump(payment), message="Payment retrieved successfully.")
        return error_response(error_code='not_found', message=ERROR_MESSAGES["not_found"]["payment"], status=404)
    except Exception as e:
        return error_response(error_code='server_error', message=ERROR_MESSAGES["server_error"]["fetch_payment"], details=str(e), status=500)
