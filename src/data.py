from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SUBJECT_FILE_MAP: dict[str, str] = {
    "Affective Computing": "affective_computing.json",
    "Artificial Intelligence for Management": "ai_for_management.json",
    "Information Technology": "info_tech.json",
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
