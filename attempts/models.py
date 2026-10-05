"""Attempt aggregate — `.cursor/specs/01-data-model.md` (app: attempts)."""

from __future__ import annotations

import uuid

from django.db import models


class Attempt(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"

    attempt_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="attempts"
    )
    quiz = models.ForeignKey(
        "quizzes.Quiz", on_delete=models.CASCADE, related_name="attempts"
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
        db_index=True,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    correct_count = models.PositiveIntegerField(null=True, blank=True)
    total_count = models.PositiveIntegerField(null=True, blank=True)
    score_percent = models.PositiveSmallIntegerField(null=True, blank=True)
    performance_message = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        ordering = ["-started_at", "-id"]

    def __str__(self) -> str:
        return f"Attempt {self.attempt_key} ({self.status})"


class AttemptAnswer(models.Model):
    attempt = models.ForeignKey(
        Attempt, on_delete=models.CASCADE, related_name="answers"
    )
    question = models.ForeignKey("quizzes.Question", on_delete=models.CASCADE)
    option = models.ForeignKey("quizzes.Option", on_delete=models.CASCADE)
    is_correct = models.BooleanField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "question"],
                name="uniq_answer_per_attempt_question",
            ),
        ]

    def __str__(self) -> str:
        return f"Answer attempt={self.attempt_id} q={self.question_id}"
