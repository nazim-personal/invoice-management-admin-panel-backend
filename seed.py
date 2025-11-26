
import os

from uuid6 import uuid7
from app.database.base import get_db_connection
from werkzeug.security import generate_password_hash

# --- Default Admin User Details ---
ADMIN_EMAIL = "admin@example.com"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Sknazim1818@"
ADMIN_ROLE = "admin"
ADMIN_NAME = "Administrator"

def _create_tables_from_schema(conn):
    """
    Executes the schema.sql file to create all tables using a provided connection.
    """
    schema_path = os.path.join(os.path.dirname(__file__), 'app', 'database', 'schemas', 'schema.sql')
    print(f"Reading database schema from: {schema_path}")

    try:
        with open(schema_path, 'r') as f:
            # Read the entire file and split into individual statements
            # Filter out any empty strings that may result from splitting
            sql_statements = [s for s in f.read().split(';') if s.strip()]

        with conn.cursor() as cursor:
            for statement in sql_statements:
                cursor.execute(statement)
        conn.commit()
        print("All tables from schema.sql have been created.")

    except FileNotFoundError:
        print(f"ERROR: The schema file was not found at {schema_path}")
        raise
    except Exception as e:
        print(f"An error occurred while creating tables from schema: {e}")
        raise

def _seed_initial_admin(conn):
    """
    Creates the first admin user using a provided connection if no admin exists.
    """
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE role = %s", (ADMIN_ROLE,))
            if cursor.fetchone():
                print("An admin user already exists. Seeding not required.")
                return

            print(f"No admin user found. Creating initial admin: {ADMIN_EMAIL}")
            password_hash = generate_password_hash(ADMIN_PASSWORD, method='scrypt')
            
            sql = """
            INSERT INTO users (id, username, email, password_hash, name, role)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (uuid7(), ADMIN_USERNAME, ADMIN_EMAIL, password_hash, ADMIN_NAME, ADMIN_ROLE))
        conn.commit()
        
        print("=" * 50)
        print("Default admin user created successfully!")
        print(f"  Email: {ADMIN_EMAIL}")
        print(f"  Password: {ADMIN_PASSWORD}")
        print("=" * 50)

    except Exception as e:
        print(f"An unexpected error occurred during admin seeding: {e}")
        raise

def initialize_database():
    """Drops the database, recreates it, creates tables, and seeds the admin user."""
    db_name = os.getenv("DB_NAME", "vyaper_billing_db")
    conn = None
    try:
        # 1. Connect to MySQL server (without specifying a DB) to drop/create
        conn_server = get_db_connection(db_required=False)
        with conn_server.cursor() as cursor:
            print(f"Dropping database `{db_name}` if it exists...")
            cursor.execute(f"DROP DATABASE IF EXISTS `{db_name}`")
            print(f"Creating database `{db_name}`...")
            cursor.execute(f"CREATE DATABASE `{db_name}`")
        conn_server.close()
        print("Database has been reset.")

        # 2. Connect to the newly created database to create tables and seed data
        conn_db = get_db_connection(db_required=True)
        print(f"Connected to database `{db_name}` for seeding.")
        
        # 3. Create all tables by executing the schema
        _create_tables_from_schema(conn_db)

        # 4. Seed the initial admin user
        _seed_initial_admin(conn_db)
        
        print("Database initialization and seeding process completed successfully.")

    except Exception as e:
        print(f"A critical error occurred during database initialization: {e}")
        raise
    finally:
        # 5. Ensure final connection is closed
        if conn and conn.open:
            conn.close()

if __name__ == "__main__":
    initialize_database()
