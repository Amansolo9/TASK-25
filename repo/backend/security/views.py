from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from access.services import user_has_permission
from accounts.models import TravelerProfile
from audit.services import record_audit_event
from security.serializers import UnmaskAccessSessionSerializer
from security.services import create_unmask_session, has_active_unmask_session


class UnmaskSessionCreateView(APIView):
    def post(self, request):
        if not user_has_permission(request.user, "sensitive.unmask"):
            return Response(
                {"detail": "Missing permission: sensitive.unmask"}, status=403
            )

        field_name = request.data.get("field_name", "")
        reason = request.data.get("reason", "").strip()
        if not field_name or not reason:
            return Response(
                {"detail": "field_name and reason are required"}, status=400
            )

        session = create_unmask_session(
            user=request.user,
            field_name=field_name,
            reason=reason,
            minutes=int(request.data.get("minutes", 5)),
        )
        record_audit_event(
            event_type="sensitive.unmask.session_created",
            request=request,
            actor=request.user,
            organization=request.user.organization,
            resource_type="unmask_session",
            resource_id=str(session.id),
            metadata={"field_name": field_name, "reason": reason},
        )
        return Response(UnmaskAccessSessionSerializer(session).data, status=201)


class TravelerIdentifierRevealView(APIView):
    FIELD_MAP = {
        "identifier": (
            "traveler_identifier",
            "identifier",
            lambda profile: profile.get_identifier(),
        ),
        "government-id": (
            "traveler_government_id",
            "government_id",
            lambda profile: profile.get_government_id(),
        ),
        "credential-number": (
            "traveler_credential_number",
            "credential_number",
            lambda profile: profile.get_credential_number(),
        ),
    }

    def _reveal(self, request, profile, sensitive_field):
        field_config = self.FIELD_MAP.get(sensitive_field)
        if field_config is None:
            return Response({"detail": "Unsupported sensitive field"}, status=400)

        session_prefix, response_field, getter = field_config
        field_name = f"{session_prefix}:{profile.id}"
        if not has_active_unmask_session(user=request.user, field_name=field_name):
            return Response(
                {"detail": "No active unmask session for this field"}, status=403
            )

        record_audit_event(
            event_type="sensitive.unmask.viewed",
            request=request,
            actor=request.user,
            organization=request.user.organization,
            resource_type="traveler_profile",
            resource_id=str(profile.id),
            metadata={"field_name": field_name},
        )
        return Response({response_field: getter(profile)})

    def get(self, request, profile_id):
        profile = get_object_or_404(
            TravelerProfile,
            id=profile_id,
            user__organization=request.user.organization,
        )
        return self._reveal(request, profile, "identifier")


class TravelerSensitiveFieldRevealView(APIView):
    FIELD_MAP = TravelerIdentifierRevealView.FIELD_MAP

    def _reveal(self, request, profile, sensitive_field):
        return TravelerIdentifierRevealView()._reveal(
            request,
            profile,
            sensitive_field,
        )

    def get(self, request, profile_id, sensitive_field):
        profile = get_object_or_404(
            TravelerProfile,
            id=profile_id,
            user__organization=request.user.organization,
        )
        return self._reveal(request, profile, sensitive_field)
