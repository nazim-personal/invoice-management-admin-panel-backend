from typing import Any, Dict, List
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from decimal import Decimal
from datetime import date

from app.database.models.customer import Customer
from app.database.models.invoice import Invoice
from app.database.models.invoice_item_model import InvoiceItem
from app.database.models.payment import Payment
from app.database.models.payment import Payment
from app.database.models.product import Product
from app.database.models.user import User
from app.schemas.invoice_schema import invoice_schema
from app.utils.error_messages import ERROR_MESSAGES
from app.utils.auth import require_admin, require_permission
from app.utils.response import success_response, error_response
from app.utils.pagination import get_pagination
from app.utils.utils import calculate_invoice_totals, generate_invoice_number, update_invoice_status
from app.utils.pdf_generator import InvoicePDFGenerator
from app.utils.helpers import validate_request, get_or_404, bulk_action_handler
from app.database.models.activity_model import ActivityLog


invoices_blueprint = Blueprint('invoices', __name__)

# ---------------------- Routes ----------------------

@invoices_blueprint.route('/invoices', methods=['GET'])
@jwt_required()
@require_permission('invoices.list')
def list_invoices():
    try:
        page, per_page = get_pagination()
        filters = {
            'status': request.args.get('status'),
            'customer_id': request.args.get('customer_id'),
            'q': request.args.get('q'),
        }

        offset = (page - 1) * per_page
        invoices, total = Invoice.list_all(
            customer_id=filters['customer_id'],
            status=filters['status'],
            q=filters['q'],
            offset=offset,
            limit=per_page
        )

        return success_response(
            result = [inv.to_dict() for inv in invoices if inv is not None],
            meta={'total': total, 'page': page, 'per_page': per_page},
            status=200
        )

    except Exception as e:
        return error_response('server_error', 'Failed to fetch invoices.', str(e), 500)


@invoices_blueprint.route('/invoices/<string:invoice_id>', methods=['GET'])
@jwt_required()
@require_permission('invoices.view')
def get_invoice(invoice_id):
    try:
        invoice = Invoice.find_by_id(invoice_id)
        if not invoice:
            return error_response('not_found', ERROR_MESSAGES["not_found"]["invoice"], status=404)

        customer = Customer.find_by_id(invoice.customer_id)
        items = InvoiceItem.find_by_invoice_id(invoice_id)
        payment = Payment.find_latest_by_invoice_id(invoice_id)

        invoice_data = {
            **invoice.to_dict(),
            'customer': customer.to_dict() if customer else None,
            'items': [i.to_dict() for i in items if i is not None],
            'payment': payment.to_dict() if payment else None
        }

        return success_response(result=invoice_data, status=200)

    except Exception as e:
        return error_response('server_error', 'Failed to fetch invoice.', str(e), 500)


