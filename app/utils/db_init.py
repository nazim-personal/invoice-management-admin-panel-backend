import os
from werkzeug.security import generate_password_hash
from uuid6 import uuid7
from app.database.db_manager import DBManager
from app.database.models.user import User

def init_db():
    """
    Initialize database:
    1. Run schema to create tables (if not exist)
    2. Create admin user if no users exist
    """
    print("🔧 Initializing database...")

    try:
        # Step 0: Create database if not exists
        from app.database.config import Config
        from app.database.base import get_db_connection

        db_config = Config.get_db_config(db_required=True)
        db_name = db_config.get('database')

        if db_name:
            print(f"🔍 Checking if database '{db_name}' exists...")
            # Connect without selecting a DB
            conn = get_db_connection(db_required=False)
            try:
                with conn.cursor() as cursor:
                    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
                    print(f"✅ Database '{db_name}' verified/created")
            finally:
                conn.close()

        # Step 1: Create tables from schema (CREATE TABLE IF NOT EXISTS)
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'schemas', 'schema.sql')

        if not os.path.exists(schema_path):
            print(f"⚠️ Schema file not found at: {schema_path}")
            return

        with open(schema_path, 'r') as f:
            schema_sql = f.read()

        # Remove DROP statements to preserve data
        schema_lines = schema_sql.split('\n')
        filtered_lines = []
        skip_until_semicolon = False

        for line in schema_lines:
            if line.strip().upper().startswith('DROP TABLE'):
                if ';' in line:
                    skip_until_semicolon = False
                else:
                    skip_until_semicolon = True
                continue

            if skip_until_semicolon:
                if ';' in line:
                    skip_until_semicolon = False
                continue
            filtered_lines.append(line)

        schema_sql_safe = '\n'.join(filtered_lines)

        # Execute schema
        connection = DBManager.get_connection()
        cursor = connection.cursor()

        # Split by semicolons and execute each statement
        statements = [s.strip() for s in schema_sql_safe.split(';') if s.strip()]
        for statement in statements:
            if statement:
                try:
                    cursor.execute(statement)
                except Exception as e:
                    print(f"⚠️ Error executing schema statement: {e}")

        connection.commit()
        cursor.close()
        connection.close()
        print("✅ Tables verified/created")

        # Step 2: Check if admin user exists
        existing_users = User.find_all()

        if not existing_users or len(existing_users) == 0:
            print("👤 No users found. Creating default admin...")

            admin_username = os.getenv('ADMIN_USERNAME', 'admin')
            admin_email = os.getenv('ADMIN_EMAIL', 'admin@example.com')
            admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')

            admin_data = {
                'username': admin_username,
                'email': admin_email,
                'password': admin_password,
                'name': 'System Administrator',
                'role': 'admin',
                'company_name': os.getenv('COMPANY_NAME', 'Your Company Name'),
                'company_address': os.getenv('COMPANY_ADDRESS', '123 Business Street'),
                'company_city': os.getenv('COMPANY_CITY', 'City, State, PIN'),
                'company_phone': os.getenv('COMPANY_PHONE', '+91 1234567890'),
                'company_email': os.getenv('COMPANY_EMAIL', 'info@company.com'),
                'company_gst': os.getenv('COMPANY_GST', '12ABCDE1234F1Z5'),
                'currency_symbol': os.getenv('CURRENCY_SYMBOL', '₹')
            }

            User.create(admin_data)
            print(f"✅ Admin user created: {admin_email}")
        else:
            print(f"✅ Found {len(existing_users)} existing user(s). Skipping admin creation.")

    except Exception as e:
        print(f"❌ Error initializing database: {e}")
