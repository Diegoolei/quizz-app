"""HTTP routes — `.cursor/specs/http/*.md`."""

from django.urls import path

from api.schema import SpectacularJSONAPIView
from api.views import (
    AttemptAnswersView,
    AttemptDetailView,
    QuizAttemptStartView,
    QuizDetailView,
    QuizListCreateView,
    UserAttemptsListView,
    UserDetailView,
    UserListCreateView,
    UserStatsView,
)

urlpatterns = [
    path("schema/", SpectacularJSONAPIView.as_view(), name="openapi-schema"),
    path("users/", UserListCreateView.as_view(), name="user-list-create"),
    path("users/<int:id>/", UserDetailView.as_view(), name="user-detail"),
    path(
        "users/<int:user_id>/attempts/",
        UserAttemptsListView.as_view(),
        name="user-attempts",
    ),
    path("users/<int:user_id>/stats/", UserStatsView.as_view(), name="user-stats"),
    path("quizzes/", QuizListCreateView.as_view(), name="quiz-list-create"),
    path("quizzes/<int:id>/", QuizDetailView.as_view(), name="quiz-detail"),
    path(
        "quizzes/<int:quiz_id>/attempts/",
        QuizAttemptStartView.as_view(),
        name="quiz-attempt-start",
    ),
    path(
        "attempts/<uuid:attempt_key>/answers/",
        AttemptAnswersView.as_view(),
        name="attempt-answers",
    ),
    path(
        "attempts/<uuid:attempt_key>/",
        AttemptDetailView.as_view(),
        name="attempt-detail",
    ),
]
