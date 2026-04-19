from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from security.models import ApiClientKey


class Command(BaseCommand):
    help = "Revoke an API signing key immediately"

    def add_arguments(self, parser):
        parser.add_argument("key_id")

    def handle(self, *args, **options):
        key = ApiClientKey.objects.filter(key_id=options["key_id"]).first()
        if not key:
            raise CommandError("key_id not found")

        key.is_active = False
        key.revoked_at = timezone.now()
        key.save(update_fields=["is_active", "revoked_at"])
        self.stdout.write(self.style.SUCCESS(f"Revoked key {key.key_id}"))
