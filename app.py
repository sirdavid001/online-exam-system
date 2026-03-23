"""Render-compatible WSGI entrypoint.

Allows start command: gunicorn app:app
"""

import os


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "onlinexam.settings")

from django.core.wsgi import get_wsgi_application
from onlinexam.bootstrap import ensure_runtime_bootstrap


app = get_wsgi_application()
ensure_runtime_bootstrap()
