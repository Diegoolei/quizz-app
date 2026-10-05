"""Typed domain errors for attempt services (API maps these to HTTP envelopes)."""

from __future__ import annotations

from typing import Any


class AttemptError(Exception):
    """Base attempt domain error."""

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


class AttemptNotFound(AttemptError):
    """Unknown attempt_key — HTTP 404 ``attempt_not_found``."""

    code = "attempt_not_found"

    def __init__(
        self,
        message: str = "Attempt not found.",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details=details)


class IncompleteAnswersError(AttemptError):
    """Missing question coverage — HTTP 422 ``incomplete_answers``."""

    code = "incomplete_answers"

    def __init__(
        self,
        message: str = "Answers must cover every question exactly once.",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details=details)


class InvalidAnswerError(AttemptError):
    """Bad question/option pairing, duplicates, or extras — HTTP 422 ``invalid_answer``."""

    code = "invalid_answer"

    def __init__(
        self,
        message: str = "One or more answers are invalid.",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details=details)


class AlreadyCompletedError(AttemptError):
    """Second submit on completed attempt — HTTP 409 ``attempt_already_completed``."""

    code = "attempt_already_completed"

    def __init__(
        self,
        message: str = "Attempt is already completed.",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details=details)
