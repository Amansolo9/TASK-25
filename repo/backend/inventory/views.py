from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from access.services import is_platform_admin, user_has_permission
from audit.services import record_audit_event
from inventory.models import (
    CorrectiveAction,
    InventoryCountLine,
    InventoryPlan,
    InventoryTask,
)
from inventory.serializers import (
    CorrectiveActionSerializer,
    InventoryCountLineSerializer,
    InventoryPlanSerializer,
    InventoryTaskSerializer,
)
from inventory.services import close_variance_line, update_line_variance
from organizations.models import Organization


class InventoryPlanListCreateView(APIView):
    def get(self, request):
        if not user_has_permission(request.user, "inventory.read"):
            return Response(
                {"detail": "Missing permission: inventory.read"}, status=403
            )
        queryset = InventoryPlan.objects.all()
        if is_platform_admin(request.user):
            org_id = request.GET.get("organization_id")
            if org_id:
                queryset = queryset.filter(organization_id=org_id)
        else:
            queryset = queryset.filter(organization=request.user.organization)
        queryset = queryset.order_by("-created_at")
        return Response(InventoryPlanSerializer(queryset, many=True).data)

    def post(self, request):
        if not user_has_permission(request.user, "inventory.write"):
            return Response(
                {"detail": "Missing permission: inventory.write"}, status=403
            )

        serializer = InventoryPlanSerializer(data=request.data)
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
        obj = serializer.save(organization=organization, created_by=request.user)
        record_audit_event(
            event_type="inventory.plan.created",
            request=request,
            actor=request.user,
            organization=request.user.organization,
            resource_type="inventory_plan",
            resource_id=str(obj.id),
        )
        return Response(
            InventoryPlanSerializer(obj).data, status=status.HTTP_201_CREATED
        )


class InventoryPlanDetailView(APIView):
    def patch(self, request, plan_id):
        if not user_has_permission(request.user, "inventory.write"):
            return Response(
                {"detail": "Missing permission: inventory.write"}, status=403
            )
        plan = InventoryPlan.objects.filter(id=plan_id).first()
        if not plan:
            return Response({"detail": "Plan not found"}, status=404)
        if (
            not is_platform_admin(request.user)
            and plan.organization_id != request.user.organization_id
        ):
            return Response({"detail": "Plan out of organization scope."}, status=404)
        serializer = InventoryPlanSerializer(plan, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, plan_id):
        if not user_has_permission(request.user, "inventory.write"):
            return Response(
                {"detail": "Missing permission: inventory.write"}, status=403
            )
        queryset = InventoryPlan.objects.filter(id=plan_id)
        if not is_platform_admin(request.user):
            queryset = queryset.filter(organization=request.user.organization)
        deleted, _ = queryset.delete()
        if not deleted:
            return Response({"detail": "Plan not found"}, status=404)
        return Response(status=204)


class InventoryTaskListCreateView(APIView):
    def get(self, request):
        if not user_has_permission(request.user, "inventory.read"):
            return Response(
                {"detail": "Missing permission: inventory.read"}, status=403
            )
        queryset = InventoryTask.objects.all()
        if is_platform_admin(request.user):
            org_id = request.GET.get("organization_id")
            if org_id:
                queryset = queryset.filter(plan__organization_id=org_id)
        else:
            queryset = queryset.filter(plan__organization=request.user.organization)
        return Response(InventoryTaskSerializer(queryset, many=True).data)

    def post(self, request):
        if not user_has_permission(request.user, "inventory.write"):
            return Response(
                {"detail": "Missing permission: inventory.write"}, status=403
            )

        serializer = InventoryTaskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = serializer.validated_data["plan"]
        if (
            not is_platform_admin(request.user)
            and plan.organization_id != request.user.organization_id
        ):
            return Response({"detail": "Plan out of organization scope."}, status=400)
        obj = serializer.save()
        return Response(
            InventoryTaskSerializer(obj).data, status=status.HTTP_201_CREATED
        )


class InventoryTaskDetailView(APIView):
    def patch(self, request, task_id):
        if not user_has_permission(request.user, "inventory.write"):
            return Response(
                {"detail": "Missing permission: inventory.write"}, status=403
            )
        task = InventoryTask.objects.select_related("plan").filter(id=task_id).first()
        if not task:
            return Response({"detail": "Task not found"}, status=404)
        if (
            not is_platform_admin(request.user)
            and task.plan.organization_id != request.user.organization_id
        ):
            return Response({"detail": "Task out of organization scope."}, status=404)
        serializer = InventoryTaskSerializer(task, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, task_id):
        if not user_has_permission(request.user, "inventory.write"):
            return Response(
                {"detail": "Missing permission: inventory.write"}, status=403
            )
        queryset = InventoryTask.objects.filter(id=task_id)
        if not is_platform_admin(request.user):
            queryset = queryset.filter(plan__organization=request.user.organization)
        deleted, _ = queryset.delete()
        if not deleted:
            return Response({"detail": "Task not found"}, status=404)
        return Response(status=204)


