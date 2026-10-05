"""Typed domain errors for users services (API maps these to HTTP envelopes)."""

from __future__ import annotations

from typing import Any


class DomainError(Exception):
    """Base for users domain errors."""

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
    """Invalid name/email — HTTP 422 ``validation_error``."""

    code = "validation_error"


class EmailTaken(DomainError):
    """Email already registered — HTTP 409 ``email_taken``."""

    code = "email_taken"

    def __init__(
        self,
        message: str = "Email already registered.",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details=details)


class UserNotFound(DomainError):
    """Unknown user id — HTTP 404 ``user_not_found``."""

    code = "user_not_found"

    def __init__(
        self,
        message: str = "User not found.",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details=details)
