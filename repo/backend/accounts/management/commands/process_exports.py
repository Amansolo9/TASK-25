from django.core.management.base import BaseCommand

from accounts.export_services import process_pending_exports


class Command(BaseCommand):
    help = "Process pending self-service data export requests"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50)

    def handle(self, *args, **options):
        process_pending_exports(limit=options["limit"])
        self.stdout.write(self.style.SUCCESS("Pending exports processed."))
