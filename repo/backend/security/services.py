from datetime import timedelta

from django.utils import timezone

from security.models import UnmaskAccessSession


def create_unmask_session(*, user, field_name, reason, minutes=5):
    expires_at = timezone.now() + timedelta(minutes=minutes)
    return UnmaskAccessSession.objects.create(
        organization=user.organization,
        user=user,
        field_name=field_name,
        reason=reason,
        expires_at=expires_at,
    )


def has_active_unmask_session(*, user, field_name):
    return UnmaskAccessSession.objects.filter(
        user=user,
        field_name=field_name,
        expires_at__gt=timezone.now(),
    ).exists()
