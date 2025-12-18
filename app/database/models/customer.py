from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, date
from .base_model import BaseModel
from app.database.db_manager import DBManager


def to_iso(dt: Any) -> Optional[str]:
    """
    Safely convert a datetime/date to ISO string, or fallback to string for other types.
    Returns None if input is None.
    """
    if isinstance(dt, (datetime, date)):
        return dt.isoformat()
    if dt is not None:
        return str(dt)
    return None

class Customer(BaseModel):
    _table_name = 'customers'
    _allowed_fields = {'name', 'email', 'phone', 'address', 'gst_number'}

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        # Convert date strings to datetime objects
        for attr in ('created_at', 'updated_at'):
            val = getattr(self, attr, None)
            if isinstance(val, str):
                try:
                    setattr(self, attr, datetime.fromisoformat(val.replace(' ', 'T')))
                except (ValueError, TypeError):
                    pass

        # Default aggregates and invoices
        self.invoices: List[Dict[str, Any]] = getattr(self, 'invoices', [])
        self.aggregates: Dict[str, Any] = getattr(self, 'aggregates', {})

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': getattr(self, 'id', None),
            'name': getattr(self, 'name', None),
            'email': getattr(self, 'email', None),
            'phone': getattr(self, 'phone', None),
            'address': getattr(self, 'address', None),
            'gst_number': getattr(self, 'gst_number', None),
            'created_at': to_iso(getattr(self, 'created_at', None)),
            'updated_at': to_iso(getattr(self, 'updated_at', None)),
            'status': getattr(self, 'status', None),
            'aggregates': getattr(self, 'aggregates', {})
        }

    @classmethod
    def from_row(cls, row: Optional[Dict[str, Any]]) -> Optional["Customer"]:
        # Ensure only dict or None is passed
        if isinstance(row, dict) or row is None:
            return cls(**row) if row else None
        return None

    @classmethod
    def create_customer(cls, data: Dict[str, Any]) -> str:
        return super().create(data)

    @classmethod
    def update_customer(cls, record_id: str, data: Dict[str, Any]) -> bool:
        return super().update(record_id, data)

    @classmethod
    def find_by_email(cls, email: str, include_deleted: bool = False) -> Optional["Customer"]:
        query = f"SELECT * FROM {cls._table_name} WHERE email = %s"
        if not include_deleted:
            query += " AND deleted_at IS NULL"
        row = DBManager.execute_query(query, (email,), fetch='one')
        if isinstance(row, dict) or row is None:
            return cls.from_row(row)
        return None

    @classmethod
    def find_by_id_with_aggregates(cls, customer_id: str, include_deleted: bool = False) -> Optional["Customer"]:
        customer_query = f"""
            SELECT
                c.*,
                COALESCE(SUM(i.total_amount), 0) AS total_billed,
                CASE
                    WHEN COUNT(i.id) = 0 THEN 'New'
                    WHEN SUM(CASE WHEN i.status = 'Overdue' OR (i.status = 'Pending' AND i.due_date < NOW()) THEN 1 ELSE 0 END) > 0 THEN 'Overdue'
                    WHEN SUM(CASE WHEN i.status = 'Pending' THEN 1 ELSE 0 END) > 0 THEN 'Pending'
                    WHEN SUM(CASE WHEN i.status = 'Paid' THEN 1 ELSE 0 END) = COUNT(i.id) THEN 'Paid'
                    ELSE 'New'
                END AS status
            FROM {cls._table_name} c
            LEFT JOIN invoices i ON c.id = i.customer_id AND i.deleted_at IS NULL
            WHERE c.id = %s
        """
        if not include_deleted:
            customer_query += " AND c.deleted_at IS NULL"
        customer_query += " GROUP BY c.id"

        customer_row = DBManager.execute_query(customer_query, (customer_id,), fetch='one')
        if not isinstance(customer_row, dict):
            return None

        invoices_query = """
            SELECT
                i.id, i.invoice_number, i.due_date, i.total_amount, i.created_at, i.status,
                (i.total_amount - COALESCE(SUM(p.amount), 0)) as due_amount
            FROM invoices i
            LEFT JOIN payments p ON i.id = p.invoice_id
            WHERE i.customer_id = %s AND i.deleted_at IS NULL
            GROUP BY i.id ORDER BY i.created_at DESC
        """
        invoices_rows = DBManager.execute_query(invoices_query, (customer_id,), fetch='all') or []

        total_paid_query = """
            SELECT COALESCE(SUM(p.amount), 0) AS total_paid
            FROM payments p
            JOIN invoices i ON p.invoice_id = i.id
            WHERE i.customer_id = %s
        """
        total_paid_row = DBManager.execute_query(total_paid_query, (customer_id,), fetch='one') or {}
        total_paid = float(total_paid_row.get('total_paid', 0.0))
        total_billed = float(customer_row.get('total_billed', 0.0))
        total_due = total_billed - total_paid

        invoices_list = [
            {
                'id': row.get('id'),
                'invoice_number': row.get('invoice_number'),
                'due_date': to_iso(row.get('due_date')),
                'total_amount': float(row.get('total_amount') or 0.0),
                'created_at': to_iso(row.get('created_at')),
                'status': row.get('status'),
                'due_amount': float(row.get('due_amount') or 0.0)
            }
            for row in invoices_rows if isinstance(row, dict)
        ]

        customer = cls.from_row(customer_row)
        if customer:
            customer.aggregates = {
                'total_billed': total_billed,
                'total_paid': total_paid,
                'total_due': total_due,
                'invoices': invoices_list
            }
        return customer

    @classmethod
    def list_all(
        cls,
        q: Optional[str] = None,
        status: Optional[str] = None,
        offset: int = 0,
        limit: int = 20,
        customer_id: Optional[str] = None,
        include_deleted: bool = False,
        deleted_only: bool = False
    ) -> Tuple[List["Customer"], int]:

        where: List[str] = []
        params: List[Any] = []

        if deleted_only:
            where.append("c.deleted_at IS NOT NULL")
        elif not include_deleted:
            where.append("c.deleted_at IS NULL")
        if customer_id:
            where.append("c.id = %s")
            params.append(customer_id)
        if q:
            like = f"%{q}%"
            where.append("(c.name LIKE %s OR c.email LIKE %s OR c.phone LIKE %s)")
            params.extend([like, like, like])

        where_sql = f" WHERE {' AND '.join(where)}" if where else ""

        base_query = f"""
            SELECT
                c.id, c.name, c.email, c.phone, c.address, c.gst_number, c.created_at, c.updated_at,
                CASE
                    WHEN SUM(CASE WHEN i.status = 'Overdue' THEN 1 ELSE 0 END) > 0 THEN 'Overdue'
                    WHEN SUM(CASE WHEN i.status = 'Pending' THEN 1 ELSE 0 END) > 0 THEN 'Pending'
                    WHEN SUM(CASE WHEN i.status = 'Partially Paid' THEN 1 ELSE 0 END) > 0 THEN 'Partially Paid'
                    WHEN COUNT(i.id) > 0 AND SUM(CASE WHEN i.status = 'Paid' THEN 1 ELSE 0 END) = COUNT(i.id) THEN 'Paid'
                    ELSE 'New'
                END AS status
            FROM {cls._table_name} c
            LEFT JOIN invoices i ON c.id = i.customer_id AND i.deleted_at IS NULL
            {where_sql}
            GROUP BY c.id
        """

        outer_where = f"WHERE sub.status = %s" if status else ""
        final_query = f"SELECT * FROM ({base_query}) AS sub {outer_where} ORDER BY sub.id DESC LIMIT %s OFFSET %s"
        final_params = params + ([status] if status else []) + [limit, offset]

        rows = DBManager.execute_query(final_query, tuple(final_params), fetch='all') or []
        customers = [c for row in rows if (c := cls.from_row(row if isinstance(row, dict) else None)) is not None]

        count_query = f"SELECT COUNT(*) AS total FROM ({base_query}) AS sub {outer_where}"
        count_params = tuple(params + ([status] if status else []))
        total = int((DBManager.execute_query(count_query, count_params, fetch='one') or {}).get('total', 0))

        return customers, total

    @classmethod
    def bulk_restore(cls, ids: List[str]) -> int:
        return super().bulk_restore(ids)

    @classmethod
    def bulk_soft_delete(cls, ids: List[str]) -> int:
        return super().bulk_soft_delete(ids)
