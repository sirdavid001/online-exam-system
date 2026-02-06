"""Render-compatible WSGI entrypoint.

Allows start command: gunicorn app:app
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "onlinexam.settings")

app = get_wsgi_application()
