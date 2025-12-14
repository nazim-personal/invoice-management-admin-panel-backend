from app.database.db_manager import DBManager
from datetime import datetime, timedelta

class ReportModel:
    @staticmethod
    def get_sales_report(start_date=None, end_date=None, period='monthly'):
        """
        Generate sales report based on invoices.
        period: 'daily', 'weekly', 'monthly', 'yearly'
        """
        where_clauses = ["deleted_at IS NULL"]
        params = []

        if start_date:
            where_clauses.append("invoice_date >= %s")
            params.append(start_date)
        if end_date:
            where_clauses.append("invoice_date <= %s")
            params.append(end_date)

        where_sql = " WHERE " + " AND ".join(where_clauses)

        # Determine grouping format based on period
        if period == 'daily':
            date_format = '%%Y-%%m-%%d'
        elif period == 'weekly':
            date_format = '%%Y-%%u' # Year-Week
        elif period == 'yearly':
            date_format = '%%Y'
        else: # monthly
            date_format = '%%Y-%%m'

        query = f"""
            SELECT
                DATE_FORMAT(invoice_date, '{date_format}') as period,
                COUNT(id) as invoice_count,
                SUM(total_amount) as total_sales,
                SUM(amount_paid) as total_collected,
                SUM(due_amount) as total_due
            FROM invoices
            {where_sql}
            GROUP BY period
            ORDER BY period DESC
        """

        # Note: 'amount_paid' and 'due_amount' might need to be calculated via join if not stored on invoice
        # Assuming for now we can join or they are updated on invoice.
        # Let's use a more robust query joining payments for accuracy if needed,
        # but the current Invoice model seems to have these as calculated fields in find_by_id.
        # For aggregation, we should join.

        query = f"""
            SELECT
                DATE_FORMAT(i.created_at, '{date_format}') as period,
                COUNT(i.id) as invoice_count,
                SUM(i.total_amount) as total_sales,
                COALESCE(SUM(p.amount), 0) as total_collected,
                (SUM(i.total_amount) - COALESCE(SUM(p.amount), 0)) as total_due
            FROM invoices i
            LEFT JOIN payments p ON i.id = p.invoice_id
            {where_sql.replace('invoice_date', 'i.created_at').replace('deleted_at', 'i.deleted_at')}
            GROUP BY period
            ORDER BY period DESC
        """

        return DBManager.execute_query(query, tuple(params), fetch='all')

    @staticmethod
    def get_payment_report(start_date=None, end_date=None, period='monthly'):
        """
        Generate payments report.
        """
        where_clauses = []
        params = []

        if start_date:
            where_clauses.append("payment_date >= %s")
            params.append(start_date)
        if end_date:
            where_clauses.append("payment_date <= %s")
            params.append(end_date)

        where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        if period == 'daily':
            date_format = '%%Y-%%m-%%d'
        elif period == 'weekly':
            date_format = '%%Y-%%u'
        elif period == 'yearly':
            date_format = '%%Y'
        else:
            date_format = '%%Y-%%m'

        query = f"""
            SELECT
                DATE_FORMAT(payment_date, '{date_format}') as period,
                COUNT(id) as payment_count,
                SUM(amount) as total_collected
            FROM payments
            {where_sql}
            GROUP BY period
            ORDER BY period DESC
        """
        return DBManager.execute_query(query, tuple(params), fetch='all')

    @staticmethod
    def get_customer_aging_report():
        """
        Generate customer aging report (who owes what).
        """
        query = """
            SELECT
                c.id, c.name, c.email, c.phone,
                COUNT(i.id) as total_invoices,
                SUM(i.total_amount) as total_billed,
                COALESCE(SUM(p.amount), 0) as total_paid,
                (SUM(i.total_amount) - COALESCE(SUM(p.amount), 0)) as current_due
            FROM customers c
            JOIN invoices i ON c.id = i.customer_id
            LEFT JOIN payments p ON i.id = p.invoice_id
            WHERE i.deleted_at IS NULL AND c.deleted_at IS NULL
            GROUP BY c.id, c.name, c.email, c.phone
            HAVING current_due > 0
            ORDER BY current_due DESC
        """
        return DBManager.execute_query(query, fetch='all')

    @staticmethod
    def get_top_products_report(start_date=None, end_date=None, limit=10):
        """
        Generate top selling products report.
        """
        where_clauses = ["i.deleted_at IS NULL"]
        params = []

        if start_date:
            where_clauses.append("i.created_at >= %s")
            params.append(start_date)
        if end_date:
            where_clauses.append("i.created_at <= %s")
            params.append(end_date)

        where_sql = " WHERE " + " AND ".join(where_clauses)

        query = f"""
            SELECT
                p.id, p.name, p.product_code,
                SUM(ii.quantity) as total_quantity_sold,
                SUM(ii.total) as total_revenue
            FROM invoice_items ii
            JOIN invoices i ON ii.invoice_id = i.id
            JOIN products p ON ii.product_id = p.id
            {where_sql}
            GROUP BY p.id, p.name, p.product_code
            ORDER BY total_revenue DESC
            LIMIT %s
        """
        params.append(limit)

        return DBManager.execute_query(query, tuple(params), fetch='all')

    @staticmethod
    def get_summary_stats():
        """
        Get high-level summary stats.
        """
        # Total Customers
        total_customers = DBManager.execute_query("SELECT COUNT(*) as count FROM customers WHERE deleted_at IS NULL", fetch='one')['count']

        # Total Products
        total_products = DBManager.execute_query("SELECT COUNT(*) as count FROM products WHERE deleted_at IS NULL", fetch='one')['count']

        # Total Invoices
        total_invoices = DBManager.execute_query("SELECT COUNT(*) as count FROM invoices WHERE deleted_at IS NULL", fetch='one')['count']

        # Financials
        financials_query = """
            SELECT
                SUM(i.total_amount) as total_sales,
                COALESCE(SUM(p.amount), 0) as total_collected
            FROM invoices i
            LEFT JOIN payments p ON i.id = p.invoice_id
            WHERE i.deleted_at IS NULL
        """
        financials = DBManager.execute_query(financials_query, fetch='one')

        from decimal import Decimal
        total_sales = Decimal(financials['total_sales']) if financials['total_sales'] else Decimal(0)
        total_collected = Decimal(financials['total_collected']) if financials['total_collected'] else Decimal(0)
        total_due = total_sales - total_collected

        return {
            'total_customers': total_customers,
            'total_products': total_products,
            'total_invoices': total_invoices,
            'total_sales': float(total_sales),
            'total_collected': float(total_collected),
            'total_due': float(total_due)
        }
