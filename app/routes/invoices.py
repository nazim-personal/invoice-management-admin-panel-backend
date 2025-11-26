from typing import Any, Dict
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from decimal import Decimal
from datetime import date

from app.database.models.customer import Customer
from app.database.models.invoice import Invoice
from app.database.models.invoice_item_model import InvoiceItem
from app.database.models.payment import Payment
from app.database.models.product import Product
from app.schemas.invoice_schema import invoice_schema
from app.utils.error_messages import ERROR_MESSAGES
from app.utils.auth import require_admin
from app.utils.response import success_response, error_response
from app.utils.pagination import get_pagination
from app.utils.utils import calculate_invoice_totals, generate_invoice_number, update_invoice_status


invoices_blueprint = Blueprint('invoices', __name__)

# ---------------------- Routes ----------------------

@invoices_blueprint.route('/invoices', methods=['GET'])
@jwt_required()
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


@invoices_blueprint.route('/invoices/<int:invoice_id>', methods=['GET'])
@jwt_required()
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
@require_admin
def create_invoice():
    data = request.get_json()
    if not data:
        return error_response('validation_error', ERROR_MESSAGES["validation"]["request_body_empty"], status=400)

    try:
        validated: Dict[str, Any] = invoice_schema.load(data)
    except ValidationError as err:
        return error_response('validation_error', 'Invalid data provided.', err.messages, 400)

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
        for i in items:
            InvoiceItem.create({
                'invoice_id': invoice_id,
                'product_id': i['product_id'],
                'quantity': int(i['quantity']),
                'price': Decimal(i['price']),
                'total': Decimal(i['price']) * int(i['quantity'])
            })
            Product.update_product(i['product_id'], {"stock_change": -i['quantity']})

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

        return success_response(result=created_invoice.to_dict(), status=201)

    except Exception as e:
        return error_response('server_error', 'Error creating invoice.', str(e), 500)


@invoices_blueprint.route('/invoices/<int:invoice_id>', methods=['PUT'])
@jwt_required()
@require_admin
def update_invoice(invoice_id: int):
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
                Product.update_stock(pid, old_items.get(pid, 0) - new_items.get(pid, 0))

            # Replace invoice items
            InvoiceItem.delete_by_invoice_id(invoice_id)
            for i in validated['items']:
                product = Product.find_by_id(i['product_id'])
                if not product:
                    return error_response('not_found', f"Product ID {i['product_id']} not found.", 404)
                InvoiceItem.create({
                    'invoice_id': invoice_id,
                    'product_id': i['product_id'],
                    'quantity': i['quantity'],
                    'price': product.price
                })

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
            total = invoice.total_amount

        # --- Update invoice and status ---
        validated.pop('items', None)
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

        return success_response(result=result, status=200)

    except Exception as e:
        return error_response('server_error', 'Error updating invoice.', str(e), 500)