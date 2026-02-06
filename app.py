"""Render-compatible WSGI entrypoint.

Allows start command: gunicorn app:app
"""

import os

import django
from django.core.management import call_command
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "onlinexam.settings")


def _should_run_startup_migrations():
    explicit = os.getenv("RUN_MIGRATIONS_ON_STARTUP", "").strip().lower()
    if explicit in {"1", "true", "yes", "on"}:
        return True
    if explicit in {"0", "false", "no", "off"}:
        return False
    return bool(os.getenv("RENDER_SERVICE_ID"))


if _should_run_startup_migrations():
    django.setup()
    call_command("migrate", interactive=False, verbosity=0)

app = get_wsgi_application()
