from marshmallow import Schema, fields

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
