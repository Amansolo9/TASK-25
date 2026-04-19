from django.urls import path

from security.views import (
    TravelerIdentifierRevealView,
    TravelerSensitiveFieldRevealView,
    UnmaskSessionCreateView,
)

urlpatterns = [
    path(
        "unmask-sessions/",
        UnmaskSessionCreateView.as_view(),
        name="unmask-session-create",
    ),
    path(
        "traveler-profiles/<int:profile_id>/reveal/",
        TravelerIdentifierRevealView.as_view(),
        name="traveler-identifier-reveal",
    ),
    path(
        "traveler-profiles/<int:profile_id>/reveal/<str:sensitive_field>/",
        TravelerSensitiveFieldRevealView.as_view(),
        name="traveler-sensitive-field-reveal",
    ),
]
