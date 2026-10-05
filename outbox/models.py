"""Outbox persistence — `.cursor/specs/01-data-model.md` (app: outbox)."""

from __future__ import annotations

from django.db import models


class OutboxEvent(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        EXCEEDED_RETRIES = "exceeded_retries", "Exceeded retries"

    event_type = models.CharField(max_length=64)
    payload = models.JSONField(default=dict)
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    retries = models.PositiveIntegerField(default=0)
    uniqueness_key = models.CharField(max_length=128, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_error = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return f"{self.event_type} ({self.status})"
