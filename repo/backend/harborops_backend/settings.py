import os
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from core.security_config import validate_runtime_security_environment


BASE_DIR = Path(__file__).resolve().parent.parent

RUNTIME_PROFILE = os.getenv("APP_RUNTIME_PROFILE", "production").strip().lower()
IS_DEV_PROFILE = RUNTIME_PROFILE in {"dev", "development", "local"}

if "test" not in sys.argv:
    validate_runtime_security_environment()

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "").strip()
if "test" in sys.argv and not SECRET_KEY:
    SECRET_KEY = "test-only-secret-key"
if not SECRET_KEY:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY is required.")

INSECURE_DJANGO_SECRET_KEYS = {
    "change-me",
    "change-me-in-production",
    "replace-me",
}
if not IS_DEV_PROFILE and SECRET_KEY in INSECURE_DJANGO_SECRET_KEYS:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY uses a placeholder value outside dev profile."
    )

DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"
if "test" in sys.argv:
    DEBUG = True
if "test" not in sys.argv and DEBUG and not IS_DEV_PROFILE:
    raise ImproperlyConfigured(
        "DJANGO_DEBUG=true is only allowed when APP_RUNTIME_PROFILE is dev/development/local."
    )

allowed_hosts_raw = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_raw.split(",") if host.strip()]

installed_apps = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "organizations",
    "access",
    "accounts",
    "audit",
    "trips",
    "warehouse",
    "inventory",
    "jobs",
    "security",
    "monitoring",
    "core",
]

INSTALLED_APPS = installed_apps

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "core.security_middleware.ResponseSecurityHeadersMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "core.security_middleware.IdempotencyMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "security.middleware.RequestSigningMiddleware",
    "core.middleware.OrganizationContextMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "harborops_backend.urls"

request_signing_prefixes_raw = os.getenv("REQUEST_SIGNING_PREFIXES", "/api/")
REQUEST_SIGNING_PREFIXES = tuple(
    item.strip() for item in request_signing_prefixes_raw.split(",") if item.strip()
)

request_signing_allowlist_raw = os.getenv(
    "REQUEST_SIGNING_ALLOWLIST_PATHS",
    "/api/auth/login/,/api/auth/register/,/api/auth/captcha/challenge/",
)
REQUEST_SIGNING_ALLOWLIST_PATHS = tuple(
    item.strip() for item in request_signing_allowlist_raw.split(",") if item.strip()
)

if "test" in sys.argv:
    SESSION_REPLAY_REQUIRE_HEADERS = False
    SESSION_SIGNING_REQUIRE_HEADERS = False
else:
    SESSION_REPLAY_REQUIRE_HEADERS = (
        os.getenv("SESSION_REPLAY_REQUIRE_HEADERS", "true").lower() == "true"
    )
    SESSION_SIGNING_REQUIRE_HEADERS = (
        os.getenv("SESSION_SIGNING_REQUIRE_HEADERS", "true").lower() == "true"
    )

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "harborops_backend.wsgi.application"
ASGI_APPLICATION = "harborops_backend.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("DB_NAME", "harborops"),
        "USER": os.getenv("DB_USER", "harborops"),
        "PASSWORD": os.getenv("DB_PASSWORD", "harborops_dev_password"),
        "HOST": os.getenv("DB_HOST", "db"),
        "PORT": os.getenv("DB_PORT", "3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

if "test" in sys.argv:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "test.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "accounts.validators.LetterNumberPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

cors_allowed_raw = os.getenv("CORS_ALLOWED_ORIGINS", "https://localhost:8443")
CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in cors_allowed_raw.split(",") if origin.strip()
]
CORS_ALLOW_CREDENTIALS = True

csrf_trusted_raw = os.getenv(
    "CSRF_TRUSTED_ORIGINS", "https://localhost:8443,https://localhost"
)
CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in csrf_trusted_raw.split(",") if origin.strip()
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "core.throttles.LoginIpThrottle",
        "core.throttles.LoginUsernameThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "login_ip": "20/min",
        "login_username": "10/min",
    },
}

if "test" in sys.argv:
    REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []

PASSWORD_HISTORY_COUNT = 5
ACCOUNT_LOCK_MINUTES = 15
CAPTCHA_AFTER_FAILURES = 5
LOCK_AFTER_FAILURES = 10

BACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
BACKUP_DIR = os.getenv("BACKUP_DIR", str(BASE_DIR / "backups"))

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True

HTTPS_ENABLED = os.getenv("DJANGO_HTTPS_ENABLED", "true").lower() == "true"
if HTTPS_ENABLED:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

if not DEBUG and HTTPS_ENABLED:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True


LOG_LEVEL = os.getenv("DJANGO_LOG_LEVEL", "INFO").upper()
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "core.structured_logging.JsonFormatter",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        }
    },
    "loggers": {
        "harborops": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "django": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_FRAMEWORK_LOG_LEVEL", "WARNING").upper(),
            "propagate": False,
        },
    },
}
