import random
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.utils import timezone

from accounts.models import CaptchaChallenge, PasswordHistory


def save_password_history(user):
    PasswordHistory.objects.create(user=user, password_hash=user.password)
    keep_count = getattr(settings, "PASSWORD_HISTORY_COUNT", 5)
    old_ids = list(
        user.password_history.order_by("-created_at").values_list("id", flat=True)[
            keep_count:
        ]
    )
    if old_ids:
        PasswordHistory.objects.filter(id__in=old_ids).delete()


def validate_not_recent_password(user, raw_password):
    keep_count = getattr(settings, "PASSWORD_HISTORY_COUNT", 5)
    for entry in user.password_history.order_by("-created_at")[:keep_count]:
        if check_password(raw_password, entry.password_hash):
            return False
    return True


def register_login_failure(user):
    user.failed_login_attempts += 1
    lock_after = getattr(settings, "LOCK_AFTER_FAILURES", 10)
    lock_minutes = getattr(settings, "ACCOUNT_LOCK_MINUTES", 15)

    if user.failed_login_attempts >= lock_after:
        user.locked_until = timezone.now() + timedelta(minutes=lock_minutes)
    user.save(update_fields=["failed_login_attempts", "locked_until"])


def reset_login_failures(user):
    if user.failed_login_attempts or user.locked_until:
        user.failed_login_attempts = 0
        user.locked_until = None
        user.save(update_fields=["failed_login_attempts", "locked_until"])


def requires_captcha(user):
    threshold = getattr(settings, "CAPTCHA_AFTER_FAILURES", 5)
    return user.failed_login_attempts >= threshold


def create_captcha_challenge(username):
    left = random.randint(1, 9)
    right = random.randint(1, 9)
    prompt = f"What is {left} + {right}?"
    answer = str(left + right)
    expires_at = timezone.now() + timedelta(minutes=10)
    challenge = CaptchaChallenge.objects.create(
        username=username,
        prompt=prompt,
        answer=answer,
        expires_at=expires_at,
    )
    return challenge


def verify_captcha(username, challenge_id, response_text):
    try:
        challenge = CaptchaChallenge.objects.get(
            challenge_id=challenge_id, username=username
        )
    except CaptchaChallenge.DoesNotExist:
        return False

    if challenge.is_expired:
        return False
    return challenge.answer.strip() == (response_text or "").strip()
