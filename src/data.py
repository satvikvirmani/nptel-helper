from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SUBJECT_FILE_MAP: dict[str, str] = {
    "Affective Computing": "affective_computing.json",
    "Artificial Intelligence for Management": "ai_for_management.json",
}


@dataclass(frozen=True)
class Subject:
    key: str
    label: str
    path: Path


def discover_subjects(project_root: Path) -> list[Subject]:
    """Return configured subjects from a static subject-to-file mapper."""
    subjects: list[Subject] = []
    data_dir = project_root / "data" / "subjects"

    for subject_label, filename in SUBJECT_FILE_MAP.items():
        path = data_dir / filename
        if not path.exists():
            continue
        subjects.append(Subject(key=subject_label, label=subject_label, path=path))

    return subjects


def load_questions(subject: Subject) -> list[dict[str, Any]]:
    """Load questions from a subject JSON file."""
    try:
        data = json.loads(subject.path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    questions: list[dict[str, Any]] = []

    if isinstance(data, dict):
        for heading, items in data.items():
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                question = dict(item)
                question.setdefault("heading", heading)
                questions.append(question)
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                questions.append(dict(item))

    return questions


def build_subject_catalog(project_root: Path) -> list[dict[str, Any]]:
    """Return frontend-ready subject and question data."""
    catalog: list[dict[str, Any]] = []

    for subject in discover_subjects(project_root):
        questions = load_questions(subject)
        normalized_questions: list[dict[str, Any]] = []

        for index, question in enumerate(questions):
            question_text = str(question.get("question", "")).strip() or "Question text is not available."
            choices = [
                choice.strip()
                for choice in question.get("choices", [])
                if isinstance(choice, str) and choice.strip()
            ]

            answers = question.get("answer", [])
            if isinstance(answers, str):
                answer_list = [answers.strip()] if answers.strip() else []
            elif isinstance(answers, list):
                answer_list = [
                    answer.strip()
                    for answer in answers
                    if isinstance(answer, str) and answer.strip()
                ]
            else:
                answer_list = []

            heading = question.get("heading")
            heading_text = heading.strip() if isinstance(heading, str) else ""

            fingerprint = "|".join([subject.key, heading_text, question_text, "||".join(choices)])
            question_id = hashlib.sha1(fingerprint.encode("utf-8")).hexdigest()[:16]

            normalized_questions.append(
                {
                    "id": question_id,
                    "heading": heading_text,
                    "question": question_text,
                    "choices": choices,
                    "answer": answer_list,
                    "index": index,
                }
            )

        catalog.append(
            {
                "key": subject.key,
                "label": subject.label,
                "questions": normalized_questions,
            }
        )

    return catalog
