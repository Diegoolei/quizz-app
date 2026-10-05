"""User persistence — `.cursor/specs/01-data-model.md` (app: users)."""

from __future__ import annotations

from django.core.validators import MinLengthValidator
from django.db import models


class User(models.Model):
    """Minimal app user (no auth)."""

    name = models.CharField(max_length=255, validators=[MinLengthValidator(1)])
    email = models.EmailField(unique=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.name} <{self.email}>"
