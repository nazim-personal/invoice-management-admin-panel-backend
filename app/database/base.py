
import pymysql
from app.database.config import Config

def get_db_connection(db_required=True):
    """
    Establishes a connection to the MySQL database using the centralized config.

    Args:
        db_required (bool): If False, connects to the MySQL server without
                              selecting a specific database.

    Returns:
        A pymysql connection object.
    """
    # Get the appropriate configuration from our central Config class
    config = Config.get_db_config(db_required=db_required)
    
    # Use the unpacked config dictionary to establish the connection
    return pymysql.connect(**config)

