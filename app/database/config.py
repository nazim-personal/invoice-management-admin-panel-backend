
import os
import pymysql.cursors
from dotenv import load_dotenv

# Load environment variables from a .env file if it exists
load_dotenv()

class Config:
    """
    Database configuration class.

    This class encapsulates the settings required to connect to the database,
    loading all values from environment variables. It provides a single,
    authoritative source for database connection parameters.
    """

    # A dictionary of connection arguments for pymysql
    MYSQL_CONFIG = {
       "host": os.getenv("DB_HOST"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME"),
        "port": int(os.getenv("DB_PORT", 3306)),  # 🔑 TiDB Cloud uses 4000
        "cursorclass": pymysql.cursors.DictCursor,
        "ssl": {"ssl": {}}
    }

    @staticmethod
    def get_db_config(db_required=True):
        """
        A static method to retrieve the database settings.
        If db_required is False, it returns a config without the database name,
        which is useful for initial setup or database creation/deletion.
        """
        config = Config.MYSQL_CONFIG.copy()
        if not db_required:
            # Remove the database key for connections to the server itself
            config.pop('database', None)
        return config
