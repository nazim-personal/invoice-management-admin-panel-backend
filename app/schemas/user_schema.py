from marshmallow import Schema, fields, validate

class UserUpdateSchema(Schema):
    """Schema for validating user profile updates (all fields optional)."""
    name = fields.Str()
    email = fields.Email()
    phone = fields.Str()
    password = fields.Str(load_only=True)
    old_password = fields.Str(load_only=True)
    billing_address = fields.Str()
    billing_city = fields.Str()
    billing_state = fields.Str()
    billing_pin = fields.Str()
    billing_gst = fields.Str()
    role = fields.Str(validate=validate.OneOf(['admin', 'staff', 'manager']))
    permissions = fields.List(fields.Str())


class ProfileUpdateSchema(Schema):
    """Schema for updating basic profile information."""
    name = fields.Str()
    email = fields.Email()
    phone = fields.Str()


class PasswordChangeSchema(Schema):
    """Schema for changing password."""
    old_password = fields.Str(required=True, validate=validate.Length(min=1))
    new_password = fields.Str(
        required=True,
        validate=validate.Length(min=6, error="Password must be at least 6 characters long")
    )


class BillingInfoSchema(Schema):
    """Schema for billing information."""
    billing_address = fields.Str()
    billing_city = fields.Str()
    billing_state = fields.Str()
    billing_pin = fields.Str()
    billing_gst = fields.Str()
