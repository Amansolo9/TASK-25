import hashlib
import hmac
from datetime import timezone as dt_timezone
from datetime import timedelta

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone

from core.crypto import decrypt_text
from security.models import ApiClientKey, ReplayNonce


class RequestSigningMiddleware:
    """Enforce HMAC signing and replay controls on mutating API routes.

    - Session-authenticated browser mutations require per-session signing headers
      plus replay nonce/timestamp checks.
    - API-key machine mutations require API-key signature headers plus
      replay nonce/timestamp checks.
    - Allowlisted auth endpoints bypass signing.
    """

    mutating_methods = {"POST", "PUT", "PATCH", "DELETE"}

    @staticmethod
    def _reject(detail, code, status=401):
        return JsonResponse({"detail": detail, "code": code}, status=status)

    def __init__(self, get_response):
        self.get_response = get_response
        prefixes = getattr(settings, "REQUEST_SIGNING_PREFIXES", ("/api/",))
        self.signed_prefixes = tuple(prefixes)
        allowlist = getattr(
            settings,
            "REQUEST_SIGNING_ALLOWLIST_PATHS",
            (
                "/api/auth/login/",
                "/api/auth/register/",
                "/api/auth/captcha/challenge/",
            ),
        )
        self.allowlist_paths = tuple(allowlist)
        self.require_session_replay_headers = getattr(
            settings, "SESSION_REPLAY_REQUIRE_HEADERS", True
        )
        self.require_session_signature_headers = getattr(
            settings, "SESSION_SIGNING_REQUIRE_HEADERS", True
        )

    @staticmethod
    def _build_machine_signature_payload(request, timestamp, nonce):
        body = request.body.decode("utf-8") if request.body else ""
        return "\n".join([request.method, request.path, timestamp, nonce, body])

    @staticmethod
    def _build_session_signature_payload(request, timestamp, nonce):
        return "\n".join([request.method, request.path, timestamp, nonce])

    @staticmethod
    def _parse_timestamp_or_reject(timestamp):
        try:
            parsed = timezone.datetime.fromisoformat(timestamp)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=dt_timezone.utc)
            return parsed, None
        except ValueError:
            return None, RequestSigningMiddleware._reject(
                "Invalid timestamp format", "invalid_signature_timestamp"
            )

    @staticmethod
    def _purge_old_nonces():
        ReplayNonce.objects.filter(
            created_at__lt=timezone.now() - timedelta(minutes=10)
        ).delete()

    def _enforce_session_replay_controls(self, request):
        timestamp = request.headers.get("X-Request-Timestamp", "").strip()
        nonce = request.headers.get("X-Request-Nonce", "").strip()
        if (
            not self.require_session_replay_headers
            and not self.require_session_signature_headers
            and not timestamp
            and not nonce
        ):
            return None
        if not timestamp and not nonce:
            return self._reject(
                "Missing replay headers", "missing_session_replay_headers", status=400
            )
        if bool(timestamp) != bool(nonce):
            return self._reject(
                "Both X-Request-Timestamp and X-Request-Nonce are required for replay-protected session mutations",
                "missing_session_replay_headers",
                status=400,
            )

        parsed_time, error_response = self._parse_timestamp_or_reject(timestamp)
        if error_response is not None:
            return error_response
        if parsed_time is None:
            return self._reject(
                "Invalid timestamp format", "invalid_signature_timestamp"
            )
        request_time = parsed_time

        if abs((timezone.now() - request_time).total_seconds()) > 300:
            return self._reject(
                "Request timestamp expired", "session_request_timestamp_expired"
            )

        session_key = getattr(request.session, "session_key", None)
        replay_scope = f"session:{session_key or request.user.id}"
        if ReplayNonce.objects.filter(key_id=replay_scope, nonce=nonce).exists():
            return self._reject(
                "Replay nonce detected", "replay_nonce_detected", status=409
            )

        ReplayNonce.objects.create(key_id=replay_scope, nonce=nonce)
        self._purge_old_nonces()
        return None

    def _enforce_session_signature_controls(self, request):
        if not self.require_session_signature_headers:
            return None

        timestamp = request.headers.get("X-Request-Timestamp", "").strip()
        nonce = request.headers.get("X-Request-Nonce", "").strip()
        signature = request.headers.get("X-Session-Signature", "").strip()
        if not (timestamp and nonce and signature):
            return self._reject(
                "Missing session signing headers",
                "missing_session_signature_headers",
                status=400,
            )

        csrf_cookie_name = getattr(settings, "CSRF_COOKIE_NAME", "csrftoken")
        session_signing_secret = request.headers.get("X-CSRFToken", "").strip()
        if not session_signing_secret:
            session_signing_secret = request.COOKIES.get(csrf_cookie_name, "")
        if not session_signing_secret:
            return self._reject(
                "Session signing secret unavailable",
                "session_signing_secret_unavailable",
                status=401,
            )

        payload = self._build_session_signature_payload(request, timestamp, nonce)
        expected = hmac.new(
            session_signing_secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return self._reject(
                "Invalid session signature", "invalid_session_signature"
            )

        return None

    def __call__(self, request):
        if request.method not in self.mutating_methods:
            return self.get_response(request)
        if request.path.startswith(self.allowlist_paths):
            return self.get_response(request)
        if not request.path.startswith(self.signed_prefixes):
            return self.get_response(request)
        if getattr(request, "user", None) and request.user.is_authenticated:
            replay_error = self._enforce_session_replay_controls(request)
            if replay_error is not None:
                return replay_error
            signature_error = self._enforce_session_signature_controls(request)
            if signature_error is not None:
                return signature_error
            return self.get_response(request)

        key_id = request.headers.get("X-Key-Id", "")
        timestamp = request.headers.get("X-Sign-Timestamp", "")
        nonce = request.headers.get("X-Sign-Nonce", "")
        signature = request.headers.get("X-Signature", "")
        if not (key_id and timestamp and nonce and signature):
            return self._reject(
                "Missing signature headers", "missing_signature_headers"
            )

        request_time, error_response = self._parse_timestamp_or_reject(timestamp)
        if error_response is not None:
            return error_response
        if request_time is None:
            return self._reject(
                "Invalid timestamp format", "invalid_signature_timestamp"
            )

        if abs((timezone.now() - request_time).total_seconds()) > 300:
            return self._reject(
                "Signature timestamp expired", "signature_timestamp_expired"
            )

        try:
            key = ApiClientKey.objects.get(
                key_id=key_id, is_active=True, revoked_at__isnull=True
            )
        except ApiClientKey.DoesNotExist:
            return self._reject("Invalid key_id", "invalid_signature_key")

        if ReplayNonce.objects.filter(key_id=key_id, nonce=nonce).exists():
            return self._reject("Replay nonce detected", "replay_nonce_detected")

        payload = self._build_machine_signature_payload(request, timestamp, nonce)
        if not key.secret_encrypted:
            return self._reject(
                "Signing key material unavailable", "signing_key_material_unavailable"
            )

        secret = decrypt_text(key.secret_encrypted)
        expected = hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return self._reject("Invalid signature", "invalid_signature")

        ReplayNonce.objects.create(key_id=key_id, nonce=nonce)
        self._purge_old_nonces()

        request.signed_api_key = key
        request.signed_organization_id = key.organization_id
        return self.get_response(request)
