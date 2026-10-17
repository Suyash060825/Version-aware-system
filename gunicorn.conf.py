"""
gunicorn.conf.py
Production Gunicorn configuration with master process model preloading.
"""
import os

bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:5000")
workers = int(os.environ.get("GUNICORN_WORKERS", "4"))
threads = int(os.environ.get("GUNICORN_THREADS", "4"))
worker_class = os.environ.get("GUNICORN_WORKER_CLASS", "gthread")
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))
keepalive = int(os.environ.get("GUNICORN_KEEPALIVE", "5"))

# Preload application and models in the master process before worker fork (copy-on-write).
# This avoids per-worker cold starts and drastically cuts RAM usage.
preload_app = True
