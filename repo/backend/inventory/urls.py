from django.urls import path

from inventory.views import (
    CorrectiveActionAcknowledgeView,
    CorrectiveActionApproveView,
    CorrectiveActionCreateView,
    InventoryCountLineCreateView,
    InventoryPlanDetailView,
    InventoryPlanListCreateView,
    InventoryTaskDetailView,
    InventoryTaskListCreateView,
    VarianceCloseView,
)

urlpatterns = [
    path(
        "plans/",
        InventoryPlanListCreateView.as_view(),
        name="inventory-plan-list-create",
    ),
    path(
        "plans/<int:plan_id>/",
        InventoryPlanDetailView.as_view(),
        name="inventory-plan-detail",
    ),
    path(
        "tasks/",
        InventoryTaskListCreateView.as_view(),
        name="inventory-task-list-create",
    ),
    path(
        "tasks/<int:task_id>/",
        InventoryTaskDetailView.as_view(),
        name="inventory-task-detail",
    ),
    path(
        "lines/", InventoryCountLineCreateView.as_view(), name="inventory-line-create"
    ),
    path(
        "lines/<int:line_id>/corrective-action/",
        CorrectiveActionCreateView.as_view(),
        name="corrective-action-create",
    ),
    path(
        "lines/<int:line_id>/approve-action/",
        CorrectiveActionApproveView.as_view(),
        name="corrective-action-approve",
    ),
    path(
        "lines/<int:line_id>/acknowledge-action/",
        CorrectiveActionAcknowledgeView.as_view(),
        name="corrective-action-acknowledge",
    ),
    path(
        "lines/<int:line_id>/close/", VarianceCloseView.as_view(), name="variance-close"
    ),
]
