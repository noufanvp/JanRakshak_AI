#!/bin/bash
# Vercel build script for Django

echo "==> Collecting static files..."
python3 manage.py collectstatic --noinput --clear

echo "==> Build complete."
