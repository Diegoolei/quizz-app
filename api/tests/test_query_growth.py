"""QG-* — escalating N+1 detection per endpoint (catalog 08)."""

import pytest

from api.tests.helpers.factories import (
    all_correct_answers_payload,
    complete_attempt,
    make_attempt,
    make_quiz,
    make_user,
    quiz_create_payload,
)
from api.tests.helpers.query_growth import assert_selects_do_not_grow


@pytest.mark.django_db
def test_qg_quiz_list(api_client):
    """QG-QUIZ-LIST: quiz count 3 → 6; SELECT must not escalate."""
    from quizzes.models import Quiz

    def build_s():
        Quiz.objects.all().delete()
        for _ in range(3):
            make_quiz(question_count=2)

    def build_2s():
        Quiz.objects.all().delete()
        for _ in range(6):
            make_quiz(question_count=2)

    assert_selects_do_not_grow(
        call_endpoint=lambda: api_client.get("/api/quizzes/"),
        build_size_s=build_s,
        build_size_2s=build_2s,
    )


@pytest.mark.django_db
def test_qg_quiz_detail(api_client):
    """QG-QUIZ-DETAIL: questions 5 → 10."""
    state = {}

    def build_s():
        state["quiz"] = make_quiz(question_count=5)

    def build_2s():
        state["quiz"] = make_quiz(question_count=10)

    assert_selects_do_not_grow(
        call_endpoint=lambda: api_client.get(f"/api/quizzes/{state['quiz'].id}/"),
        build_size_s=build_s,
        build_size_2s=build_2s,
    )


@pytest.mark.django_db
def test_qg_quiz_create(api_client):
    """QG-QUIZ-CREATE: nested questions 5 → 10; SELECT growth only."""
    payloads = {"s": quiz_create_payload(5), "d": quiz_create_payload(10)}

    assert_selects_do_not_grow(
        call_endpoint=lambda: api_client.post(
            "/api/quizzes/", payloads["current"], format="json"
        ),
        build_size_s=lambda: payloads.__setitem__("current", payloads["s"]),
        build_size_2s=lambda: payloads.__setitem__("current", payloads["d"]),
    )


@pytest.mark.django_db
def test_qg_user_create(api_client):
    """QG-USER-CREATE: many pre-existing users; create SELECTs stay flat."""
    from users.models import User

    def build_s():
        User.objects.all().delete()

    def build_2s():
        User.objects.all().delete()
        for i in range(20):
            make_user(email=f"pre{i}@example.com")

    counter = {"n": 0}

    def call():
        counter["n"] += 1
        return api_client.post(
            "/api/users/",
            {"name": "N", "email": f"new{counter['n']}@example.com"},
            format="json",
        )

    assert_selects_do_not_grow(
        call_endpoint=call,
        build_size_s=build_s,
        build_size_2s=build_2s,
    )


@pytest.mark.django_db
def test_qg_user_get(api_client):
    """QG-USER-GET: unrelated quizzes/attempts grow; get-by-pk flat."""
    user = make_user()

    def build_s():
        make_quiz(question_count=2)

    def build_2s():
        for _ in range(10):
            q = make_quiz(question_count=2)
            make_attempt(user, q)

    assert_selects_do_not_grow(
        call_endpoint=lambda: api_client.get(f"/api/users/{user.id}/"),
        build_size_s=build_s,
        build_size_2s=build_2s,
    )


@pytest.mark.django_db
def test_qg_attempt_start(api_client):
    """QG-ATTEMPT-START: questions on quiz 5 → 10."""
    user = make_user()
    state = {}

    def build_s():
        state["quiz"] = make_quiz(question_count=5)

    def build_2s():
        state["quiz"] = make_quiz(question_count=10)

    assert_selects_do_not_grow(
        call_endpoint=lambda: api_client.post(
            f"/api/quizzes/{state['quiz'].id}/attempts/",
            {"user_id": user.id},
            format="json",
        ),
        build_size_s=build_s,
        build_size_2s=build_2s,
    )


