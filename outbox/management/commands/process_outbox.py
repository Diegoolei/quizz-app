"""Management command: drain eligible outbox events (cron / compose sidecar)."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from outbox.services.outbox_service import DEFAULT_BATCH_SIZE, process_outbox


class Command(BaseCommand):
    help = (
        "Process a batch of pending/failed outbox email events. "
        "Uses the process-global MockEmailSender (prefer a long-running process "
        "so the odd/even fail cadence survives across ticks)."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--limit",
            type=int,
            default=DEFAULT_BATCH_SIZE,
            help=f"Max events per tick (default {DEFAULT_BATCH_SIZE}).",
        )

    def handle(self, *args, **options) -> None:
        limit = options["limit"]
        count = process_outbox(limit=limit)
        self.stdout.write(self.style.SUCCESS(f"Processed {count} outbox event(s)."))
