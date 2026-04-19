import os
import tempfile
from io import StringIO
from pathlib import Path
from subprocess import CalledProcessError, CompletedProcess
from unittest.mock import patch

from django.core.management import call_command
from django.test import SimpleTestCase, override_settings


class RestoreDbDrillCommandTests(SimpleTestCase):
    def _fake_subprocess(self, args, **kwargs):
        command = args[0]
        if command == "openssl":
            out_idx = args.index("-out") + 1
            out_path = Path(args[out_idx])
            out_path.write_text(
                "CREATE TABLE demo (id INT);\nINSERT INTO demo VALUES (1);\n"
            )
            return CompletedProcess(args=args, returncode=0)
        if command == "mysql":
            return CompletedProcess(args=args, returncode=0)
        raise CalledProcessError(returncode=1, cmd=args)

    def test_restore_db_drill_dry_run_passes_validation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir)
            (backup_dir / "harborops_20260101_010101.sql.enc").write_bytes(b"encrypted")

            out = StringIO()
            with (
                override_settings(BACKUP_DIR=str(backup_dir)),
                patch.dict(
                    os.environ,
                    {"BACKUP_PASSPHRASE": "strong-passphrase-123"},
                    clear=False,
                ),
                patch(
                    "subprocess.run", side_effect=self._fake_subprocess
                ) as mocked_run,
            ):
                call_command("restore_db_drill", stdout=out)

            output = out.getvalue()
            self.assertIn("Decryption and SQL validation passed", output)
            self.assertIn("Dry-run only", output)
            self.assertEqual(mocked_run.call_count, 1)

    def test_restore_db_drill_execute_mode_runs_create_import_drop(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir)
            (backup_dir / "harborops_20260101_010101.sql.enc").write_bytes(b"encrypted")

            out = StringIO()
            with (
                override_settings(BACKUP_DIR=str(backup_dir)),
                patch.dict(
                    os.environ,
                    {
                        "BACKUP_PASSPHRASE": "strong-passphrase-123",
                        "DB_HOST": "db",
                        "DB_PORT": "3306",
                        "DB_ADMIN_USER": "root",
                        "DB_ADMIN_PASSWORD": "root-password-123",
                    },
                    clear=False,
                ),
                patch(
                    "subprocess.run", side_effect=self._fake_subprocess
                ) as mocked_run,
            ):
                call_command("restore_db_drill", "--execute", stdout=out)

            output = out.getvalue()
            self.assertIn("Restore drill execute mode completed", output)

            mysql_commands = [
                call.args[0]
                for call in mocked_run.call_args_list
                if call.args and call.args[0] and call.args[0][0] == "mysql"
            ]
            self.assertGreaterEqual(len(mysql_commands), 3)
            self.assertTrue(
                any(
                    "CREATE DATABASE IF NOT EXISTS" in " ".join(cmd)
                    for cmd in mysql_commands
                )
            )
            self.assertTrue(
                any(
                    "DROP DATABASE IF EXISTS" in " ".join(cmd) for cmd in mysql_commands
                )
            )
