import re

from django.core.exceptions import ValidationError


class LetterNumberPasswordValidator:
    def validate(self, password, user=None):
        has_letter = bool(re.search(r"[A-Za-z]", password))
        has_number = bool(re.search(r"\d", password))
        if not has_letter or not has_number:
            raise ValidationError(
                "Password must contain at least one letter and one number.",
                code="password_missing_letter_or_number",
            )

    def get_help_text(self):
        return "Your password must contain at least one letter and one number."
