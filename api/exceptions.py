"""DRF exception handler — error envelope per `.cursor/specs/06-api-conventions.md`."""

from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.exceptions import APIException, ParseError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

import attempts.services.exceptions as attempt_exc
import quizzes.services.exceptions as quiz_exc
import users.services.exceptions as user_exc

DOMAIN_STATUS: dict[type[BaseException], int] = {
    user_exc.ValidationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    user_exc.EmailTaken: status.HTTP_409_CONFLICT,
    user_exc.UserNotFound: status.HTTP_404_NOT_FOUND,
    quiz_exc.ValidationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    quiz_exc.QuizNotFound: status.HTTP_404_NOT_FOUND,
    attempt_exc.AttemptNotFound: status.HTTP_404_NOT_FOUND,
    attempt_exc.AlreadyCompletedError: status.HTTP_409_CONFLICT,
    attempt_exc.IncompleteAnswersError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    attempt_exc.InvalidAnswerError: status.HTTP_422_UNPROCESSABLE_ENTITY,
}


def error_body(
    *,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    for exc_type, http_status in DOMAIN_STATUS.items():
        if isinstance(exc, exc_type):
            return Response(
                error_body(
                    code=getattr(exc, "code", "domain_error"),
                    message=getattr(exc, "message", str(exc)) or str(exc),
                    details=getattr(exc, "details", {}) or {},
                ),
                status=http_status,
            )

    if isinstance(exc, ParseError):
        return Response(
            error_body(
                code="invalid_json",
                message="Malformed JSON body.",
                details={},
            ),
            status=status.HTTP_400_BAD_REQUEST,
        )

    response = drf_exception_handler(exc, context)
    if response is not None:
        if isinstance(exc, APIException):
            code = getattr(exc, "default_code", "error")
            if code == "invalid":
                code = "validation_error"
            data = response.data
            if isinstance(data, dict) and "detail" in data and len(data) == 1:
                details: dict[str, Any] = {}
                message = str(data["detail"])
            elif isinstance(data, dict):
                details = data
                message = "Validation failed."
                code = "validation_error"
            else:
                details = {}
                message = str(data)
            http_status = response.status_code
            if http_status == status.HTTP_400_BAD_REQUEST and code == "validation_error":
                http_status = status.HTTP_422_UNPROCESSABLE_ENTITY
            response.status_code = http_status
            response.data = error_body(code=code, message=message, details=details)
        return response

    return None
