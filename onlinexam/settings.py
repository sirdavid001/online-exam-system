import os

import dj_database_url
from dotenv import load_dotenv

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
MEDIA_ROOT = os.path.join(BASE_DIR, "static")

# Load .env file
load_dotenv(os.path.join(BASE_DIR, ".env"))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-change-me")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

def _split_csv_env(name, default=""):
    return [value.strip() for value in os.getenv(name, default).split(",") if value.strip()]


ALLOWED_HOSTS = _split_csv_env("ALLOWED_HOSTS", "127.0.0.1,localhost,testserver")

render_external_host = os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip()
if render_external_host and render_external_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_external_host)

if os.getenv("RENDER_SERVICE_ID") and ".onrender.com" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(".onrender.com")

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "exam",
    "teacher",
    "student",
    "widget_tweaks",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG

ROOT_URLCONF = "onlinexam.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [TEMPLATE_DIR],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "onlinexam.wsgi.application"

# Database
database_url = os.getenv("DATABASE_URL", "").strip()
if database_url:
    parse_kwargs = {"conn_max_age": 600}
    if database_url.startswith(("postgres://", "postgresql://", "postgis://")):
        parse_kwargs["ssl_require"] = not DEBUG

    DATABASES = {
        "default": dj_database_url.parse(
            database_url,
            **parse_kwargs,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATICFILES_DIRS = [STATIC_DIR]
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# WhiteNoise static serving for production (Render/gunicorn).
# Default to non-manifest storage so deployments still work even if
# collectstatic was not run yet.
USE_MANIFEST_STATICFILES = os.getenv("USE_MANIFEST_STATICFILES", "False").lower() == "true"
if USE_MANIFEST_STATICFILES:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
    WHITENOISE_MANIFEST_STRICT = False
else:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

WHITENOISE_USE_FINDERS = True

LOGIN_REDIRECT_URL = "/afterlogin"
AUTHENTICATION_BACKENDS = [
    "exam.auth_backends.MultiIdentifierBackend",
    "django.contrib.auth.backends.ModelBackend",
]
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Contact-us and auth emails (all secrets via environment variables)
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "").strip()
BREVO_SENDER_NAME = os.getenv("BREVO_SENDER_NAME", "").strip()
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "").strip()

EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "").strip()
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "").strip()
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "20"))

configured_from_email = os.getenv("DEFAULT_FROM_EMAIL", "").strip()

if BREVO_API_KEY:
    # Brevo transactional API mode (uses API key provided by user).
    EMAIL_BACKEND = "exam.email_backends.BrevoAPIEmailBackend"
    DEFAULT_FROM_EMAIL = (
        configured_from_email
        or BREVO_SENDER_EMAIL
        or EMAIL_HOST_USER
        or "noreply@online-exam.local"
    )
elif EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    # Generic SMTP mode (Gmail or other SMTP provider).
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com").strip()
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
    DEFAULT_FROM_EMAIL = configured_from_email or EMAIL_HOST_USER
else:
    # Local/dev fallback.
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    DEFAULT_FROM_EMAIL = configured_from_email or "noreply@online-exam.local"

EMAIL_RECEIVING_USER = [
    email.strip()
    for email in os.getenv("EMAIL_RECEIVING_USER", "").split(",")
    if email.strip()
]

if not EMAIL_RECEIVING_USER and "@" in DEFAULT_FROM_EMAIL:
    EMAIL_RECEIVING_USER = [DEFAULT_FROM_EMAIL]
