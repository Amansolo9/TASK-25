from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from access.services import is_platform_admin, user_has_permission
from audit.services import record_audit_event
from organizations.models import Organization
from warehouse.models import Location, PartnerRecord, Warehouse, Zone
from warehouse.serializers import (
    LocationSerializer,
    PartnerRecordSerializer,
    WarehouseSerializer,
    ZoneSerializer,
)


class WarehouseListCreateView(APIView):
    def get(self, request):
        if not user_has_permission(request.user, "warehouse.read"):
            return Response(
                {"detail": "Missing permission: warehouse.read"}, status=403
            )
        queryset = Warehouse.objects.all()
        if is_platform_admin(request.user):
            org_id = request.GET.get("organization_id")
            if org_id:
                queryset = queryset.filter(organization_id=org_id)
        else:
            queryset = queryset.filter(organization=request.user.organization)
        queryset = queryset.order_by("name")
        return Response(WarehouseSerializer(queryset, many=True).data)

    def post(self, request):
        if not user_has_permission(request.user, "warehouse.write"):
            return Response(
                {"detail": "Missing permission: warehouse.write"}, status=403
            )

        serializer = WarehouseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization = request.user.organization
        if is_platform_admin(request.user) and request.data.get("organization_id"):
            organization = Organization.objects.filter(
                id=request.data.get("organization_id"), is_active=True
            ).first()
        if organization is None:
            return Response(
                {"detail": "Valid organization_id is required."}, status=400
            )
        obj = serializer.save(organization=organization)
        record_audit_event(
            event_type="warehouse.created",
            request=request,
            actor=request.user,
            organization=request.user.organization,
            resource_type="warehouse",
            resource_id=str(obj.id),
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class WarehouseDetailView(APIView):
    def put(self, request, warehouse_id):
        if not user_has_permission(request.user, "warehouse.write"):
            return Response(
                {"detail": "Missing permission: warehouse.write"}, status=403
            )
        warehouse = Warehouse.objects.filter(id=warehouse_id).first()
        if not warehouse:
            return Response({"detail": "Warehouse not found"}, status=404)
        if (
            not is_platform_admin(request.user)
            and warehouse.organization_id != request.user.organization_id
        ):
            return Response(
                {"detail": "Warehouse out of organization scope."}, status=404
            )
        serializer = WarehouseSerializer(warehouse, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, warehouse_id):
        if not user_has_permission(request.user, "warehouse.write"):
            return Response(
                {"detail": "Missing permission: warehouse.write"}, status=403
            )
        queryset = Warehouse.objects.filter(id=warehouse_id)
        if not is_platform_admin(request.user):
            queryset = queryset.filter(organization=request.user.organization)
        deleted, _ = queryset.delete()
        if not deleted:
            return Response({"detail": "Warehouse not found"}, status=404)
        return Response(status=204)


class ZoneListCreateView(APIView):
    def get(self, request):
        if not user_has_permission(request.user, "warehouse.read"):
            return Response(
                {"detail": "Missing permission: warehouse.read"}, status=403
            )
        queryset = Zone.objects.all()
        if is_platform_admin(request.user):
            org_id = request.GET.get("organization_id")
            if org_id:
                queryset = queryset.filter(warehouse__organization_id=org_id)
        else:
            queryset = queryset.filter(
                warehouse__organization=request.user.organization
            )
        queryset = queryset.order_by("name")
        return Response(ZoneSerializer(queryset, many=True).data)

    def post(self, request):
        if not user_has_permission(request.user, "warehouse.write"):
            return Response(
                {"detail": "Missing permission: warehouse.write"}, status=403
            )
        serializer = ZoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        warehouse = serializer.validated_data["warehouse"]
        if (
            not is_platform_admin(request.user)
            and warehouse.organization_id != request.user.organization_id
        ):
            return Response(
                {"detail": "Warehouse out of organization scope."}, status=400
            )
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ZoneDetailView(APIView):
    def put(self, request, zone_id):
        if not user_has_permission(request.user, "warehouse.write"):
            return Response(
                {"detail": "Missing permission: warehouse.write"}, status=403
            )
        zone = Zone.objects.select_related("warehouse").filter(id=zone_id).first()
        if not zone:
            return Response({"detail": "Zone not found"}, status=404)
        if (
            not is_platform_admin(request.user)
            and zone.warehouse.organization_id != request.user.organization_id
        ):
            return Response({"detail": "Zone out of organization scope."}, status=404)
        serializer = ZoneSerializer(zone, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, zone_id):
        if not user_has_permission(request.user, "warehouse.write"):
            return Response(
                {"detail": "Missing permission: warehouse.write"}, status=403
            )
        queryset = Zone.objects.filter(id=zone_id)
        if not is_platform_admin(request.user):
            queryset = queryset.filter(
                warehouse__organization=request.user.organization
            )
        deleted, _ = queryset.delete()
        if not deleted:
            return Response({"detail": "Zone not found"}, status=404)
        return Response(status=204)


class LocationListCreateView(APIView):
    def get(self, request):
        if not user_has_permission(request.user, "warehouse.read"):
            return Response(
                {"detail": "Missing permission: warehouse.read"}, status=403
            )
        queryset = Location.objects.all()
        if is_platform_admin(request.user):
            org_id = request.GET.get("organization_id")
            if org_id:
                queryset = queryset.filter(zone__warehouse__organization_id=org_id)
        else:
            queryset = queryset.filter(
                zone__warehouse__organization=request.user.organization
            )
        return Response(LocationSerializer(queryset, many=True).data)

    def post(self, request):
        if not user_has_permission(request.user, "warehouse.write"):
            return Response(
                {"detail": "Missing permission: warehouse.write"}, status=403
            )
        serializer = LocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        zone = serializer.validated_data["zone"]
        if (
            not is_platform_admin(request.user)
            and zone.warehouse.organization_id != request.user.organization_id
        ):
            return Response({"detail": "Zone out of organization scope."}, status=400)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LocationDetailView(APIView):
    def put(self, request, location_id):
        if not user_has_permission(request.user, "warehouse.write"):
            return Response(
                {"detail": "Missing permission: warehouse.write"}, status=403
            )
        location = (
            Location.objects.select_related("zone__warehouse")
            .filter(id=location_id)
            .first()
        )
        if not location:
            return Response({"detail": "Location not found"}, status=404)
        if (
            not is_platform_admin(request.user)
            and location.zone.warehouse.organization_id != request.user.organization_id
        ):
            return Response(
                {"detail": "Location out of organization scope."}, status=404
            )
        serializer = LocationSerializer(location, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, location_id):
        if not user_has_permission(request.user, "warehouse.write"):
            return Response(
                {"detail": "Missing permission: warehouse.write"}, status=403
            )
        queryset = Location.objects.filter(id=location_id)
        if not is_platform_admin(request.user):
            queryset = queryset.filter(
                zone__warehouse__organization=request.user.organization
            )
        deleted, _ = queryset.delete()
        if not deleted:
            return Response({"detail": "Location not found"}, status=404)
        return Response(status=204)


class PartnerRecordListCreateView(APIView):
    def get(self, request):
        if not user_has_permission(request.user, "warehouse.read"):
            return Response(
                {"detail": "Missing permission: warehouse.read"}, status=403
            )
        queryset = PartnerRecord.objects.all()
        if is_platform_admin(request.user):
            org_id = request.GET.get("organization_id")
            if org_id:
                queryset = queryset.filter(organization_id=org_id)
        else:
            queryset = queryset.filter(organization=request.user.organization)
        queryset = queryset.order_by(
            "partner_type", "external_code", "-effective_start"
        )
        return Response(PartnerRecordSerializer(queryset, many=True).data)

    def post(self, request):
        if not user_has_permission(request.user, "warehouse.write"):
            return Response(
                {"detail": "Missing permission: warehouse.write"}, status=403
            )
        serializer = PartnerRecordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization = request.user.organization
        if is_platform_admin(request.user) and request.data.get("organization_id"):
            organization = Organization.objects.filter(
                id=request.data.get("organization_id"), is_active=True
            ).first()
        if organization is None:
            return Response(
                {"detail": "Valid organization_id is required."}, status=400
            )
        obj = serializer.save(organization=organization)
        try:
            obj.full_clean()
            obj.save()
        except ValidationError as exc:
            obj.delete()
            return Response({"detail": exc.message_dict or exc.messages}, status=400)
        return Response(
            PartnerRecordSerializer(obj).data, status=status.HTTP_201_CREATED
        )


class PartnerRecordDetailView(APIView):
    def put(self, request, partner_id):
        if not user_has_permission(request.user, "warehouse.write"):
            return Response(
                {"detail": "Missing permission: warehouse.write"}, status=403
            )
        partner = PartnerRecord.objects.filter(id=partner_id).first()
        if not partner:
            return Response({"detail": "Partner not found"}, status=404)
        if (
            not is_platform_admin(request.user)
            and partner.organization_id != request.user.organization_id
        ):
            return Response(
                {"detail": "Partner out of organization scope."}, status=404
            )
        serializer = PartnerRecordSerializer(partner, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        try:
            obj.full_clean()
            obj.save()
        except ValidationError as exc:
            return Response({"detail": exc.message_dict or exc.messages}, status=400)
        return Response(PartnerRecordSerializer(obj).data)

    def delete(self, request, partner_id):
        if not user_has_permission(request.user, "warehouse.write"):
            return Response(
                {"detail": "Missing permission: warehouse.write"}, status=403
            )
        queryset = PartnerRecord.objects.filter(id=partner_id)
        if not is_platform_admin(request.user):
            queryset = queryset.filter(organization=request.user.organization)
        deleted, _ = queryset.delete()
        if not deleted:
            return Response({"detail": "Partner not found"}, status=404)
        return Response(status=204)
