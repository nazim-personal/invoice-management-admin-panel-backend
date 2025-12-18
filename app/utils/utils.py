from datetime import datetime
from decimal import Decimal
import hashlib
import random
import re
import string

from app.database.base import get_db_connection
from app.database.db_manager import DBManager
from app.database.models.invoice import Invoice
from app.database.models.payment import Payment

def short_customer_code(customer_id: str, length: int = 4) -> str:
    """Generate a short customer code from UUID or integer ID"""
    customer_id_str = str(customer_id)
    hash_val = hashlib.md5(customer_id_str.encode()).hexdigest()
    return hash_val[:length].upper()

def generate_invoice_number(customer_id: str) -> str:
    """
    Generate sequential invoice number with format:
    INV-YYYYMM-CODE-SEQ
    Works with DBManager directly (no raw connection needed)
    """
    ym = datetime.now().strftime("%Y%m")
    cust_code = short_customer_code(customer_id)

    # Get the maximum global sequence number
    query = """
        SELECT MAX(CAST(SUBSTRING_INDEX(invoice_number, '-', -1) AS UNSIGNED)) AS max_seq
        FROM invoices
        WHERE invoice_number REGEXP 'INV-[0-9]{6}-[A-Z0-9]+-[0-9]{3}'
    """
    result = DBManager.execute_query(query, fetch="one")
    max_seq = 0
    if (
        result
        and isinstance(result, dict)
        and "max_seq" in result
        and result["max_seq"] is not None
    ):
        max_seq = int(result["max_seq"])

    seq = max_seq + 1
    seq_str = str(seq).zfill(3)
    return f"INV-{ym}-{cust_code}-{seq_str}"

def generate_unique_product_code(product_name):
    """
    Generates a unique, human-readable product code from a product name.
    e.g., "Classic Blue T-Shirt" -> "CBT-1234"

    Args:
        product_name (str): The name of the product.

    Returns:
        str: A unique product code.
    """
    conn = get_db_connection()
    try:
        while True:
            # 1. Generate a 3-letter prefix from the product name.
            clean_name = re.sub(r"[^A-Za-z0-9 ]", "", product_name).strip()
            words = clean_name.split()
            prefix = "".join(word[0].upper() for word in words[:3])

            # Ensure the prefix is exactly 3 characters long.
            if len(prefix) < 3 and words:
                prefix += words[0][1 : 1 + (3 - len(prefix))].upper()
            if len(prefix) < 3:
                prefix += "X" * (3 - len(prefix))

            # 2. Append a 4-digit random number.
            rand_num = "".join(random.choices(string.digits, k=4))
            product_code = f"{prefix}-{rand_num}"

            # 3. Check for uniqueness in the database.
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM products WHERE product_code = %s", (product_code,)
                )
                if not cur.fetchone():
                    return product_code
    finally:
        if conn:
            conn.close()

def calculate_invoice_totals(items, discount_amount=Decimal('0.00'), tax_percent=Decimal('0.00')):
    """Calculate subtotal, tax, and total amounts."""
    subtotal = sum(Decimal(item['price']) * Decimal(item['quantity']) for item in items)
    tax_amount = (subtotal - discount_amount) * (tax_percent / Decimal('100.00'))
    total = subtotal - discount_amount + tax_amount
    return subtotal, tax_amount, total


def update_invoice_status(invoice_id, total_amount):
    """Update invoice status based on payments."""
    payments = Payment.find_by_invoice_id(invoice_id)
    total_paid = sum((p.amount or 0) for p in payments if p)

    # Ensure total_amount is Decimal for comparison
    total_amount = Decimal(str(total_amount))

    if total_paid >= total_amount:
        status = 'Paid'
    elif total_paid > 0:
        status = 'Partially Paid'
    else:
        status = 'Pending'

    Invoice.update(invoice_id, {'status': status})
    return status


