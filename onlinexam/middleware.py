import threading

from django.conf import settings
from django.core.management import call_command
from django.db import connection


_schema_checked = False
_schema_lock = threading.Lock()


def _auth_user_exists():
    with connection.cursor() as cursor:
        if connection.vendor == "postgresql":
            cursor.execute("SELECT to_regclass('public.auth_user')")
            return bool(cursor.fetchone()[0])
        return "auth_user" in connection.introspection.table_names(cursor)


class EnsureSchemaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        global _schema_checked

        if getattr(settings, "RUNNING_ON_VERCEL", False) and not _schema_checked:
            with _schema_lock:
                if not _schema_checked:
                    if not _auth_user_exists():
                        call_command("migrate", interactive=False, run_syncdb=True, verbosity=0)
                    _schema_checked = True

        return self.get_response(request)
