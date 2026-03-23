#!/bin/bash
echo "--- Starting Vercel Build Script ---"
# Install dependencies (Vercel does this automatically, but we ensure it)
pip install -r requirements.txt
# Run migrations
python manage.py migrate --noinput
# Collect static files
python manage.py collectstatic --noinput
echo "--- Vercel Build Script Completed ---"
