# app/database/models/dashboard_model.py
import calendar
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List
from dateutil.relativedelta import relativedelta
from app.database.base import get_db_connection


def calculate_percentage_change(current: Decimal, previous: Decimal) -> Decimal:
    """
    Calculate the percentage change from previous to current.
    """
    if previous == 0:
        return Decimal("100.0") if current > 0 else Decimal("0.0")
    return Decimal(((current - previous) / previous) * 100)


def get_dashboard_stats() -> Dict[str, Any]:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            today = date.today()
            first_day_current_month = today.replace(day=1)
            first_day_last_month = first_day_current_month - relativedelta(months=1)
            last_day_last_month = first_day_current_month - timedelta(days=1)

            # Total revenue - current month
            cur.execute(
                """
                SELECT COALESCE(SUM(total_amount), 0) AS total_revenue
                FROM invoices
                WHERE status='Paid' AND deleted_at IS NULL
                  AND created_at >= %s
            """,
                (first_day_current_month,),
            )
            row = cur.fetchone() or {}
            total_revenue = Decimal(row.get("total_revenue", 0))

            # Total revenue - last month
            cur.execute(
                """
                SELECT COALESCE(SUM(total_amount), 0) AS total_revenue
                FROM invoices
                WHERE status='Paid' AND deleted_at IS NULL
                  AND created_at BETWEEN %s AND %s
            """,
                (first_day_last_month, last_day_last_month),
            )
            row = cur.fetchone() or {}
            last_month_revenue = Decimal(row.get("total_revenue", 0))

            revenue_change_percent = calculate_percentage_change(
                total_revenue, last_month_revenue
            )

            # Total customers - current month
            cur.execute(
                """
                SELECT COUNT(*) AS total_customers
                FROM customers
                WHERE deleted_at IS NULL
                  AND created_at >= %s
            """,
                (first_day_current_month,),
            )
            row = cur.fetchone() or {}
            total_customers = int(row.get("total_customers", 0))

            # Total customers - last month
            cur.execute(
                """
                SELECT COUNT(*) AS total_customers
                FROM customers
                WHERE deleted_at IS NULL
                  AND created_at BETWEEN %s AND %s
            """,
                (first_day_last_month, last_day_last_month),
            )
            row = cur.fetchone() or {}
            last_month_customers = int(row.get("total_customers", 0))

            customers_change_percent = calculate_percentage_change(
                Decimal(total_customers), Decimal(last_month_customers)
            )

            # Other counts
            cur.execute(
                "SELECT COUNT(*) AS total_invoices FROM invoices WHERE deleted_at IS NULL"
            )
            row = cur.fetchone() or {}
            total_invoices = int(row.get("total_invoices", 0))

            cur.execute(
                "SELECT COUNT(*) AS pending_invoices FROM invoices WHERE status='Pending' AND deleted_at IS NULL"
            )
            row = cur.fetchone() or {}
            pending_invoices = int(row.get("pending_invoices", 0))

            cur.execute(
                "SELECT COUNT(*) AS total_products FROM products WHERE deleted_at IS NULL"
            )
            row = cur.fetchone() or {}
            total_products = int(row.get("total_products", 0))

            return {
                "total_revenue": total_revenue,
                "revenue_change_percent": revenue_change_percent,
                "total_customers": total_customers,
                "customers_change_percent": customers_change_percent,
                "total_invoices": total_invoices,
                "pending_invoices": pending_invoices,
                "total_products": total_products,
            }
    finally:
        conn.close()

def get_sales_performance() -> List[Dict[str, Any]]:
    """
    Returns last 6 months sales performance with:
    - month: 'Apr 2025'
    - revenue: total revenue for the month
    - invoice_count: number of invoices
    Only includes paid invoices where deleted_at IS NULL.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 
                    DATE_FORMAT(created_at, '%%Y-%%m') AS ym,
                    COALESCE(SUM(total_amount), 0) AS revenue,
                    COUNT(*) AS invoice_count
                FROM invoices
                WHERE LOWER(status) = 'paid'
                  AND created_at >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
                GROUP BY ym
                ORDER BY ym ASC
                """
            )
            rows = cur.fetchall()

            stats_map = {
                row["ym"]: {
                    "revenue": Decimal(row["revenue"]),
                    "count": int(row["invoice_count"])
                }
                for row in rows
            }

            today = datetime.today()
            results: List[Dict[str, Any]] = []

            # Generate last 6 months
            for i in range(5, -1, -1):
                # Correctly calculate past months
                month_date = today.replace(day=1) - relativedelta(months=i)
                ym = month_date.strftime('%Y-%m')
                label = month_date.strftime('%b %Y')

                month_stats = stats_map.get(ym, {"revenue": Decimal("0.0"), "count": 0})
                results.append({
                    "month": label,
                    "revenue": month_stats["revenue"],
                    "invoice_count": month_stats["count"],
                })

            return results
    finally:
        conn.close()

def get_latest_invoices() -> List[Dict[str, Any]]:
    """
    Fetches the 10 most recent invoices along with customer info and due amount.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 
                    i.id, 
                    i.total_amount, 
                    i.status,
                    c.id AS customer_id,
                    c.name AS customer_name,
                    c.phone AS customer_phone,
                    i.created_at,
                    COALESCE(SUM(p.amount), 0) AS amount_paid
                FROM invoices i
                JOIN customers c ON i.customer_id = c.id
                LEFT JOIN payments p ON i.id = p.invoice_id
                WHERE i.deleted_at IS NULL
                GROUP BY i.id, c.id, c.name, c.phone
                ORDER BY i.created_at DESC
                LIMIT 10
                """
            )
            invoices = cur.fetchall()

            result = []
            for inv in invoices:
                total_amount = Decimal(inv["total_amount"])
                amount_paid = Decimal(inv["amount_paid"])
                due_amount = total_amount - amount_paid

                result.append({
                    "id": inv["id"],
                    "total_amount": total_amount,
                    "due_amount": due_amount,
                    "status": inv["status"],
                    "created_at": inv["created_at"].isoformat() if inv["created_at"] else None,
                    "customer": {
                        "id": inv["customer_id"],
                        "name": inv["customer_name"],
                        "phone": inv["customer_phone"]
                    }
                })
            return result
    finally:
        conn.close()