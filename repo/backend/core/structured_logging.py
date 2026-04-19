import json
import logging
from datetime import datetime, timezone


APP_LOG_CATEGORIES = {
    "audit",
    "auth",
    "trips",
    "jobs",
    "inventory",
    "warehouse",
    "verification",
    "security",
    "monitoring",
    "system",
}

SENSITIVE_LOG_KEY_TOKENS = {
    "password",
    "secret",
    "token",
    "signature",
    "authorization",
    "credential",
    "api_key",
}
REDACTED_VALUE = "[REDACTED]"


def _is_sensitive_key(key):
    normalized = str(key).strip().lower().replace("-", "_")
    return any(token in normalized for token in SENSITIVE_LOG_KEY_TOKENS)


def sanitize_for_logging(value, key_hint=None):
    if key_hint is not None and _is_sensitive_key(key_hint):
        return REDACTED_VALUE

    if isinstance(value, dict):
        return {k: sanitize_for_logging(v, key_hint=k) for k, v in value.items()}

    if isinstance(value, list):
        return [sanitize_for_logging(item) for item in value]

    if isinstance(value, tuple):
        return tuple(sanitize_for_logging(item) for item in value)

    return value


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        event = getattr(record, "event", None)
        if isinstance(event, dict):
            payload["event"] = sanitize_for_logging(event)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def get_app_logger(category):
    if category not in APP_LOG_CATEGORIES:
        category = "system"
    return logging.getLogger(f"harborops.{category}")


def log_app_event(category, action, level="info", **fields):
    logger = get_app_logger(category)
    fn = getattr(logger, level, logger.info)
    fn(action, extra={"event": {"category": category, "action": action, **fields}})
