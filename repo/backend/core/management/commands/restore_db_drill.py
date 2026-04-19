import os
import subprocess
import tempfile
import uuid
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Run restore drill from latest encrypted backup"

    def add_arguments(self, parser):
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Actually import into a temporary database (requires DB create/drop privileges)",
        )
        parser.add_argument(
            "--admin-user",
            default=None,
            help="Database user with create/drop privileges for execute mode (defaults to DB_ADMIN_USER or DB_USER)",
        )
        parser.add_argument(
            "--admin-password",
            default=None,
            help="Password for --admin-user (defaults to DB_ADMIN_PASSWORD or DB_PASSWORD)",
        )

    def handle(self, *args, **options):
        backup_dir = Path(settings.BACKUP_DIR)
        if not backup_dir.exists():
            raise CommandError(f"Backup directory does not exist: {backup_dir}")
        backup_files = sorted(
            backup_dir.glob("harborops_*.sql.enc"), key=lambda p: p.stat().st_mtime
        )
        if not backup_files:
            raise CommandError("No encrypted backups found.")

        latest = backup_files[-1]
        passphrase = os.getenv("BACKUP_PASSPHRASE", "change-me")

        with tempfile.TemporaryDirectory() as temp_dir:
            sql_path = Path(temp_dir) / "restore_drill.sql"
            try:
                subprocess.run(
                    [
                        "openssl",
                        "enc",
                        "-d",
                        "-aes-256-cbc",
                        "-pbkdf2",
                        "-in",
                        str(latest),
                        "-out",
                        str(sql_path),
                        "-k",
                        passphrase,
                    ],
                    check=True,
                )
            except subprocess.CalledProcessError as exc:
                raise CommandError("Backup decryption failed.") from exc

            content = sql_path.read_text(encoding="utf-8", errors="ignore")
            if "CREATE TABLE" not in content and "INSERT INTO" not in content:
                raise CommandError(
                    "Decrypted backup does not look like a valid SQL dump."
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Decryption and SQL validation passed for {latest.name}"
                )
            )

            if not options["execute"]:
                self.stdout.write(
                    self.style.WARNING(
                        "Dry-run only. Use --execute to run full import drill."
                    )
                )
                return

            if passphrase == "change-me":
                raise CommandError(
                    "Refusing execute mode with default BACKUP_PASSPHRASE. Set a secure passphrase first."
                )

            temp_db = f"harborops_restore_drill_{uuid.uuid4().hex[:8]}"
            env = os.environ.copy()
            host = os.getenv("DB_HOST", "db")
            port = os.getenv("DB_PORT", "3306")
            user = (
                options.get("admin_user")
                or os.getenv("DB_ADMIN_USER")
                or os.getenv("DB_USER", "harborops")
            )
            password = (
                options.get("admin_password")
                or os.getenv("DB_ADMIN_PASSWORD")
                or os.getenv("DB_PASSWORD", "")
            )
            env["MYSQL_PWD"] = password

            db_created = False
            try:
                try:
                    subprocess.run(
                        [
                            "mysql",
                            "-h",
                            host,
                            "-P",
                            port,
                            "-u",
                            user,
                            "-e",
                            f"CREATE DATABASE IF NOT EXISTS {temp_db};",
                        ],
                        env=env,
                        check=True,
                    )
                    db_created = True

                    with sql_path.open("rb") as sql_file:
                        subprocess.run(
                            [
                                "mysql",
                                "-h",
                                host,
                                "-P",
                                port,
                                "-u",
                                user,
                                temp_db,
                            ],
                            stdin=sql_file,
                            env=env,
                            check=True,
                        )
                except subprocess.CalledProcessError as exc:
                    raise CommandError(
                        "Restore drill execute failed. Ensure DB credentials allow temporary database create/drop and import."
                    ) from exc
            finally:
                if db_created:
                    subprocess.run(
                        [
                            "mysql",
                            "-h",
                            host,
                            "-P",
                            port,
                            "-u",
                            user,
                            "-e",
                            f"DROP DATABASE IF EXISTS {temp_db};",
                        ],
                        env=env,
                        check=True,
                    )

            self.stdout.write(
                self.style.SUCCESS("Restore drill execute mode completed.")
            )
