
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
        "host": os.getenv("DB_HOST", "localhost"),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", "root"),
        "database": os.getenv("DB_NAME", "vyaper_billing_db"),
        "cursorclass": pymysql.cursors.DictCursor
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
