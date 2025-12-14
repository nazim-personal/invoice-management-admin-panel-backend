from marshmallow import Schema, fields, validate
from datetime import date

# Schema for validating an initial payment made during invoice creation.
class InitialPaymentSchema(Schema):
    amount = fields.Decimal(
        places=2,
        as_string=True,
        required=True,
        validate=validate.Range(min=0.01, error="Payment amount must be positive.")
    )
    # The payment method. Aligns with the database ENUM.
    method = fields.Str(
        required=True,
        validate=validate.OneOf(["cash", "card", "upi", "bank_transfer"], error="Invalid payment method.")
    )
    # An optional payment reference number (e.g., transaction ID).
    reference_no = fields.Str(allow_none=True)


# Schema for validating a payment record against an existing invoice.
class PaymentSchema(Schema):
    id = fields.Str(dump_only=True)
    invoice_id = fields.Str(
        required=True,
        validate=validate.Range(min=1, error="Invoice ID must be a positive integer.")
    )
    amount = fields.Decimal(
        places=2,
        as_string=True,
        required=True,
        validate=validate.Range(min=0.01, error="Payment amount must be positive.")
    )
    # Payment date is optional; defaults to the current date if not provided.
    payment_date = fields.Date(allow_none=True, load_default=date.today)
    # The payment method. Renamed from payment_method to be consistent.
    method = fields.Str(
        required=True,
        validate=validate.OneOf(["cash", "card", "upi", "bank_transfer"], error="Invalid payment method.")
    )
    reference_no = fields.Str(allow_none=True)
    created_at = fields.DateTime(dump_only=True)


# Schema for payment with customer and invoice details
class PaymentDetailSchema(Schema):
    id = fields.Str()
    invoice_id = fields.Str()
    amount = fields.Decimal(places=2, as_string=True)
    payment_date = fields.Date()
    method = fields.Str()
    reference_no = fields.Str(allow_none=True)
    created_at = fields.DateTime()

    # Invoice details
    invoice_number = fields.Str()
    invoice_total = fields.Decimal(places=2, as_string=True)

    # Customer details
    customer_id = fields.Str()
    customer_name = fields.Str()
    customer_email = fields.Str()
