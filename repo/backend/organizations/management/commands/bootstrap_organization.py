from django.core.management.base import BaseCommand

from organizations.models import Organization


class Command(BaseCommand):
    help = "Create a default organization for local development"

    def handle(self, *args, **options):
        organization, created = Organization.objects.get_or_create(
            code="HARBOR_DEMO",
            defaults={"name": "HarborOps Demo Organization"},
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(f"Created organization {organization.code}")
            )
        else:
            self.stdout.write(
                self.style.WARNING(f"Organization {organization.code} already exists")
            )
