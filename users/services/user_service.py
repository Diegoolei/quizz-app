"""User create/get services — `.cursor/specs/http/users.md`, `01-data-model.md`."""

from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import IntegrityError

from users.models import User
from users.services.exceptions import EmailTaken, UserNotFound, ValidationError


def create_user(name: str, email: str) -> User:
    """Create a user with non-empty name and unique valid email.

    Raises:
        ValidationError: blank/missing name or invalid email.
        EmailTaken: email already registered.
    """
    cleaned_name = _require_non_blank_name(name)
    cleaned_email = _require_valid_email(email)

    if User.objects.filter(email=cleaned_email).exists():
        raise EmailTaken(details={"email": ["Email already registered."]})

    try:
        return User.objects.create(name=cleaned_name, email=cleaned_email)
    except IntegrityError as exc:
        raise EmailTaken(details={"email": ["Email already registered."]}) from exc


def get_user(id: int) -> User:
    """Fetch a user by primary key.

    Raises:
        UserNotFound: unknown id.
    """
    try:
        return User.objects.get(pk=id)
    except User.DoesNotExist as exc:
        raise UserNotFound(details={"id": id}) from exc


def _require_non_blank_name(name: str) -> str:
    if name is None or not isinstance(name, str):
        raise ValidationError(
            "Name is required.",
            details={"name": ["This field is required."]},
        )
    cleaned = name.strip()
    if not cleaned:
        raise ValidationError(
            "Name may not be blank.",
            details={"name": ["This field may not be blank."]},
        )
    return cleaned


def _require_valid_email(email: str) -> str:
    if email is None or not isinstance(email, str):
        raise ValidationError(
            "Email is required.",
            details={"email": ["This field is required."]},
        )
    cleaned = email.strip()
    if not cleaned:
        raise ValidationError(
            "Email may not be blank.",
            details={"email": ["This field may not be blank."]},
        )
    try:
        validate_email(cleaned)
    except DjangoValidationError as exc:
        raise ValidationError(
            "Enter a valid email address.",
            details={"email": list(exc.messages)},
        ) from exc
    return cleaned
