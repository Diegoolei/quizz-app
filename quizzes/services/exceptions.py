"""Typed domain errors for quiz services (API maps these to HTTP envelopes)."""

from __future__ import annotations

from typing import Any


class DomainError(Exception):
    """Base for quizzes domain errors."""

    code: str = "domain_error"

    def __init__(
        self,
        message: str = "",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.details = details if details is not None else {}
        super().__init__(message)


class ValidationError(DomainError):
    """Invalid authoring payload — HTTP 422 ``validation_error``."""

    code = "validation_error"


class QuizNotFound(DomainError):
    """Unknown quiz id — HTTP 404 ``quiz_not_found``."""

    code = "quiz_not_found"

    def __init__(
        self,
        message: str = "Quiz not found.",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details=details)
