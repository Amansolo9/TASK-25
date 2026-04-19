from django.urls import path

from accounts.views import (
    AccountDeletionRequestView,
    CsrfTokenView,
    CaptchaChallengeView,
    ChangePasswordView,
    ComparisonItemDeleteView,
    ComparisonItemListCreateView,
    ExportRequestCreateView,
    ExportRequestDownloadView,
    ExportRequestListView,
    FavoriteItemDeleteView,
    FavoriteItemListCreateView,
    LocalAlertAcknowledgeView,
    LocalAlertListView,
    LoginView,
    LogoutView,
    MeView,
    PreferenceView,
    RegisterView,
    TravelerProfileDetailView,
    TravelerProfileListCreateView,
    VerificationDocumentOpenView,
    VerificationDocumentUploadView,
    VerificationRequestListCreateView,
    VerificationReviewCreateView,
)

urlpatterns = [
    path("csrf/", CsrfTokenView.as_view(), name="csrf"),
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path(
        "captcha/challenge/", CaptchaChallengeView.as_view(), name="captcha-challenge"
    ),
    path("preferences/", PreferenceView.as_view(), name="preferences"),
    path(
        "traveler-profiles/",
        TravelerProfileListCreateView.as_view(),
        name="traveler-profiles",
    ),
    path(
        "traveler-profiles/<int:profile_id>/",
        TravelerProfileDetailView.as_view(),
        name="traveler-profile-detail",
    ),
    path("alerts/", LocalAlertListView.as_view(), name="local-alerts"),
    path(
        "alerts/<int:alert_id>/acknowledge/",
        LocalAlertAcknowledgeView.as_view(),
        name="local-alert-ack",
    ),
    path("favorites/", FavoriteItemListCreateView.as_view(), name="favorites"),
    path(
        "favorites/<int:favorite_id>/",
        FavoriteItemDeleteView.as_view(),
        name="favorites-delete",
    ),
    path("comparisons/", ComparisonItemListCreateView.as_view(), name="comparisons"),
    path(
        "comparisons/<int:comparison_id>/",
        ComparisonItemDeleteView.as_view(),
        name="comparisons-delete",
    ),
    path("exports/", ExportRequestListView.as_view(), name="exports"),
    path("exports/request/", ExportRequestCreateView.as_view(), name="export-request"),
    path(
        "exports/<int:export_id>/download/",
        ExportRequestDownloadView.as_view(),
        name="export-download",
    ),
    path(
        "deletion-request/",
        AccountDeletionRequestView.as_view(),
        name="deletion-request",
    ),
    path(
        "verification-requests/",
        VerificationRequestListCreateView.as_view(),
        name="verification-requests",
    ),
    path(
        "verification-requests/<int:verification_id>/review/",
        VerificationReviewCreateView.as_view(),
        name="verification-review",
    ),
    path(
        "verification-requests/<int:verification_id>/documents/upload/",
        VerificationDocumentUploadView.as_view(),
        name="verification-document-upload",
    ),
    path(
        "verification-documents/<int:document_id>/open/",
        VerificationDocumentOpenView.as_view(),
        name="verification-document-open",
    ),
]
