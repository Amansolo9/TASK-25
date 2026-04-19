from django.contrib import admin

from jobs.models import (
    IngestAttachmentFingerprint,
    IngestRowError,
    Job,
    JobCheckpoint,
    JobDependency,
    JobFailure,
    JobLease,
)

admin.site.register(Job)
admin.site.register(JobDependency)
admin.site.register(JobCheckpoint)
admin.site.register(JobLease)
admin.site.register(JobFailure)
admin.site.register(IngestRowError)
admin.site.register(IngestAttachmentFingerprint)
