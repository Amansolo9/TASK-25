import hashlib
import secrets

from django.core.management.base import BaseCommand, CommandError

from core.crypto import encrypt_text
from security.models import ApiClientKey


class Command(BaseCommand):
    help = "Rotate an existing API signing key"

    def add_arguments(self, parser):
        parser.add_argument("key_id")
        parser.add_argument(
            "--reveal-secret",
            action="store_true",
            help="Print the full rotated secret (not recommended)",
        )

    @staticmethod
    def _masked_secret(secret):
        return f"{secret[:4]}...{secret[-4:]}"

    def handle(self, *args, **options):
        key = ApiClientKey.objects.filter(
            key_id=options["key_id"], is_active=True
        ).first()
        if not key:
            raise CommandError("Active key_id not found")

        secret = secrets.token_hex(32)
        key.secret_encrypted = encrypt_text(secret)
        key.secret_fingerprint = hashlib.sha256(secret.encode("utf-8")).hexdigest()
        key.save(update_fields=["secret_encrypted", "secret_fingerprint"])
        if options["reveal_secret"]:
            self.stderr.write(
                "Warning: revealing raw secret in terminal output. Avoid logging this output."
            )
            self.stdout.write(
                self.style.SUCCESS(f"Rotated key {key.key_id} secret={secret}")
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Rotated key {key.key_id} secret={self._masked_secret(secret)}"
            )
        )
