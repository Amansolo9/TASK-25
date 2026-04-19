import json
from datetime import timedelta

from django.http import JsonResponse
from django.utils import timezone

from core.models import IdempotencyRecord


class ResponseSecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "DENY"
        response["Referrer-Policy"] = "same-origin"
        response["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self' http://localhost:8000 http://localhost:4173",
        )
        return response


class IdempotencyMiddleware:
    mutable_methods = {"POST", "PUT", "PATCH", "DELETE"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method not in self.mutable_methods:
            return self.get_response(request)

        key = request.headers.get("Idempotency-Key", "").strip()
        if not key:
            return self.get_response(request)

        user = (
            request.user
            if getattr(request, "user", None) and request.user.is_authenticated
            else None
        )
        existing = IdempotencyRecord.objects.filter(
            user=user,
            method=request.method,
            path=request.path,
            key=key,
        ).first()
        if existing:
            return JsonResponse(existing.response_body, status=existing.status_code)

        response = self.get_response(request)

        if response.status_code >= 500:
            return response

        body = {}
        try:
            payload = (
                response.content.decode("utf-8") if hasattr(response, "content") else ""
            )
            body = json.loads(payload) if payload else {}
        except Exception:
            body = {"detail": "non-json response"}

        IdempotencyRecord.objects.create(
            user=user,
            method=request.method,
            path=request.path,
            key=key,
            status_code=response.status_code,
            response_body=body,
        )
        IdempotencyRecord.objects.filter(
            created_at__lt=timezone.now() - timedelta(hours=24)
        ).delete()

        return response
