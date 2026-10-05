"""Quiz aggregate — `.cursor/specs/01-data-model.md` (app: quizzes)."""

from __future__ import annotations

from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models import Q


class Quiz(models.Model):
    title = models.CharField(max_length=255, validators=[MinLengthValidator(1)])
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        verbose_name_plural = "quizzes"

    def __str__(self) -> str:
        return self.title


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField(validators=[MinLengthValidator(1)])
    explanation = models.TextField(validators=[MinLengthValidator(1)])
    position = models.PositiveIntegerField()

    class Meta:
        ordering = ["position", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["quiz", "position"],
                name="uniq_question_position_per_quiz",
            ),
        ]

    def __str__(self) -> str:
        return f"Q{self.position}: {self.text[:40]}"


class Option(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="options"
    )
    text = models.CharField(max_length=512, validators=[MinLengthValidator(1)])
    is_correct = models.BooleanField(default=False)
    position = models.PositiveIntegerField()

    class Meta:
        ordering = ["position", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["question", "position"],
                name="uniq_option_position_per_question",
            ),
            models.UniqueConstraint(
                fields=["question"],
                condition=Q(is_correct=True),
                name="uniq_one_correct_option_per_question",
            ),
        ]

    def __str__(self) -> str:
        return self.text[:40]
