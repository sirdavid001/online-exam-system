"""Render-compatible WSGI entrypoint.

Allows start command: gunicorn app:app
"""

import os

import django
from django.contrib.auth import get_user_model
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


def _superuser_env_credentials():
    username = os.getenv("DJANGO_SUPERUSER_USERNAME", "").strip()
    password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "").strip()
    email = os.getenv("DJANGO_SUPERUSER_EMAIL", "").strip()
    return username, password, email


def _bootstrap_superuser_from_env():
    username, password, email = _superuser_env_credentials()
    if not username or not password:
        return

    user_model = get_user_model()
    user, _ = user_model.objects.get_or_create(username=username)

    user.is_staff = True
    user.is_superuser = True
    user.is_active = True
    if email:
        user.email = email
    user.set_password(password)
    user.save()


run_migrations_on_startup = _should_run_startup_migrations()
bootstrap_superuser = bool(_superuser_env_credentials()[0] and _superuser_env_credentials()[1])

if run_migrations_on_startup or bootstrap_superuser:
    django.setup()

if run_migrations_on_startup:
    call_command("migrate", interactive=False, verbosity=0)

if bootstrap_superuser:
    _bootstrap_superuser_from_env()

app = get_wsgi_application()
