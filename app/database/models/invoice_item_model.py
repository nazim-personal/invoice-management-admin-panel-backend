
from .base_model import BaseModel
from app.database.db_manager import DBManager
from decimal import Decimal

class InvoiceItem(BaseModel):
    _table_name = 'invoice_items'

    def __init__(self, **kwargs):
        # Let the base model set all attributes from the database row
        super().__init__(**kwargs)

        # Now, specifically override and forcefully cast the attributes to their correct types.
        # This corrects any automatic type conversions (e.g., INT to Decimal) by the DB driver.
        if hasattr(self, 'quantity') and self.quantity is not None:
            self.quantity = int(self.quantity)
        
        if hasattr(self, 'price') and self.price is not None:
            self.price = Decimal(self.price)

        if hasattr(self, 'total') and self.total is not None:
            self.total = Decimal(self.total)

    def to_dict(self):
        # Ensure price and total are converted to float for JSON serialization
        price_float = float(self.price) if self.price is not None else 0.0
        total_float = float(self.total) if self.total is not None else 0.0
        
        product_details = {
            'name': getattr(self, 'product_name', None),
            'product_code': getattr(self, 'product_code', None),
            'description': getattr(self, 'product_description', None),
            'stock': getattr(self, 'stock', None)
        }

        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'product_id': self.product_id,
            'quantity': self.quantity, # Guaranteed to be an int
            'price': price_float,
            'total': total_float,
            'product': product_details
        }

    @classmethod
    def from_row(cls, row):
        return cls(**row) if row else None

    @classmethod
    def find_by_invoice_id(cls, invoice_id):
        query = """
            SELECT
                ii.id, ii.invoice_id, ii.product_id, ii.quantity, ii.price, ii.total,
                p.name as product_name, p.product_code, p.description as product_description, p.stock
            FROM invoice_items ii
            JOIN products p ON ii.product_id = p.id
            WHERE ii.invoice_id = %s
        """
        params = (invoice_id,)
        rows = DBManager.execute_query(query, params, fetch='all')
        return [cls.from_row(row) for row in rows] if rows else []

    @classmethod
    def delete_by_invoice_id(cls, invoice_id):
        query = f"DELETE FROM {cls._table_name} WHERE invoice_id = %s"
        params = (invoice_id,)
        DBManager.execute_write_query(query, params)

    @classmethod
    def create_invoice_item(cls, data):
        return super().create(data)