class InventoryCountLineCreateView(APIView):
    def get(self, request):
        if not user_has_permission(request.user, "inventory.read"):
            return Response(
                {"detail": "Missing permission: inventory.read"}, status=403
            )
        queryset = InventoryCountLine.objects.all()
        if is_platform_admin(request.user):
            org_id = request.GET.get("organization_id")
            if org_id:
                queryset = queryset.filter(task__plan__organization_id=org_id)
        else:
            queryset = queryset.filter(
                task__plan__organization=request.user.organization
            )
        queryset = queryset.order_by("-id")
        return Response(InventoryCountLineSerializer(queryset, many=True).data)

    def post(self, request):
        if not user_has_permission(request.user, "inventory.write"):
            return Response(
                {"detail": "Missing permission: inventory.write"}, status=403
            )

        serializer = InventoryCountLineSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = serializer.validated_data["task"]
        if (
            not is_platform_admin(request.user)
            and task.plan.organization_id != request.user.organization_id
        ):
            return Response({"detail": "Task out of organization scope."}, status=400)

        line = serializer.save()
        update_line_variance(line)
        if line.requires_review:
            task.status = "review"
            task.save(update_fields=["status"])

        record_audit_event(
            event_type="inventory.line.counted",
            request=request,
            actor=request.user,
            organization=request.user.organization,
            resource_type="inventory_line",
            resource_id=str(line.id),
            metadata={
                "requires_review": line.requires_review,
                "variance_quantity": str(line.variance_quantity),
            },
        )
        return Response(
            InventoryCountLineSerializer(line).data, status=status.HTTP_201_CREATED
        )


class CorrectiveActionCreateView(APIView):
    def post(self, request, line_id):
        if not user_has_permission(request.user, "inventory.write"):
            return Response(
                {"detail": "Missing permission: inventory.write"}, status=403
            )

        line = get_object_or_404(
            InventoryCountLine,
            id=line_id,
            **(
                {"task__plan__organization": request.user.organization}
                if not is_platform_admin(request.user)
                else {}
            ),
        )
        payload = dict(request.data)
        payload["line"] = line.id
        serializer = CorrectiveActionSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        action = serializer.save()
        return Response(
            CorrectiveActionSerializer(action).data, status=status.HTTP_201_CREATED
        )


class CorrectiveActionApproveView(APIView):
    def post(self, request, line_id):
        if not user_has_permission(request.user, "inventory.write"):
            return Response(
                {"detail": "Missing permission: inventory.write"}, status=403
            )

        action = get_object_or_404(
            CorrectiveAction,
            line_id=line_id,
            **(
                {"line__task__plan__organization": request.user.organization}
                if not is_platform_admin(request.user)
                else {}
            ),
        )
        action.approved_by = request.user
        action.approved_at = timezone.now()
        action.accountability_acknowledged = bool(
            request.data.get("accountability_acknowledged")
        )
        action.save(
            update_fields=["approved_by", "approved_at", "accountability_acknowledged"]
        )
        return Response(CorrectiveActionSerializer(action).data)


class CorrectiveActionAcknowledgeView(APIView):
    def post(self, request, line_id):
        if not user_has_permission(request.user, "inventory.write"):
            return Response(
                {"detail": "Missing permission: inventory.write"}, status=403
            )

        action = get_object_or_404(
            CorrectiveAction,
            line_id=line_id,
            **(
                {"line__task__plan__organization": request.user.organization}
                if not is_platform_admin(request.user)
                else {}
            ),
        )
        action.accountability_acknowledged = True
        action.save(update_fields=["accountability_acknowledged"])
        return Response(CorrectiveActionSerializer(action).data)


class VarianceCloseView(APIView):
    def post(self, request, line_id):
        if not user_has_permission(request.user, "inventory.write"):
            return Response(
                {"detail": "Missing permission: inventory.write"}, status=403
            )

        line = get_object_or_404(
            InventoryCountLine,
            id=line_id,
            **(
                {"task__plan__organization": request.user.organization}
                if not is_platform_admin(request.user)
                else {}
            ),
        )
        try:
            closure = close_variance_line(
                line=line,
                reviewer=request.user,
                review_notes=request.data.get("review_notes", ""),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)

        record_audit_event(
            event_type="inventory.variance.closed",
            request=request,
            actor=request.user,
            organization=request.user.organization,
            resource_type="inventory_line",
            resource_id=str(line.id),
        )
        return Response({"detail": "Variance closed", "closure_id": closure.id})
