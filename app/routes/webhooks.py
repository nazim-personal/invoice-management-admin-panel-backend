import base64
import json
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from app.services.phonepe_service import phonepe_service
from app.database.models.invoice import Invoice
from app.database.models.payment import Payment
from app.database.models.activity_model import ActivityLog
from app.utils.response import success_response, error_response
from app.utils.utils import update_invoice_status
from decimal import Decimal

webhooks_bp = Blueprint('webhooks', __name__)

@webhooks_bp.route('/webhooks/phonepe/', methods=['POST'])
def phonepe_webhook():
    """
    Receive and process PhonePe payment webhook notifications.
    This endpoint is called by PhonePe when payment status changes.
    """
    try:
        # Get the request data
        data = request.get_json()

        if not data or 'response' not in data:
            return error_response(
                error_code='invalid_request',
                message='Invalid webhook payload',
                status=400
            )

        # Extract base64 encoded response
        base64_response = data['response']
        x_verify_header = request.headers.get('X-VERIFY')

        if not x_verify_header:
            return error_response(
                error_code='unauthorized',
                message='Missing X-VERIFY header',
                status=401
            )

        # Verify webhook signature
        if not phonepe_service.verify_webhook_signature(x_verify_header, base64_response):
            return error_response(
                error_code='unauthorized',
                message='Invalid webhook signature',
                status=401
            )

        # Decode the response
        decoded_response = base64.b64decode(base64_response).decode('utf-8')
        response_data = json.loads(decoded_response)

        # Extract payment information
        payment_state = response_data.get('code')  # SUCCESS, PAYMENT_ERROR, etc.
        transaction_data = response_data.get('data', {})
        merchant_transaction_id = transaction_data.get('merchantTransactionId')
        phonepe_transaction_id = transaction_data.get('transactionId')
        amount_in_paise = transaction_data.get('amount', 0)
        amount = Decimal(amount_in_paise) / 100  # Convert paise to rupees

        # Extract invoice ID from merchant transaction ID (format: INV_{invoice_id}_{random})
        if not merchant_transaction_id or not merchant_transaction_id.startswith('INV_'):
            return error_response(
                error_code='invalid_transaction',
                message='Invalid merchant transaction ID format',
                status=400
            )

        # Parse invoice ID from transaction ID
        parts = merchant_transaction_id.split('_')
        if len(parts) < 2:
            return error_response(
                error_code='invalid_transaction',
                message='Cannot extract invoice ID from transaction',
                status=400
            )

        invoice_id = parts[1]

        # Get the invoice
        invoice = Invoice.find_by_id(invoice_id)
        if not invoice:
            return error_response(
                error_code='not_found',
                message=f'Invoice {invoice_id} not found',
                status=404
            )

        # Process based on payment state
        if payment_state == 'PAYMENT_SUCCESS':
            # Check if payment already recorded (prevent duplicate)
            existing_payment = Payment.find_by_transaction_id(merchant_transaction_id)
            if existing_payment:
                return success_response(
                    result={'message': 'Payment already processed'},
                    message='Duplicate webhook ignored'
                )

            # Record the payment
            payment_data = {
                'invoice_id': invoice_id,
                'amount': amount,
                'payment_date': None,  # Will use current date
                'method': 'upi',
                'reference_no': phonepe_transaction_id,
                'transaction_id': merchant_transaction_id,
                'payment_gateway': 'phonepe',
                'gateway_response': json.dumps(response_data)
            }

            payment_id = Payment.create(payment_data)

            if payment_id:
                # Update invoice status
                update_invoice_status(invoice_id, invoice.total_amount)

                # Log activity
                ActivityLog.create_log(
                    user_id=invoice.customer_id,  # Use customer as user for auto-payments
                    action='PAYMENT_RECEIVED_PHONEPE',
                    entity_type='invoice',
                    entity_id=invoice_id,
                    details={
                        'amount': float(amount),
                        'payment_gateway': 'phonepe',
                        'transaction_id': merchant_transaction_id,
                        'phonepe_transaction_id': phonepe_transaction_id
                    },
                    ip_address=request.remote_addr
                )

                return success_response(
                    result={
                        'payment_id': payment_id,
                        'invoice_id': invoice_id,
                        'amount': float(amount),
                        'status': 'success'
                    },
                    message='Payment processed successfully'
                )
            else:
                return error_response(
                    error_code='server_error',
                    message='Failed to record payment',
                    status=500
                )

        elif payment_state == 'PAYMENT_ERROR' or payment_state == 'PAYMENT_DECLINED':
            # Log failed payment attempt
            ActivityLog.create_log(
                user_id=invoice.customer_id,
                action='PAYMENT_FAILED_PHONEPE',
                entity_type='invoice',
                entity_id=invoice_id,
                details={
                    'amount': float(amount),
                    'payment_gateway': 'phonepe',
                    'transaction_id': merchant_transaction_id,
                    'error_code': payment_state,
                    'error_message': response_data.get('message', 'Payment failed')
                },
                ip_address=request.remote_addr
            )

            return success_response(
                result={'status': 'failed', 'message': 'Payment failed'},
                message='Payment failure recorded'
            )

        else:
            # Payment pending or other status
            return success_response(
                result={'status': payment_state},
                message='Payment status updated'
            )

    except json.JSONDecodeError:
        return error_response(
            error_code='invalid_request',
            message='Invalid JSON in webhook payload',
            status=400
        )
    except Exception as e:
        return error_response(
            error_code='server_error',
            message='Webhook processing failed',
            details=str(e),
            status=500
        )
