from .base_model import BaseModel
from app.database.db_manager import DBManager
from decimal import Decimal
from datetime import date
from app.database.models.invoice import Invoice

class Payment(BaseModel):
    _table_name = 'payments'

    def __init__(self, **kwargs):
        super().__init__()
        for key, value in kwargs.items():
            if key == 'amount' and value is not None:
                value = Decimal(value)
            setattr(self, key, value)

    def to_dict(self):
        amount_float = float(self.amount)
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'amount': amount_float,
            'payment_date': self.payment_date.isoformat() if isinstance(self.payment_date, date) else None,
            'method': self.method,
            'reference_no': self.reference_no
        }

    @classmethod
    def from_row(cls, row):
        return cls(**row) if row else None

    @classmethod
    def record_payment(cls, data):
        return super().create(data)

    @classmethod
    def find_by_id(cls, payment_id):
        query = f"SELECT * FROM {cls._table_name} WHERE id = %s"
        row = DBManager.execute_query(query, (payment_id,), fetch='one')
        return cls.from_row(row)

    @classmethod
    def find_by_invoice_id(cls, invoice_id):
        query = f"SELECT * FROM {cls._table_name} WHERE invoice_id = %s ORDER BY payment_date DESC"
        rows = DBManager.execute_query(query, (invoice_id,), fetch='all')
        return [cls.from_row(row) for row in rows] if rows else []
    
    @classmethod
    def find_latest_by_invoice_id(cls, invoice_id):
        # return only one (latest) payment
        query = f"SELECT * FROM {cls._table_name} WHERE invoice_id = %s ORDER BY payment_date DESC LIMIT 1"
        row = DBManager.execute_query(query, (invoice_id,), fetch='one')
        return cls.from_row(row) if row else None
