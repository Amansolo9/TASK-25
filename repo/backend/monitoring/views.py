from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from access.services import is_platform_admin, user_has_permission
from monitoring.models import AlertThreshold, AnomalyAlert
from monitoring.serializers import AlertThresholdSerializer, AnomalyAlertSerializer


class AnomalyAlertListView(APIView):
    def get(self, request):
        if not user_has_permission(request.user, "monitoring.read"):
            return Response(
                {"detail": "Missing permission: monitoring.read"}, status=403
            )
        queryset = AnomalyAlert.objects.all()
        if is_platform_admin(request.user):
            org_id = request.GET.get("organization_id")
            if org_id:
                queryset = queryset.filter(organization_id=org_id)
        else:
            queryset = queryset.filter(organization=request.user.organization)
        queryset = queryset.order_by("-created_at")
        return Response(AnomalyAlertSerializer(queryset, many=True).data)


class AnomalyAlertAcknowledgeView(APIView):
    def post(self, request, alert_id):
        if not user_has_permission(request.user, "monitoring.read"):
            return Response(
                {"detail": "Missing permission: monitoring.read"}, status=403
            )
        alert = get_object_or_404(
            AnomalyAlert,
            id=alert_id,
            **(
                {"organization": request.user.organization}
                if not is_platform_admin(request.user)
                else {}
            ),
        )
        alert.acknowledged = True
        alert.save(update_fields=["acknowledged"])
        return Response(AnomalyAlertSerializer(alert).data)


class AlertThresholdListCreateView(APIView):
    def get(self, request):
        if not user_has_permission(request.user, "monitoring.read"):
            return Response(
                {"detail": "Missing permission: monitoring.read"}, status=403
            )
        queryset = AlertThreshold.objects.all()
        if is_platform_admin(request.user):
            org_id = request.GET.get("organization_id")
            if org_id:
                queryset = queryset.filter(organization_id=org_id)
        else:
            queryset = queryset.filter(organization=request.user.organization)
        return Response(AlertThresholdSerializer(queryset, many=True).data)

    def post(self, request):
        if not user_has_permission(request.user, "monitoring.write"):
            return Response(
                {"detail": "Missing permission: monitoring.write"}, status=403
            )
        serializer = AlertThresholdSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization = request.user.organization
        if is_platform_admin(request.user) and request.data.get("organization_id"):
            from organizations.models import Organization

            organization = Organization.objects.filter(
                id=request.data.get("organization_id"), is_active=True
            ).first()
        if organization is None:
            return Response(
                {"detail": "Valid organization_id is required."}, status=400
            )
        obj = serializer.save(organization=organization)
        return Response(
            AlertThresholdSerializer(obj).data, status=status.HTTP_201_CREATED
        )
