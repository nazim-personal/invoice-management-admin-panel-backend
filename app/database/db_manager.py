
from .base import get_db_connection
from decimal import Decimal
from datetime import datetime, date

# --- Centralized Normalization Functions ---

def normalize_value(value):
    """Recursively normalize values for JSON serialization."""
    if isinstance(value, Decimal):
        # Return string to preserve formatting (e.g., "33333.00")
        return "{:.2f}".format(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value

def normalize_row(row):
    """Normalize all values in a DB row dictionary."""
    # Assumes row is a dictionary, as provided by DictCursor
    return {k: normalize_value(v) for k, v in row.items()}

def normalize_rows(rows):
    """Normalize a list of DB row dictionaries."""
    return [normalize_row(r) for r in rows]

# --- DBManager Class ---

class DBManager:
    """
    A centralized manager for handling all database interactions.
    This class abstracts away connection/cursor handling and normalizes output data.
    """

    @staticmethod
    def execute_query(query, params=None, fetch=None):
        """
        Executes a read-only query and returns normalized data.
        Supports fetch='one' or fetch='all'.
        Rolls back on error (to clear locks if any).
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params or ())

                if fetch == 'one':
                    row = cursor.fetchone()
                    return normalize_row(row) if row else None

                if fetch == 'all':
                    rows = cursor.fetchall()
                    return normalize_rows(rows) if rows else []

                return None
        except Exception as e:
            conn.rollback()  # rollback prevents dangling transactions/locks
            raise e
        finally:
            conn.close()

    @staticmethod
    def execute_write_query(query, params=None):
        """
        Executes a write query (INSERT, UPDATE, DELETE).
        Commits if successful, rolls back on error.
        Returns True if successful, otherwise raises.
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params or ())
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()   # rollback ensures no partial insert/update
            raise e
        finally:
            conn.close()

    @staticmethod
    def execute_bulk_write_query(query, params_list):
        """
        Executes a bulk write query using executemany.
        params_list should be a list of tuples/lists.
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.executemany(query, params_list or [])
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
