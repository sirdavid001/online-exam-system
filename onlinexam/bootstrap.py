import os
import threading

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


_bootstrap_lock = threading.Lock()
_bootstrap_done = False


def _auth_user_exists():
    with connection.cursor() as cursor:
        if connection.vendor == "postgresql":
            cursor.execute("SELECT to_regclass('public.auth_user')")
            return bool(cursor.fetchone()[0])
        return "auth_user" in connection.introspection.table_names(cursor)


def _has_pending_migrations():
    executor = MigrationExecutor(connection)
    targets = executor.loader.graph.leaf_nodes()
    return bool(executor.migration_plan(targets))


def _admin_credentials():
    username = (
        os.getenv("ADMIN_USERNAME")
        or os.getenv("DJANGO_SUPERUSER_USERNAME")
        or ""
    ).strip()
    password = (
        os.getenv("ADMIN_PASSWORD")
        or os.getenv("DJANGO_SUPERUSER_PASSWORD")
        or ""
    )
    email = (
        os.getenv("ADMIN_EMAIL")
        or os.getenv("DJANGO_SUPERUSER_EMAIL")
        or getattr(settings, "DEFAULT_FROM_EMAIL", "")
        or ""
    ).strip()
    return username, password, email


def _ensure_admin_user():
    username, password, email = _admin_credentials()
    if not username or not password:
        return

    User = get_user_model()
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "email": email,
            "is_staff": True,
            "is_superuser": True,
            "is_active": True,
        },
    )

    changed = created
    if email and user.email != email:
        user.email = email
        changed = True
    if not user.is_staff:
        user.is_staff = True
        changed = True
    if not user.is_superuser:
        user.is_superuser = True
        changed = True
    if not user.is_active:
        user.is_active = True
        changed = True
    if not user.check_password(password):
        user.set_password(password)
        changed = True

    if changed:
        user.save()


def ensure_runtime_bootstrap():
    global _bootstrap_done

    running_on_vercel = getattr(settings, "RUNNING_ON_VERCEL", False)
    admin_username, admin_password, _ = _admin_credentials()
    needs_admin = bool(admin_username and admin_password)

    if not running_on_vercel and not needs_admin:
        return

    with _bootstrap_lock:
        if _bootstrap_done:
            return

        if running_on_vercel and _has_pending_migrations():
            call_command("migrate", interactive=False, run_syncdb=True, verbosity=0)

        if needs_admin and _auth_user_exists():
            _ensure_admin_user()

        _bootstrap_done = True
