from rest_framework import serializers

from jobs.models import (
    IngestAttachmentFingerprint,
    IngestRowError,
    Job,
    JobCheckpoint,
    JobDependency,
    JobFailure,
)


class JobSerializer(serializers.ModelSerializer):
    dependency_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), required=False, write_only=True
    )

    class Meta:
        model = Job
        fields = [
            "id",
            "job_type",
            "source_path",
            "payload_json",
            "status",
            "trigger_type",
            "priority",
            "dedupe_key",
            "attempt_count",
            "max_attempts",
            "next_run_at",
            "started_at",
            "finished_at",
            "created_at",
            "dependency_ids",
        ]
        read_only_fields = [
            "status",
            "attempt_count",
            "started_at",
            "finished_at",
            "created_at",
        ]


class JobCheckpointSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobCheckpoint
        fields = [
            "id",
            "job",
            "file_name",
            "row_offset",
            "attachment_index",
            "state_json",
            "updated_at",
        ]


class JobFailureSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobFailure
        fields = ["id", "attempt", "error_type", "error_message", "created_at"]


class IngestRowErrorSerializer(serializers.ModelSerializer):
    class Meta:
        model = IngestRowError
        fields = [
            "id",
            "job",
            "source_file",
            "row_number",
            "error_message",
            "raw_row_json",
            "resolved",
            "resolution_note",
            "resolved_by",
            "resolved_at",
            "created_at",
        ]


class IngestRowErrorResolveSerializer(serializers.Serializer):
    resolution_note = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )


class IngestAttachmentFingerprintSerializer(serializers.ModelSerializer):
    class Meta:
        model = IngestAttachmentFingerprint
        fields = [
            "id",
            "source_signature",
            "content_hash",
            "first_seen_job",
            "created_at",
        ]


class JobDependencySerializer(serializers.ModelSerializer):
    class Meta:
        model = JobDependency
        fields = ["id", "job", "depends_on"]