@pytest.mark.django_db
def test_qg_attempt_submit(api_client):
    """QG-ATTEMPT-SUBMIT: answers 5 → 10; SELECT flat."""
    user = make_user()
    state = {}

    def build_s():
        quiz = make_quiz(question_count=5)
        state["attempt"] = make_attempt(user, quiz)
        state["payload"] = all_correct_answers_payload(quiz)

    def build_2s():
        quiz = make_quiz(question_count=10)
        state["attempt"] = make_attempt(user, quiz)
        state["payload"] = all_correct_answers_payload(quiz)

    assert_selects_do_not_grow(
        call_endpoint=lambda: api_client.post(
            f"/api/attempts/{state['attempt'].attempt_key}/answers/",
            state["payload"],
            format="json",
        ),
        build_size_s=build_s,
        build_size_2s=build_2s,
    )


@pytest.mark.django_db
def test_qg_attempt_get_in_progress(api_client):
    """QG-ATTEMPT-GET-IP: questions 5 → 10."""
    user = make_user()
    state = {}

    def build_s():
        quiz = make_quiz(question_count=5)
        state["attempt"] = make_attempt(user, quiz)

    def build_2s():
        quiz = make_quiz(question_count=10)
        state["attempt"] = make_attempt(user, quiz)

    assert_selects_do_not_grow(
        call_endpoint=lambda: api_client.get(
            f"/api/attempts/{state['attempt'].attempt_key}/"
        ),
        build_size_s=build_s,
        build_size_2s=build_2s,
    )


@pytest.mark.django_db
def test_qg_attempt_get_completed(api_client):
    """QG-ATTEMPT-GET-DONE: questions 5 → 10."""
    user = make_user()
    state = {}

    def build_s():
        quiz = make_quiz(question_count=5)
        attempt = make_attempt(user, quiz)
        complete_attempt(attempt)
        state["attempt"] = attempt

    def build_2s():
        quiz = make_quiz(question_count=10)
        attempt = make_attempt(user, quiz)
        complete_attempt(attempt)
        state["attempt"] = attempt

    assert_selects_do_not_grow(
        call_endpoint=lambda: api_client.get(
            f"/api/attempts/{state['attempt'].attempt_key}/"
        ),
        build_size_s=build_s,
        build_size_2s=build_2s,
    )


@pytest.mark.django_db
def test_qg_progress_list(api_client):
    """QG-PROGRESS-LIST: attempt count 5 → 10."""
    user = make_user()
    quiz = make_quiz(question_count=2)

    def build_s():
        from attempts.models import Attempt

        Attempt.objects.filter(user=user).delete()
        for _ in range(5):
            make_attempt(user, quiz)

    def build_2s():
        from attempts.models import Attempt

        Attempt.objects.filter(user=user).delete()
        for _ in range(10):
            make_attempt(user, quiz)

    assert_selects_do_not_grow(
        call_endpoint=lambda: api_client.get(f"/api/users/{user.id}/attempts/"),
        build_size_s=build_s,
        build_size_2s=build_2s,
    )


@pytest.mark.django_db
def test_qg_progress_stats(api_client):
    """QG-PROGRESS-STATS: 2 quizzes × 3 completed → 2 × 6 completed."""
    user = make_user()

    def build_s():
        from attempts.models import Attempt

        Attempt.objects.filter(user=user).delete()
        for _ in range(2):
            quiz = make_quiz(question_count=2)
            for _ in range(3):
                complete_attempt(make_attempt(user, quiz))

    def build_2s():
        from attempts.models import Attempt

        Attempt.objects.filter(user=user).delete()
        for _ in range(2):
            quiz = make_quiz(question_count=2)
            for _ in range(6):
                complete_attempt(make_attempt(user, quiz))

    assert_selects_do_not_grow(
        call_endpoint=lambda: api_client.get(f"/api/users/{user.id}/stats/"),
        build_size_s=build_s,
        build_size_2s=build_2s,
    )
