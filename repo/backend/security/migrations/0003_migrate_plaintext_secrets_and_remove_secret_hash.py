import hashlib

from django.db import migrations


def migrate_plaintext_secrets(apps, schema_editor):
    ApiClientKey = apps.get_model("security", "ApiClientKey")
    try:
        from core.crypto import encrypt_text
    except Exception:
        return

    for key in ApiClientKey.objects.all().iterator():
        secret_hash = getattr(key, "secret_hash", "") or ""
        if secret_hash and not key.secret_encrypted:
            key.secret_encrypted = encrypt_text(secret_hash)
            key.secret_fingerprint = hashlib.sha256(
                secret_hash.encode("utf-8")
            ).hexdigest()
            key.save(update_fields=["secret_encrypted", "secret_fingerprint"])


class Migration(migrations.Migration):
    dependencies = [
        ("security", "0002_apiclientkey_secret_encrypted_and_more"),
    ]

    operations = [
        migrations.RunPython(
            migrate_plaintext_secrets,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name="apiclientkey",
            name="secret_hash",
        ),
    ]
