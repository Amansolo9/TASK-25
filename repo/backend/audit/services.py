from audit.models import AuditEvent
from core.structured_logging import log_app_event


def record_audit_event(
    *,
    event_type,
    request=None,
    actor=None,
    organization=None,
    resource_type="",
    resource_id="",
    metadata=None,
):
    ip_address = None
    if request is not None:
        ip_address = request.META.get("REMOTE_ADDR")

    AuditEvent.objects.create(
        organization=organization,
        actor=actor,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        metadata_json=metadata or {},
    )

    log_app_event(
        "audit",
        event_type,
        organization_id=getattr(organization, "id", None),
        actor_id=getattr(actor, "id", None),
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        metadata=metadata or {},
    )
