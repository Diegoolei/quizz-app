"""Idempotent seed of AI-development quizzes — `.cursor/specs/07-seed-data.md`."""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from quizzes.models import Option, Question, Quiz

SEED_QUIZZES: list[dict] = [
    {
        "title": "Intro to LLMs",
        "description": "Core concepts for large language models.",
        "questions": [
            {
                "text": "What is a token in LLM context?",
                "explanation": "Tokens are pieces of text the model processes.",
                "options": [
                    ("A billing/text unit models consume", True),
                    ("A GPU kernel", False),
                    ("A database row", False),
                ],
            },
            {
                "text": "What does temperature control?",
                "explanation": "Higher temperature increases randomness of sampling.",
                "options": [
                    ("Sampling randomness", True),
                    ("GPU clock speed", False),
                    ("Disk cache size", False),
                ],
            },
            {
                "text": "What is a context window?",
                "explanation": "The maximum tokens a model can consider at once.",
                "options": [
                    ("Max tokens the model can attend to", True),
                    ("Browser viewport size", False),
                    ("Training epoch length", False),
                ],
            },
            {
                "text": "What is fine-tuning?",
                "explanation": "Further training a pretrained model on task data.",
                "options": [
                    ("Further training on domain/task data", True),
                    ("Deleting model weights", False),
                    ("Compressing images", False),
                ],
            },
            {
                "text": "What is RAG?",
                "explanation": "Retrieval-Augmented Generation grounds answers in documents.",
                "options": [
                    ("Retrieval-Augmented Generation", True),
                    ("Random Access Graphics", False),
                    ("Recursive Array Growth", False),
                ],
            },
        ],
    },
    {
        "title": "Prompt Engineering Basics",
        "description": "Practical prompting patterns for AI apps.",
        "questions": [
            {
                "text": "What is few-shot prompting?",
                "explanation": "Providing examples in the prompt to guide format/behavior.",
                "options": [
                    ("Including examples in the prompt", True),
                    ("Training for a few epochs only", False),
                    ("Using fewer GPUs", False),
                ],
            },
            {
                "text": "Why specify output format?",
                "explanation": "Clear formats improve parseability and reliability.",
                "options": [
                    ("Improves structured, parseable answers", True),
                    ("Reduces electricity cost always", False),
                    ("Disables hallucinations forever", False),
                ],
            },
            {
                "text": "What is chain-of-thought prompting?",
                "explanation": "Asking the model to reason step by step before answering.",
                "options": [
                    ("Requesting step-by-step reasoning", True),
                    ("Chaining HTTP redirects", False),
                    ("Linking database foreign keys", False),
                ],
            },
            {
                "text": "What helps reduce prompt injection risk?",
                "explanation": "Treat user input as untrusted; separate instructions from data.",
                "options": [
                    ("Treat user content as untrusted data", True),
                    ("Always raise temperature", False),
                    ("Disable logging", False),
                ],
            },
            {
                "text": "What is a system prompt?",
                "explanation": "High-priority instructions that set role and constraints.",
                "options": [
                    ("High-priority role/constraint instructions", True),
                    ("A Linux init script", False),
                    ("A SQL migration", False),
                ],
            },
        ],
    },
]


class Command(BaseCommand):
    help = "Seed idempotent AI-development quizzes (≥2 quizzes, ≥5 questions each)."

    def handle(self, *args, **options) -> None:
        created = 0
        skipped = 0
        for seed in SEED_QUIZZES:
            if Quiz.objects.filter(title=seed["title"]).exists():
                skipped += 1
                continue
            with transaction.atomic():
                quiz = Quiz.objects.create(
                    title=seed["title"],
                    description=seed["description"],
                )
                for position, q in enumerate(seed["questions"], start=1):
                    question = Question.objects.create(
                        quiz=quiz,
                        text=q["text"],
                        explanation=q["explanation"],
                        position=position,
                    )
                    Option.objects.bulk_create(
                        [
                            Option(
                                question=question,
                                text=text,
                                is_correct=is_correct,
                                position=opt_pos,
                            )
                            for opt_pos, (text, is_correct) in enumerate(
                                q["options"], start=1
                            )
                        ]
                    )
            created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete: created={created}, skipped_existing={skipped}."
            )
        )
