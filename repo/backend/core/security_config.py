import base64
import os

from django.core.exceptions import ImproperlyConfigured

INSECURE_DEFAULT_AES_KEYS = {
    "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=",
    "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=",
}

INSECURE_PLACEHOLDER_AES_KEYS = {
    "change-me",
    "replace-me",
    "replace-with-generated-key",
    "replace-with-unique-key",
}

INSECURE_SECRET_VALUES = {
    "",
    "change-me",
    "change-me-in-production",
    "replace-me",
    "changeme",
    "default",
    "replace-with-strong-db-password",
    "replace-with-strong-root-password",
    "replace-with-strong-django-secret",
    "replace-with-strong-passphrase",
    "harborops_dev_db_password_local_only",
    "harborops_dev_root_password_local_only",
    "django-insecure-harborops-local-dev-secret-key-2026",
    "harborops-local-backup-passphrase-2026",
}


def _validate_secret_var(name, min_length=12):
    value = os.getenv(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"{name} is required.")
    if value.lower() in INSECURE_SECRET_VALUES:
        raise ImproperlyConfigured(
            f"{name} uses an insecure default or placeholder value."
        )
    if len(value) < min_length:
        raise ImproperlyConfigured(f"{name} must be at least {min_length} characters.")
    return True


def _validate_any_secret_var(names, label, min_length=12):
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            if value.lower() in INSECURE_SECRET_VALUES:
                raise ImproperlyConfigured(
                    f"{label} uses an insecure default or placeholder value."
                )
            if len(value) < min_length:
                raise ImproperlyConfigured(
                    f"{label} must be at least {min_length} characters."
                )
            return True
    raise ImproperlyConfigured(f"{label} is required.")


def validate_app_aes_key_environment():
    key_b64 = os.getenv("APP_AES256_KEY_B64", "").strip()
    if not key_b64:
        raise ImproperlyConfigured(
            "APP_AES256_KEY_B64 is required and must be a unique base64-encoded 32-byte key."
        )
    if key_b64 in INSECURE_DEFAULT_AES_KEYS:
        raise ImproperlyConfigured(
            "APP_AES256_KEY_B64 uses an insecure default value; configure a unique key."
        )
    if key_b64.lower() in INSECURE_PLACEHOLDER_AES_KEYS:
        raise ImproperlyConfigured(
            "APP_AES256_KEY_B64 uses a placeholder value; configure a unique key."
        )
    try:
        decoded = base64.b64decode(key_b64, validate=True)
    except Exception as exc:  # pragma: no cover - exact exception varies by runtime
        raise ImproperlyConfigured(
            "APP_AES256_KEY_B64 must be valid base64 and decode to 32 bytes."
        ) from exc
    if len(decoded) != 32:
        raise ImproperlyConfigured(
            "APP_AES256_KEY_B64 must decode to exactly 32 bytes."
        )
    return True


def validate_runtime_security_environment():
    validate_app_aes_key_environment()
    _validate_secret_var("DJANGO_SECRET_KEY", min_length=24)
    _validate_any_secret_var(["MYSQL_PASSWORD", "DB_PASSWORD"], "DB password")
    _validate_any_secret_var(
        ["MYSQL_ROOT_PASSWORD", "DB_ADMIN_PASSWORD"], "DB admin password"
    )
    _validate_secret_var("BACKUP_PASSPHRASE", min_length=12)
    return True
