"""Render-compatible WSGI entrypoint.

Allows start command: gunicorn app:app
"""

import os


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "onlinexam.settings")

from django.core.management import call_command
from django.core.wsgi import get_wsgi_application
from django.conf import settings
from django.db import connection


def _ensure_schema():
    # Legacy Vercel builds can skip the configured build command. If the
    # database is present but empty, bootstrap the schema on cold start.
    if not getattr(settings, "RUNNING_ON_VERCEL", False):
        return

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('public.auth_user')")
            auth_user_table = cursor.fetchone()[0]
    except Exception:
        return

    if auth_user_table:
        return

    call_command("migrate", interactive=False, run_syncdb=True, verbosity=0)


app = get_wsgi_application()
_ensure_schema()
