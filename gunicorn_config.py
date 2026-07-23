"""
Gunicorn configuration for production deployment.
Place this in the project root or specify with: gunicorn -c gunicorn_config.py
"""

import multiprocessing
import os

# Server binding
bind = "0.0.0.0:" + os.environ.get("PORT", "8000")

# Workers
workers = multiprocessing.cpu_count() * 2 + 1
max_requests = 1000
max_requests_jitter = 50

# Worker class and threading
worker_class = "sync"  # Use "gevent" for async if needed
threads = 2

# Timeouts
timeout = 60
graceful_timeout = 30
keepalive = 5

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (handled by reverse proxy like Render)
keyfile = None
certfile = None

# Application settings
forwarded_allow_ips = "*"
secure_scheme_headers = {
    "X_PROTO": "https",
    "X_FORWARDED_PROTOCOL": "https",
    "X_FORWARDED_PROTO": "https",
    "X_FORWARDED_SSL": "on",
    "X_SCHEME": "https",
}

# Process naming
proc_name = "janrakshak_ai"
