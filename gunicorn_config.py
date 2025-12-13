import os
import multiprocessing

# Gunicorn configuration for GCP Cloud Run

# Port: Cloud Run injects the PORT environment variable (default 8080)
port = os.getenv("PORT", "8080")
bind = f"0.0.0.0:{port}"

# Workers:
# For Cloud Run (containerized), we often want to limit memory usage.
# 1-2 workers is usually sufficient for a standard instance (e.g., 512MB - 1GB RAM).
# If using 'gthread' worker class, we can handle concurrency with threads.
workers = int(os.getenv("GUNICORN_WORKERS", "1"))

# Threads:
# Using threads allows handling multiple requests per worker, good for I/O bound apps.
threads = int(os.getenv("GUNICORN_THREADS", "8"))

# Worker Class:
# 'gthread' is standard for threaded workers.
worker_class = "gthread"

# Timeout:
# Cloud Run defaults to 300s (5 mins), but web requests should be faster.
# Set slightly higher than default to allow for PDF generation or slow DB queries.
timeout = 120

# Logging
accesslog = "-"  # Stdout
errorlog = "-"   # Stderr
loglevel = "info"

# Keepalive to reduce connection overhead
keepalive = 5
