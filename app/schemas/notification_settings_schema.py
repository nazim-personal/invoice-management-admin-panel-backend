from marshmallow import Schema, fields, validate

class NotificationSettingsSchema(Schema):
    id = fields.Str(dump_only=True)
    user_id = fields.Str(dump_only=True)
    invoice_created = fields.Boolean()
    payment_received = fields.Boolean()
    invoice_overdue = fields.Boolean()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

notification_settings_schema = NotificationSettingsSchema()