@invoices_blueprint.route('/invoices', methods=['POST'])
@jwt_required()
@require_permission('invoices.create')
def create_invoice():
    data = request.get_json()
    if not data:
        return error_response('validation_error', ERROR_MESSAGES["validation"]["request_body_empty"], status=400)

    try:
        validated = validate_request(invoice_schema)
    except ValueError as err:
        return error_response('validation_error', 'Invalid data provided.', err.args[0], 400)

    try:
        customer = Customer.find_by_id(validated['customer_id'])
        if not customer:
            return error_response('not_found', ERROR_MESSAGES["not_found"]["customer"], 404)

        # Prepare product data
        items = []
        for item in validated['items']:
            product = Product.find_by_id(item['product_id'])
            if not product:
                return error_response('not_found', f"Product ID {item['product_id']} not found.", 404)
            items.append({'price': product.price, **item})

        discount = Decimal(validated.get('discount_amount', '0.00'))
        tax_percent = Decimal(validated.get('tax_percent', '0.00'))
        subtotal, tax, total = calculate_invoice_totals(items, discount, tax_percent)

        invoice_data = {
            'customer_id': validated['customer_id'],
            'user_id': get_jwt_identity(),
            'invoice_number': generate_invoice_number(customer.id),
            'due_date': validated.get('due_date'),
            'subtotal_amount': subtotal,
            'discount_amount': discount,
            'tax_percent': tax_percent,
            'tax_amount': tax,
            'total_amount': total,
            'status': 'Pending'
        }

        # Handle initial payment
        initial_payment = validated.get('initial_payment')
        if initial_payment:
            pay_amount = Decimal(initial_payment['amount'])
            if pay_amount >= total:
                invoice_data['status'] = 'Paid'
            elif pay_amount > 0:
                invoice_data['status'] = 'Partially Paid'

        # Create invoice
        invoice_id = Invoice.create_invoice(invoice_data)
        if not invoice_id:
            return error_response('server_error', "Invoice creation failed.", 500)

        # Create invoice items & update stock
        items_data = []
        for i in items:
            items_data.append({
                'invoice_id': invoice_id,
                'product_id': i['product_id'],
                'quantity': int(i['quantity']),
                'price': Decimal(i['price']),
                'total': Decimal(i['price']) * int(i['quantity'])
            })
            Product.update_product(i['product_id'], {"stock_change": -i['quantity']})

        InvoiceItem.bulk_create(items_data)

        # Record initial payment
        if initial_payment:
            Payment.record_payment({
                'invoice_id': invoice_id,
                'amount': Decimal(initial_payment['amount']),
                'payment_date': date.today(),
                'method': initial_payment['method'],
                'reference_no': initial_payment.get('reference_no')
            })

        created_invoice = Invoice.find_by_id(invoice_id)
        if not created_invoice:
            return error_response('not_found', 'Created invoice not found.', 404)

        # Log activity
        ActivityLog.create_log(
            user_id=get_jwt_identity(),
            action='INVOICE_CREATED',
            entity_type='invoice',
            entity_id=invoice_id,
            details={'invoice_number': invoice_data['invoice_number'], 'total': float(total)},
            ip_address=request.remote_addr
        )

        return success_response(result=created_invoice.to_dict(), status=201)

    except Exception as e:
        return error_response('server_error', 'Error creating invoice.', str(e), 500)


@invoices_blueprint.route('/invoices/<string:invoice_id>', methods=['PUT'])
@jwt_required()
@require_permission('invoices.update')
def update_invoice(invoice_id: str):
    data = request.get_json()
    if not data:
        return error_response('validation_error', ERROR_MESSAGES["validation"]["request_body_empty"], 400)

    invoice = Invoice.find_by_id(invoice_id)
    if not invoice:
        return error_response('not_found', ERROR_MESSAGES["not_found"]["invoice"], 404)

    try:
        validated: Dict[str, Any] = invoice_schema.load(data, partial=True)
    except ValidationError as err:
        return error_response('validation_error', 'Invalid data provided.', err.messages, 400)

    try:
        # --- Handle item updates ---
        if 'items' in validated:
            old_items = {i.product_id: i.quantity for i in InvoiceItem.find_by_invoice_id(invoice_id) if i is not None}
            new_items = {i['product_id']: i['quantity'] for i in validated['items']}
            all_pids = set(old_items) | set(new_items)

            # Adjust stock differences
            for pid in all_pids:
                stock_change = old_items.get(pid, 0) - new_items.get(pid, 0)
                Product.update_product(pid, {"stock_change": stock_change})

            # Replace invoice items
            InvoiceItem.delete_by_invoice_id(invoice_id)
            items_data = []
            for i in validated['items']:
                product = Product.find_by_id(i['product_id'])
                if not product:
                    return error_response('not_found', f"Product ID {i['product_id']} not found.", 404)
                items_data.append({
                    'invoice_id': invoice_id,
                    'product_id': i['product_id'],
                    'quantity': int(i['quantity']),
                    'price': Decimal(product.price),
                    'total': Decimal(product.price) * int(i['quantity'])
                })
            InvoiceItem.bulk_create(items_data)

        # --- Recalculate totals if needed ---
        if {'items', 'discount_amount', 'tax_percent'} & validated.keys():
            current_items = InvoiceItem.find_by_invoice_id(invoice_id)
            items_data = [{'price': i.price, 'quantity': i.quantity} for i in current_items if i is not None]
            subtotal, tax, total = calculate_invoice_totals(
                items_data,
                Decimal(validated.get('discount_amount', invoice.discount_amount)),
                Decimal(validated.get('tax_percent', invoice.tax_percent))
            )
            validated.update({
                'subtotal_amount': subtotal,
                'tax_amount': tax,
                'total_amount': total
            })
        else:
            total = Decimal(invoice.total_amount)

        # --- Handle "Mark as Paid" ---
        if validated.get('is_mark_as_paid'):
            # Calculate amount to pay
            total_amount = Decimal(invoice.total_amount)
            # If items were updated, use the new total
            if 'total_amount' in validated:
                total_amount = validated['total_amount']

            # Get already paid amount
            paid_amount = Payment.get_total_paid(invoice_id)
            remaining_balance = total_amount - paid_amount

            payment_amount = Decimal(validated.get('amount_paid') or remaining_balance)

            if payment_amount > 0:
                Payment.record_payment({
                    'invoice_id': invoice_id,
                    'amount': payment_amount,
                    'payment_date': date.today(),
                    'method': 'cash', # Default to cash if not specified
                    'reference_no': f'Marked as paid via API'
                })

                # Log activity
                ActivityLog.create_log(
                    user_id=get_jwt_identity(),
                    action='PAYMENT_RECORDED',
                    entity_type='invoice',
                    entity_id=invoice_id,
                    details={'amount': float(payment_amount), 'method': 'cash'},
                    ip_address=request.remote_addr
                )

        # --- Update invoice and status ---
        # Remove non-model fields
        validated.pop('items', None)
        validated.pop('is_mark_as_paid', None)
        validated.pop('amount_paid', None)

        if validated:
            Invoice.update(invoice_id, validated)

        update_invoice_status(invoice_id, total)

        # --- Fetch updated data safely ---
        updated_invoice = Invoice.find_by_id(invoice_id)
        if not updated_invoice:
            return error_response('not_found', ERROR_MESSAGES["not_found"]["invoice"], 404)

        customer = Customer.find_by_id(updated_invoice.customer_id)
        customer_data = customer.to_dict() if customer else None

        items = [i.to_dict() for i in InvoiceItem.find_by_invoice_id(invoice_id) if i is not None]
        payments = [p.to_dict() for p in Payment.find_by_invoice_id(invoice_id) if p is not None]

        result = {
            **updated_invoice.to_dict(),
            'customer': customer_data,
            'items': items,
            'payments': payments
        }

        # Log activity
        ActivityLog.create_log(
            user_id=get_jwt_identity(),
            action='INVOICE_UPDATED',
            entity_type='invoice',
            entity_id=invoice_id,
            details=validated, # Log what changed
            ip_address=request.remote_addr
        )

        return success_response(result=result, status=200)

    except Exception as e:
        return error_response('server_error', 'Error updating invoice.', str(e), 500)


