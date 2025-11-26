
from dotenv import load_dotenv
# Load environment variables first to ensure all configs are set
load_dotenv()

from app import create_app
from seed import initialize_database

# --- Database Initialization ---
# WARNING: This will delete and recreate the database on every application start.
# All data will be lost on restart. This is for development purposes only.
print("Initializing database...")
initialize_database()
print("Database initialization complete.")
# -----------------------------

# Create the Flask application instance using the app factory pattern
app = create_app()

if __name__ == "__main__":
    # For development, app.run() is used. 
    # For production, a more robust WSGI server like Gunicorn should be used.
    app.run(host="0.0.0.0", port=5001, debug=True)
