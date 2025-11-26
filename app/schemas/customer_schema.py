from marshmallow import Schema, fields

class CustomerSchema(Schema):
    """Schema for validating and serializing customer data."""
    id = fields.Str(dump_only=True)
    name = fields.Str(required=True, metadata={"description": "Customer's name."})
    email = fields.Email(required=True, metadata={"description": "Unique email address."})
    phone = fields.Str(required=True, metadata={"description": "Contact phone number."})
    address = fields.Str(metadata={"description": "Physical address."})
    gst_number = fields.Str(metadata={"description": "GST identification number."})
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True, allow_none=True)

    class Meta:
        ordered = True

class CustomerUpdateSchema(Schema):
    """Schema for validating customer updates (all fields optional)."""
    name = fields.Str()
    email = fields.Email()
    phone = fields.Str()
    address = fields.Str()
    gst_number = fields.Str()

class CustomerSummarySchema(CustomerSchema):
    """Extends the base schema to include the read-only status field."""
    status = fields.Str(dump_only=True)

class CustomerDetailSchema(CustomerSummarySchema):
    """Extends the summary schema to include aggregated data for detail views."""
    aggregates = fields.Dict(dump_only=True)

class CustomerListSchema(Schema):
    """Schema for the list of customers with summary data."""
    items = fields.List(fields.Nested(lambda: CustomerSummarySchema()))
    total = fields.Int()

class BulkDeleteSchema(Schema):
    """Schema for bulk operations (e.g., deletion)."""
    ids = fields.List(fields.Str(), required=True)