# ---------------- Bulk Restore ----------------
@invoices_blueprint.route('/invoices/bulk-restore', methods=['POST'])
@jwt_required()
@require_permission('invoices.restore')
def restore_invoices():
    data = request.get_json() or {}
    ids_to_restore: List[str] = data.get('ids', [])

    if not ids_to_restore or not isinstance(ids_to_restore, list):
        return error_response('validation_error', "Invalid request. 'ids' must be a list.", 400)

    return bulk_action_handler(ids_to_restore, Invoice.bulk_restore, "{count} invoice(s) restored successfully.", "No matching invoices found for the provided IDs.")


# ---------------- Bulk Delete ----------------
@invoices_blueprint.route('/invoices/bulk-delete', methods=['POST'])
@jwt_required()
@require_permission('invoices.delete')
def bulk_delete_invoices():
    data = request.get_json() or {}
    ids_to_delete: List[str] = data.get('ids', [])

    if not ids_to_delete or not isinstance(ids_to_delete, list):
        return error_response('validation_error', "Invalid request. 'ids' must be a list.", 400)

    return bulk_action_handler(ids_to_delete, Invoice.bulk_soft_delete, "{count} invoice(s) soft-deleted successfully.", "No matching invoices found for the provided IDs.")


# ---------------- PDF Generation ----------------
@invoices_blueprint.route('/invoices/<string:invoice_id>/pdf', methods=['GET'])
@jwt_required()
@require_permission('invoices.view')
def generate_invoice_pdf(invoice_id: str):
    """
    Generate and download professional invoice PDF with QR code
    """
    try:
        from flask import send_file

        # Fetch invoice with all related data
        invoice = Invoice.find_by_id(invoice_id)
        if not invoice:
            return error_response('not_found', ERROR_MESSAGES["not_found"]["invoice"], 404)

        # Get customer details
        customer = Customer.find_by_id(invoice.customer_id)
        if not customer:
            return error_response('not_found', "Customer not found for this invoice.", 404)

        # Get invoice items
        items = InvoiceItem.find_by_invoice_id(invoice_id)

        # Format invoice data for PDF
        invoice_data = {
            'invoice_number': invoice.invoice_number,
            'invoice_date': invoice.invoice_date.strftime('%b %d, %Y') if invoice.invoice_date else 'N/A',
            'due_date': invoice.due_date.strftime('%b %d, %Y') if invoice.due_date else 'N/A',
            'status': invoice.status,
            'payment_terms': getattr(invoice, 'payment_terms', '30'),
            'notes': getattr(invoice, 'notes', 'Thank you for your business!'),  # Dynamic notes
            'customer': {
                'name': customer.name or 'N/A',
                'address': customer.address or '',
                'city': customer.city or '',
                'state': customer.state or '',
                'gst_number': customer.gst_number or 'N/A'
            },
            'items': [],
            'subtotal': float(invoice.subtotal) if invoice.subtotal else 0.0,
            'tax_amount': float(invoice.tax_amount) if invoice.tax_amount else 0.0,
            'total': float(invoice.total) if invoice.total else 0.0
        }

        # Add items with product details
        for item in items:
            product = Product.find_by_id(item.product_id)
            invoice_data['items'].append({
                'product_name': product.name if product else 'Unknown Product',
                'quantity': item.quantity,
                'price': float(item.unit_price) if item.unit_price else 0.0,
                'tax_rate': float(item.tax_rate) if item.tax_rate else 0.0,
                'total': float(item.total_price) if item.total_price else 0.0
            })

        # Get current user for company details
        current_user_id = get_jwt_identity()
        current_user = User.find_by_id(current_user_id)

        # Generate PDF
        pdf_generator = InvoicePDFGenerator(user=current_user)
        pdf_buffer = pdf_generator.generate_invoice_pdf(invoice_data)

        # Send PDF as file download
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'invoice-{invoice.invoice_number}.pdf'
        )

    except Exception as e:
        return error_response('server_error', 'Error generating invoice PDF.', details=str(e), status=500)


