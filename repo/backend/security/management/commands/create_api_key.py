import secrets
import hashlib

from django.core.management.base import BaseCommand, CommandError

from core.crypto import encrypt_text
from organizations.models import Organization
from security.models import ApiClientKey


class Command(BaseCommand):
    help = "Create local API signing key for offline workers"

    def add_arguments(self, parser):
        parser.add_argument("organization_code")
        parser.add_argument("key_id")
        parser.add_argument(
            "--reveal-secret",
            action="store_true",
            help="Print the full generated secret (not recommended)",
        )

    @staticmethod
    def _masked_secret(secret):
        return f"{secret[:4]}...{secret[-4:]}"

    def handle(self, *args, **options):
        org = Organization.objects.filter(code=options["organization_code"]).first()
        if not org:
            raise CommandError("Organization not found")

        if ApiClientKey.objects.filter(key_id=options["key_id"]).exists():
            raise CommandError("key_id already exists")

        secret = secrets.token_hex(32)
        ApiClientKey.objects.create(
            organization=org,
            key_id=options["key_id"],
            secret_encrypted=encrypt_text(secret),
            secret_fingerprint=hashlib.sha256(secret.encode("utf-8")).hexdigest(),
            is_active=True,
        )
        if options["reveal_secret"]:
            self.stderr.write(
                "Warning: revealing raw secret in terminal output. Avoid logging this output."
            )
            self.stdout.write(
                self.style.SUCCESS(f"Created key {options['key_id']} secret={secret}")
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Created key {options['key_id']} secret={self._masked_secret(secret)}"
            )
        )
