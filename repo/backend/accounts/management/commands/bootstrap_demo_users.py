from django.core.management.base import BaseCommand

from access.models import BaseRole, Role
from accounts.models import User, UserRole
from organizations.models import Organization


class Command(BaseCommand):
    help = "Create demo users for local development"

    def handle(self, *args, **options):
        org = Organization.objects.get(code="HARBOR_DEMO")

        self._upsert_user(
            organization=org,
            username="orgadmin",
            real_name="Org Admin",
            password="SecurePass1234",
            role_code=BaseRole.ORG_ADMIN,
            is_staff=True,
        )
        self._upsert_user(
            organization=org,
            username="senior1",
            real_name="Senior One",
            password="SecurePass1234",
            role_code=BaseRole.SENIOR,
            is_staff=False,
        )
        self._upsert_user(
            organization=org,
            username="family1",
            real_name="Family Member One",
            password="SecurePass1234",
            role_code=BaseRole.FAMILY_MEMBER,
            is_staff=False,
        )
        self._upsert_user(
            organization=org,
            username="caregiver1",
            real_name="Caregiver One",
            password="SecurePass1234",
            role_code=BaseRole.CAREGIVER,
            is_staff=False,
        )
        self._upsert_user(
            organization=org,
            username="platform1",
            real_name="Platform Admin One",
            password="SecurePass1234",
            role_code=BaseRole.PLATFORM_ADMIN,
            is_staff=True,
        )

        self.stdout.write(self.style.SUCCESS("Demo users bootstrapped."))

    def _upsert_user(
        self, organization, username, real_name, password, role_code, is_staff
    ):
        user, _ = User.objects.get_or_create(username=username)
        user.organization = organization
        user.real_name = real_name
        user.is_staff = is_staff
        user.is_active = True
        user.set_password(password)
        user.save()

        role = Role.objects.get(organization=organization, code=role_code)
        UserRole.objects.get_or_create(user=user, role=role)
