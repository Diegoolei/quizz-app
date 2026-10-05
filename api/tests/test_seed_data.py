"""D-SEED — seed ≥2 quizzes with ≥5 questions; idempotent (07-seed-data)."""

import pytest


@pytest.mark.django_db
def test_seed_quizzes_minimums_and_idempotent():
    """After seed: ≥2 quizzes, each ≥5 questions, exactly one correct option; re-run ok."""
    from quizzes.models import Option, Question, Quiz
    from quizzes.management.commands.seed_quizzes import Command

    Command().handle()
    Command().handle()

    quizzes = Quiz.objects.all()
    assert quizzes.count() >= 2
    for quiz in quizzes:
        questions = Question.objects.filter(quiz=quiz)
        assert questions.count() >= 5
        for question in questions:
            assert Option.objects.filter(question=question, is_correct=True).count() == 1
