import os
import subprocess
from datetime import timezone as dt_timezone
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


class Command(BaseCommand):
    help = "Create encrypted local MySQL dump and apply retention"

    @staticmethod
    def _validate_passphrase(value):
        candidate = (value or "").strip()
        if not candidate or candidate.lower() in {"change-me", "changeme", "default"}:
            raise CommandError(
                "Refusing backup with insecure BACKUP_PASSPHRASE. Set a non-default value."
            )
        if len(candidate) < 12:
            raise CommandError("BACKUP_PASSPHRASE must be at least 12 characters.")
        return candidate

    def handle(self, *args, **options):
        backup_dir = Path(settings.BACKUP_DIR)
        backup_dir.mkdir(parents=True, exist_ok=True)

        key = self._validate_passphrase(os.getenv("BACKUP_PASSPHRASE"))

        stamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        dump_path = backup_dir / f"harborops_{stamp}.sql"
        enc_path = backup_dir / f"harborops_{stamp}.sql.enc"

        env = os.environ.copy()
        env["MYSQL_PWD"] = os.getenv("DB_PASSWORD", "")

        cmd = [
            "mysqldump",
            "-h",
            os.getenv("DB_HOST", "db"),
            "-P",
            os.getenv("DB_PORT", "3306"),
            "-u",
            os.getenv("DB_USER", "harborops"),
            "--no-tablespaces",
            os.getenv("DB_NAME", "harborops"),
        ]
        with dump_path.open("wb") as fh:
            subprocess.run(cmd, env=env, check=True, stdout=fh)
        subprocess.run(
            [
                "openssl",
                "enc",
                "-aes-256-cbc",
                "-salt",
                "-pbkdf2",
                "-in",
                str(dump_path),
                "-out",
                str(enc_path),
                "-k",
                key,
            ],
            check=True,
        )
        dump_path.unlink(missing_ok=True)

        cutoff = timezone.now() - timedelta(days=settings.BACKUP_RETENTION_DAYS)
        deleted = 0
        for file in backup_dir.glob("harborops_*.sql.enc"):
            if (
                timezone.datetime.fromtimestamp(
                    file.stat().st_mtime, tz=dt_timezone.utc
                )
                < cutoff
            ):
                file.unlink(missing_ok=True)
                deleted += 1

        self.stdout.write(
            self.style.SUCCESS(f"Backup created: {enc_path.name}; deleted {deleted}")
        )
