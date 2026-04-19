from django.urls import path

from jobs.views import (
    AttachmentDedupeCheckView,
    JobCompleteView,
    JobCheckpointUpsertView,
    JobClaimView,
    JobFailView,
    JobFailuresView,
    JobHeartbeatView,
    JobListCreateView,
    JobRowErrorListView,
    JobRowErrorResolveView,
    JobRetryView,
)

urlpatterns = [
    path("", JobListCreateView.as_view(), name="job-list-create"),
    path("<int:job_id>/retry/", JobRetryView.as_view(), name="job-retry"),
    path(
        "<int:job_id>/checkpoints/",
        JobCheckpointUpsertView.as_view(),
        name="job-checkpoint-upsert",
    ),
    path("<int:job_id>/failures/", JobFailuresView.as_view(), name="job-failures"),
    path(
        "<int:job_id>/row-errors/", JobRowErrorListView.as_view(), name="job-row-errors"
    ),
    path(
        "row-errors/<int:error_id>/resolve/",
        JobRowErrorResolveView.as_view(),
        name="job-row-error-resolve",
    ),
    path(
        "attachments/dedupe-check/",
        AttachmentDedupeCheckView.as_view(),
        name="attachment-dedupe-check",
    ),
    path("worker/claim/", JobClaimView.as_view(), name="job-claim"),
    path(
        "worker/<int:job_id>/heartbeat/",
        JobHeartbeatView.as_view(),
        name="job-heartbeat",
    ),
    path(
        "worker/<int:job_id>/complete/", JobCompleteView.as_view(), name="job-complete"
    ),
    path("worker/<int:job_id>/fail/", JobFailView.as_view(), name="job-fail"),
]
