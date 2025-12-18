from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError

from app.database.models.invoice import Invoice
from app.database.models.payment import Payment
from app.database.models.activity_model import ActivityLog
from app.schemas.payment_schema import PaymentSchema, PaymentDetailSchema
from app.utils.response import success_response, error_response
from app.utils.error_messages import ERROR_MESSAGES
from app.utils.auth import require_admin, require_permission
from app.utils.pagination import get_pagination
from app.utils.utils import update_invoice_status
from app.utils.helpers import validate_request, get_or_404

payments_blueprint = Blueprint('payments', __name__)

# Instantiate schema
payment_schema = PaymentSchema()

@payments_blueprint.route('/payments/search/', methods=['GET'])
@jwt_required()
def search_payments():
    """Search payments with multiple filters."""
    search_term = request.args.get('q')
    method = request.args.get('method')
    reference_no = request.args.get('reference_no')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    page, per_page = get_pagination()

    try:
        payments, total = Payment.search_payments(
            search_term=search_term,
            method=method,
            reference_no=reference_no,
            start_date=start_date,
            end_date=end_date,
            page=page,
            per_page=per_page
        )
        serialized_payments = payment_schema.dump(payments, many=True)
        return success_response(
            serialized_payments,
            message="Payments retrieved successfully.",
            meta={'total': total, 'page': page, 'per_page': per_page}
        )
    except Exception as e:
        return error_response(error_code='server_error', message="An error occurred during the search.", details=str(e), status=500)


@payments_blueprint.route('/invoices/<string:invoice_id>/pay/', methods=['POST'])
@jwt_required()
@require_permission('payments.create')
def record_payment(invoice_id):
    try:
        validated_data = validate_request(payment_schema)
    except ValueError as err:
        return error_response(error_code='validation_error', message="The provided payment data is invalid.", details=err.args[0], status=400)

    try:
        invoice = get_or_404(Invoice, invoice_id, "Invoice")
        if not invoice:
            return error_response(error_code='not_found', message=ERROR_MESSAGES["not_found"]["invoice"], status=404)

        # Ensure the invoice_id from the URL is used for the payment
        validated_data['invoice_id'] = invoice_id

        payment_id = Payment.create(validated_data)

        if payment_id:
            # Update invoice status based on new total paid
            update_invoice_status(invoice_id, invoice.total_amount)

            # Log activity
            ActivityLog.create_log(
                user_id=get_jwt_identity(),
                action='PAYMENT_RECORDED',
                entity_type='payment',
                entity_id=payment_id,
                details={
                    'invoice_id': invoice_id,
                    'invoice_number': invoice.invoice_number,
                    'amount': float(validated_data['amount']),
                    'method': validated_data['method'],
                    'reference_no': validated_data.get('reference_no')
                },
                ip_address=request.remote_addr
            )

            new_payment = Payment.find_by_id(payment_id)
            return success_response(payment_schema.dump(new_payment), message="Payment recorded successfully.", status=201)
        return error_response(error_code='server_error', message="Failed to record payment.", status=500)
    except Exception as e:
        return error_response(error_code='server_error', message="An error occurred while recording the payment.", details=str(e), status=500)


@payments_blueprint.route('/payments/', methods=['GET'])
@jwt_required()
@require_permission('payments.list')
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

@payments_blueprint.route('/invoices/<string:invoice_id>/payments/', methods=['GET'])
@jwt_required()
@require_permission('payments.view')
def get_payments_for_invoice(invoice_id):
    page, per_page = get_pagination()
    try:
        invoice = get_or_404(Invoice, invoice_id, "Invoice")
        if not invoice:
            return error_response(error_code='not_found', message=ERROR_MESSAGES["not_found"]["invoice"], status=404)

        # Get payments for this invoice
        payments, total = Payment.find_by_invoice_id_with_pagination_and_count(invoice_id, page=page, per_page=per_page)

        serialized_payments = payment_schema.dump(payments, many=True)
        return success_response(
            serialized_payments,
            message=f"Payments for invoice {invoice_id} retrieved successfully.",
            meta={'total': total, 'page': page, 'per_page': per_page}
        )
    except Exception as e:
        return error_response(error_code='server_error', message=ERROR_MESSAGES["server_error"]["fetch_payment"], details=str(e), status=500)


@payments_blueprint.route('/payments/<string:payment_id>/', methods=['GET'])
@jwt_required()
@require_permission('payments.view')
def get_payment(payment_id):
    """Get payment with customer and invoice details."""
    try:
        payment_detail_schema = PaymentDetailSchema()
        payment_data = Payment.get_payment_with_details(payment_id)
        if payment_data:
            return success_response(payment_detail_schema.dump(payment_data), message="Payment retrieved successfully.")
        return error_response(error_code='not_found', message=ERROR_MESSAGES["not_found"]["payment"], status=404)
    except Exception as e:
        return error_response(error_code='server_error', message=ERROR_MESSAGES["server_error"]["fetch_payment"], details=str(e), status=500)
