from .base_model import BaseModel
from app.database.db_manager import DBManager
from datetime import datetime, date
from decimal import Decimal

class Invoice(BaseModel):
    _table_name = 'invoices'

    def __init__(self, **kwargs):
        super().__init__()
        for key, value in kwargs.items():
            # Convert date/datetime strings from DB to objects upon instantiation
            if key in ('created_at', 'updated_at') and value and isinstance(value, str):
                try:
                    value = datetime.fromisoformat(value.replace(' ', 'T'))
                except ValueError:
                    pass
            elif key == 'due_date' and value and isinstance(value, str):
                try:
                    value = date.fromisoformat(value)
                except ValueError:
                    pass
            setattr(self, key, value)

    def to_dict(self):
        return {
            "id": self.id,
            "invoice_number": self.invoice_number,
            "created_at": self.created_at.isoformat() if getattr(self, 'created_at', None) else None,
            "due_date": self.due_date.isoformat() if getattr(self, 'due_date', None) else None,
            "subtotal_amount": float(self.subtotal_amount),
            "discount_amount": float(self.discount_amount),
            "tax_percent": float(self.tax_percent),
            "tax_amount": float(self.tax_amount),
            "total_amount": float(self.total_amount),
            "due_amount": float(getattr(self, 'due_amount', 0.0)),
            "amount_paid": float(getattr(self, 'amount_paid', 0.0)),
            "status": self.status,
            "updated_at": self.updated_at.isoformat() if getattr(self, 'updated_at', None) else None,
            "customer": {
                "id": getattr(self, "customer_id", None),
                "name": getattr(self, "customer_name", None),
                "phone": getattr(self, "customer_phone", None),
            }
        }

    @classmethod
    def from_row(cls, row):
        return cls(**row) if row else None

    @classmethod
    def create_invoice(cls, data):
        return super().create(data)

    @classmethod
    def update(cls, invoice_id, data):
        if not data:
            return

        for field in ['subtotal_amount', 'discount_amount', 'tax_amount', 'total_amount']:
            if field in data and data[field] is not None:
                data[field] = Decimal(data[field]).quantize(Decimal('0.00'))
        
        data['updated_at'] = datetime.now()

        set_clauses = []
        params = []
        for key, value in data.items():
            set_clauses.append(f"{key} = %s")
            params.append(value)

        query = f"UPDATE {cls._table_name} SET {', '.join(set_clauses)} WHERE id = %s"
        params.append(invoice_id)
        DBManager.execute_write_query(query, tuple(params))

    @classmethod
    def find_by_id(cls, invoice_id, include_deleted=False):
        query = f"""
            SELECT i.*, COALESCE(SUM(p.amount), 0) as amount_paid, (i.total_amount - COALESCE(SUM(p.amount), 0)) as due_amount
            FROM {cls._table_name} i
            LEFT JOIN payments p ON i.id = p.invoice_id
            WHERE i.id = %s
        """
        if not include_deleted:
            query += " AND i.deleted_at IS NULL"
        query += " GROUP BY i.id"
        row = DBManager.execute_query(query, (invoice_id,), fetch='one')
        return cls.from_row(row)

    @classmethod
    def find_by_invoice_number(cls, invoice_number):
        query = "SELECT * FROM invoices WHERE invoice_number = %s AND deleted_at IS NULL"
        row = DBManager.execute_query(query, (invoice_number,), fetch='one')
        return cls.from_row(row)

    @classmethod
    def list_all(cls, customer_id=None, status=None, offset=0, limit=10, q=None, include_deleted=False):
        where = []
        if not include_deleted:
            where.append("i.deleted_at IS NULL")

        params = []
        query_base = """ 
            SELECT i.*, 
                   c.id AS customer_id,
                   c.name AS customer_name,
                   c.phone AS customer_phone,
                   COALESCE(SUM(p.amount), 0) AS amount_paid,
                   (i.total_amount - COALESCE(SUM(p.amount), 0)) AS due_amount
            FROM invoices i
            JOIN customers c ON i.customer_id = c.id
            LEFT JOIN payments p ON i.id = p.invoice_id
        """

        if customer_id:
            where.append("i.customer_id = %s")
            params.append(customer_id)
        if status:
            where.append("i.status = %s")
            params.append(status)
        if q:
            where.append("(i.invoice_number LIKE %s OR c.name LIKE %s)")
            like_q = f"%{q}%"
            params.extend([like_q, like_q])

        where_sql = " WHERE " + " AND ".join(where) if where else ""
        group_by_sql = " GROUP BY i.id, c.id, c.name, c.phone ORDER BY i.id DESC LIMIT %s OFFSET %s"
        final_query = query_base + where_sql + group_by_sql
        params.extend([limit, offset])

        rows = DBManager.execute_query(final_query, tuple(params), fetch='all')
        invoices = [cls.from_row(row) for row in rows] if rows else []

        count_query_params = tuple(params[:-2])
        count_query = """
            SELECT COUNT(DISTINCT i.id) as total 
            FROM invoices i 
            JOIN customers c ON i.customer_id = c.id
        """ + where_sql

        count_result = DBManager.execute_query(count_query, count_query_params, fetch='one')
        total = count_result['total'] if count_result else 0

        return invoices, total
    
    @classmethod
    def bulk_soft_delete(cls, ids):
        if not ids:
            return 0
        placeholders = ', '.join(['%s'] * len(ids))
        query = f"UPDATE {cls._table_name} SET deleted_at = NOW() WHERE id IN ({placeholders}) AND deleted_at IS NULL"
        DBManager.execute_write_query(query, tuple(ids))
        return len(ids)