@invoices_blueprint.route('/invoices/<string:invoice_id>/phonepe-payment/', methods=['POST'])
@jwt_required()
@require_permission('invoices.view')
def initiate_phonepe_payment(invoice_id):
    """
    Initiate PhonePe payment for an invoice.
    Returns payment URL for customer to complete payment.
    """
    try:
        from app.services.phonepe_service import phonepe_service

        # Get invoice
        invoice = Invoice.find_by_id(invoice_id)
        if not invoice:
            return error_response('not_found', ERROR_MESSAGES["not_found"]["invoice"], status=404)

        # Get customer details
        customer = Customer.find_by_id(invoice.customer_id)
        if not customer:
            return error_response('not_found', 'Customer not found for this invoice', status=404)

        # Calculate remaining amount to be paid
        total_paid = Payment.get_total_paid(invoice_id)
        remaining_amount = invoice.total_amount - total_paid

        if remaining_amount <= 0:
            return error_response(
                'validation_error',
                'Invoice is already fully paid',
                status=400
            )

        # Initiate PhonePe payment
        result = phonepe_service.initiate_payment(
            invoice_id=invoice_id,
            amount=remaining_amount,
            customer_phone=customer.phone or '9999999999',  # Fallback phone
            customer_name=customer.name
        )

        if result.get('success'):
            # Log activity
            ActivityLog.create_log(
                user_id=get_jwt_identity(),
                action='PHONEPE_PAYMENT_INITIATED',
                entity_type='invoice',
                entity_id=invoice_id,
                details={
                    'amount': float(remaining_amount),
                    'transaction_id': result.get('transaction_id'),
                    'customer_id': customer.id
                },
                ip_address=request.remote_addr
            )

            return success_response(
                result={
                    'payment_url': result.get('payment_url'),
                    'transaction_id': result.get('transaction_id'),
                    'amount': float(remaining_amount)
                },
                message='PhonePe payment initiated successfully',
                status=200
            )
        else:
            return error_response(
                'phonepe_error',
                result.get('message', 'Failed to initiate PhonePe payment'),
                details=result.get('error_code'),
                status=500
            )

    except Exception as e:
        return error_response('server_error', 'Error initiating PhonePe payment', details=str(e), status=500)