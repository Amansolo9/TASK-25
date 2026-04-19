from django.core.management.base import BaseCommand

from access.models import BaseRole, Permission, Role, RolePermission
from organizations.models import Organization


BASE_PERMISSIONS = [
    ("trip.read", "trips", "read"),
    ("trip.write", "trips", "write"),
    ("booking.write", "bookings", "write"),
    ("warehouse.read", "warehouses", "read"),
    ("warehouse.write", "warehouses", "write"),
    ("inventory.read", "inventory", "read"),
    ("inventory.write", "inventory", "write"),
    ("verification.review", "verification", "review"),
    ("audit.read", "audit", "read"),
    ("jobs.read", "jobs", "read"),
    ("jobs.write", "jobs", "write"),
    ("monitoring.read", "monitoring", "read"),
    ("monitoring.write", "monitoring", "write"),
    ("export.read.any", "exports", "read_any"),
    ("sensitive.unmask", "sensitive", "unmask"),
]


ROLE_DEFAULTS = {
    BaseRole.SENIOR: ["trip.read", "booking.write"],
    BaseRole.FAMILY_MEMBER: ["trip.read", "booking.write"],
    BaseRole.CAREGIVER: ["trip.read", "trip.write", "booking.write"],
    BaseRole.ORG_ADMIN: [
        "trip.read",
        "trip.write",
        "booking.write",
        "warehouse.read",
        "warehouse.write",
        "inventory.read",
        "inventory.write",
        "verification.review",
        "audit.read",
        "jobs.read",
        "jobs.write",
        "monitoring.read",
        "monitoring.write",
        "export.read.any",
        "sensitive.unmask",
    ],
    BaseRole.PLATFORM_ADMIN: [
        "trip.read",
        "trip.write",
        "booking.write",
        "warehouse.read",
        "warehouse.write",
        "inventory.read",
        "inventory.write",
        "verification.review",
        "audit.read",
        "jobs.read",
        "jobs.write",
        "monitoring.read",
        "monitoring.write",
        "export.read.any",
        "sensitive.unmask",
    ],
}


class Command(BaseCommand):
    help = "Bootstrap base roles and permissions for each organization"

    def handle(self, *args, **options):
        permission_map = {}
        for code, screen, action in BASE_PERMISSIONS:
            permission, _ = Permission.objects.get_or_create(
                code=code,
                defaults={
                    "screen": screen,
                    "action": action,
                    "description": f"{action} access to {screen}",
                },
            )
            permission_map[code] = permission

        for organization in Organization.objects.filter(is_active=True):
            for role_code, permission_codes in ROLE_DEFAULTS.items():
                role, _ = Role.objects.get_or_create(
                    organization=organization,
                    code=role_code,
                    defaults={
                        "name": role_code.replace("_", " ").title(),
                        "is_base_role": True,
                    },
                )
                for permission_code in permission_codes:
                    RolePermission.objects.get_or_create(
                        role=role,
                        permission=permission_map[permission_code],
                    )

        self.stdout.write(
            self.style.SUCCESS("Access roles and permissions bootstrapped.")
        )
