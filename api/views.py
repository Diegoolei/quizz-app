"""Thin DRF views — validate input, call domain services, return JSON."""

from __future__ import annotations

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from attempts.services import (
    get_attempt,
    list_user_attempts,
    start_attempt,
    submit_answers,
    user_stats,
)
from quizzes.services import create_quiz, get_quiz_public, list_quizzes
from users.services import create_user, get_user
from users.services.exceptions import ValidationError as UserValidationError

RATE_LIMIT_429 = OpenApiResponse(description="Rate limit exceeded (rate_limit_exceeded)")


class UserListCreateView(APIView):
    @extend_schema(
        responses={201: OpenApiResponse(description="Created"), 429: RATE_LIMIT_429}
    )
    def post(self, request: Request) -> Response:
        user = create_user(name=request.data.get("name"), email=request.data.get("email"))
        return Response(
            {"id": user.id, "name": user.name, "email": user.email},
            status=status.HTTP_201_CREATED,
        )


class UserDetailView(APIView):
    @extend_schema(
        responses={200: OpenApiResponse(description="OK"), 429: RATE_LIMIT_429}
    )
    def get(self, request: Request, id: int) -> Response:
        user = get_user(id)
        return Response({"id": user.id, "name": user.name, "email": user.email})


class QuizListCreateView(APIView):
    @extend_schema(
        responses={200: OpenApiResponse(description="List"), 429: RATE_LIMIT_429}
    )
    def get(self, request: Request) -> Response:
        return Response(list_quizzes())

    @extend_schema(
        responses={201: OpenApiResponse(description="Created"), 429: RATE_LIMIT_429}
    )
    def post(self, request: Request) -> Response:
        data = request.data
        quiz = create_quiz(
            title=data.get("title"),
            description=data.get("description", ""),
            questions=data.get("questions"),
        )
        return Response(quiz, status=status.HTTP_201_CREATED)


class QuizDetailView(APIView):
    @extend_schema(
        responses={200: OpenApiResponse(description="OK"), 429: RATE_LIMIT_429}
    )
    def get(self, request: Request, id: int) -> Response:
        return Response(get_quiz_public(id))


class QuizAttemptStartView(APIView):
    @extend_schema(
        responses={201: OpenApiResponse(description="Started"), 429: RATE_LIMIT_429}
    )
    def post(self, request: Request, quiz_id: int) -> Response:
        if "user_id" not in request.data:
            raise UserValidationError(
                "user_id is required.",
                details={"user_id": ["This field is required."]},
            )
        result = start_attempt(request.data.get("user_id"), quiz_id)
        return Response(result, status=status.HTTP_201_CREATED)


class AttemptAnswersView(APIView):
    @extend_schema(
        responses={200: OpenApiResponse(description="Saved"), 429: RATE_LIMIT_429}
    )
    def post(self, request: Request, attempt_key) -> Response:
        answers = request.data.get("answers")
        if answers is None:
            raise UserValidationError(
                "answers is required.",
                details={"answers": ["This field is required."]},
            )
        result = submit_answers(attempt_key, answers)
        return Response(result, status=status.HTTP_200_OK)


class AttemptDetailView(APIView):
    @extend_schema(
        responses={200: OpenApiResponse(description="OK"), 429: RATE_LIMIT_429}
    )
    def get(self, request: Request, attempt_key) -> Response:
        return Response(get_attempt(attempt_key))


class UserAttemptsListView(APIView):
    @extend_schema(
        responses={200: OpenApiResponse(description="OK"), 429: RATE_LIMIT_429}
    )
    def get(self, request: Request, user_id: int) -> Response:
        return Response(list_user_attempts(user_id))


class UserStatsView(APIView):
    @extend_schema(
        responses={200: OpenApiResponse(description="OK"), 429: RATE_LIMIT_429}
    )
    def get(self, request: Request, user_id: int) -> Response:
        return Response(user_stats(user_id))
