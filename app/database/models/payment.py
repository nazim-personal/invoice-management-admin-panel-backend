from .base_model import BaseModel
from app.database.db_manager import DBManager
from decimal import Decimal
from datetime import date, datetime
from app.database.models.invoice import Invoice

class Payment(BaseModel):
    _table_name = 'payments'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for key, value in kwargs.items():
            if key == 'amount' and value is not None:
                value = Decimal(value)
            elif key == 'payment_date' and isinstance(value, str):
                try:
                    value = date.fromisoformat(value)
                except ValueError:
                    pass
            elif key == 'created_at' and isinstance(value, str):
                try:
                    value = datetime.fromisoformat(value)
                except ValueError:
                    pass
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

    @classmethod
    def find_with_pagination_and_count(cls, page=1, per_page=10):
        offset = (page - 1) * per_page
        query = f"""
            SELECT p.*, i.invoice_number, c.name as customer_name, c.email as customer_email
            FROM {cls._table_name} p
            JOIN invoices i ON p.invoice_id = i.id
            JOIN customers c ON i.customer_id = c.id
            WHERE p.deleted_at IS NULL
            ORDER BY p.payment_date DESC
            LIMIT %s OFFSET %s
        """
        rows = DBManager.execute_query(query, (per_page, offset), fetch='all')
        items = [cls.from_row(row) for row in rows] if rows else []

        count_query = f"SELECT COUNT(*) as total FROM {cls._table_name} WHERE deleted_at IS NULL"
        count_result = DBManager.execute_query(count_query, fetch='one')
        total = count_result['total'] if count_result else 0

        return items, total

    @classmethod
    def find_by_invoice_id_with_pagination_and_count(cls, invoice_id, page=1, per_page=10):
        offset = (page - 1) * per_page
        query = f"SELECT * FROM {cls._table_name} WHERE invoice_id = %s AND deleted_at IS NULL ORDER BY payment_date DESC LIMIT %s OFFSET %s"
        rows = DBManager.execute_query(query, (invoice_id, per_page, offset), fetch='all')
        items = [cls.from_row(row) for row in rows] if rows else []

        count_query = f"SELECT COUNT(*) as total FROM {cls._table_name} WHERE invoice_id = %s AND deleted_at IS NULL"
        count_result = DBManager.execute_query(count_query, (invoice_id,), fetch='one')
        total = count_result['total'] if count_result else 0

        return items, total

    @classmethod
    def get_total_paid(cls, invoice_id):
        """
        Calculate total amount paid for an invoice.
        """
        query = f"SELECT COALESCE(SUM(amount), 0) as total FROM {cls._table_name} WHERE invoice_id = %s"
        result = DBManager.execute_query(query, (invoice_id,), fetch='one')
        return Decimal(result['total']) if result else Decimal(0)

    @classmethod
    def search_payments(cls, search_term=None, method=None, reference_no=None, start_date=None, end_date=None, page=1, per_page=10):
        """
        Search payments with multiple filters.
        """
        where_clauses = []
        params = []

        if search_term:
            where_clauses.append("(p.reference_no LIKE %s OR p.method LIKE %s)")
            params.extend([f"%{search_term}%", f"%{search_term}%"])

        if method:
            where_clauses.append("p.method = %s")
            params.append(method)

        if reference_no:
            where_clauses.append("p.reference_no LIKE %s")
            params.append(f"%{reference_no}%")

        if start_date:
            where_clauses.append("p.payment_date >= %s")
            params.append(start_date)

        if end_date:
            where_clauses.append("p.payment_date <= %s")
            params.append(end_date)

        where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        offset = (page - 1) * per_page
        query = f"""
            SELECT p.*
            FROM {cls._table_name} p
            {where_sql}
            ORDER BY p.payment_date DESC
            LIMIT %s OFFSET %s
        """
        params.extend([per_page, offset])

        rows = DBManager.execute_query(query, tuple(params), fetch='all')
        items = [cls.from_row(row) for row in rows] if rows else []

        # Get total count
        count_query = f"SELECT COUNT(*) as total FROM {cls._table_name} p {where_sql}"
        count_result = DBManager.execute_query(count_query, tuple(params[:-2]), fetch='one')
        total = count_result['total'] if count_result else 0

        return items, total

    @classmethod
    def get_payment_with_details(cls, payment_id):
        """
        Get payment with customer and invoice details.
        """
        query = f"""
            SELECT
                p.*,
                i.invoice_number,
                i.total_amount as invoice_total,
                i.customer_id,
                c.name as customer_name,
                c.email as customer_email
            FROM {cls._table_name} p
            JOIN invoices i ON p.invoice_id = i.id
            JOIN customers c ON i.customer_id = c.id
            WHERE p.id = %s
        """
        row = DBManager.execute_query(query, (payment_id,), fetch='one')
        return row if row else None

    @classmethod
    def find_by_transaction_id(cls, transaction_id):
        """
        Find payment by PhonePe transaction ID.
        """
        query = f"SELECT * FROM {cls._table_name} WHERE transaction_id = %s LIMIT 1"
        row = DBManager.execute_query(query, (transaction_id,), fetch='one')
        return cls.from_row(row) if row else None
