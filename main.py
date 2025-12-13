
from dotenv import load_dotenv
# Load environment variables first to ensure all configs are set
load_dotenv()

from app import create_app


# Create the Flask application instance using the app factory pattern
app = create_app()

if __name__ == "__main__":
    # For development, app.run() is used.
    # For production, a more robust WSGI server like Gunicorn should be used.
    app.run(host="0.0.0.0", port=5001, debug=True)
