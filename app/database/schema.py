from .base import get_db_connection

def create_schema():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id CHAR(36) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL,
            phone VARCHAR(255) NOT NULL,
            address VARCHAR(255) NOT NULL,
            gst_number VARCHAR(255) NOT NULL,
            status VARCHAR(255) NOT NULL
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id CHAR(36) PRIMARY KEY,
            product_code VARCHAR(255) NOT NULL,
            name VARCHAR(255) NOT NULL,
            description VARCHAR(255) NOT NULL,
            price DECIMAL(10, 2) NOT NULL,
            stock INT NOT NULL,
            status VARCHAR(255) NOT NULL
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id CHAR(36) PRIMARY KEY,
            customer_id CHAR(36) NOT NULL,
            invoice_date DATE NOT NULL,
            total_amount DECIMAL(10, 2) NOT NULL,
            status VARCHAR(255) NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id CHAR(36) PRIMARY KEY,
            invoice_id CHAR(36) NOT NULL,
            payment_date DATE NOT NULL,
            amount DECIMAL(10, 2) NOT NULL,
            payment_method VARCHAR(255) NOT NULL,
            status VARCHAR(255) NOT NULL,
            transaction_id VARCHAR(255) DEFAULT NULL,
            payment_gateway VARCHAR(50) DEFAULT NULL,
            gateway_response TEXT DEFAULT NULL,
            FOREIGN KEY (invoice_id) REFERENCES invoices(id)
        );
        CREATE INDEX IF NOT EXISTS idx_payments_transaction_id ON payments(transaction_id);
        CREATE INDEX IF NOT EXISTS idx_payments_gateway ON payments(payment_gateway);
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id CHAR(36) PRIMARY KEY,
            username VARCHAR(255) NOT NULL,
            password VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL
        );
        """)
    conn.commit()
    conn.close()
