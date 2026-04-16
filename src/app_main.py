from __future__ import annotations

import os
import random
from pathlib import Path

import streamlit as st

from src.data import Subject, discover_subjects, load_questions
from src.progress import clear_progress, load_progress, save_progress

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

try:
    from google import genai

    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROGRESS_KEY = "nptel_helper_progress_v1"


st.set_page_config(page_title="NPTEL Question Practice", layout="wide")


def run() -> None:
    st.title("NPTEL Question Practice")
    st.caption("Practice by subject, track your progress, and continue from where you left off.")

    _initialize_state()

    subjects: list[Subject] = st.session_state.subjects
    if not subjects:
        st.warning("No subject files were found. Add JSON files to data/subjects and reload.")
        return

    with st.sidebar:
        st.header("Session Controls")

        selected_label = st.selectbox(
            "Subject",
            options=[subject.label for subject in subjects],
            index=_subject_index(subjects, st.session_state.active_subject_key),
        )

        selected_subject = next(subject for subject in subjects if subject.label == selected_label)
        if selected_subject.key != st.session_state.active_subject_key:
            _switch_subject(selected_subject)
            st.rerun()

        if st.button("Shuffle Current Subject", use_container_width=True):
            random.shuffle(st.session_state.questions)
            st.session_state.user_answers = {}
            st.session_state.llm_explanation = {}
            _persist_current_subject_answers()
            st.rerun()

        if st.button("Save Progress", use_container_width=True):
            _persist_current_subject_answers()
            st.success("Progress saved to browser local storage.")

        if st.button("Reset All Progress", use_container_width=True):
            clear_progress(PROGRESS_KEY)
            st.session_state.progress_store = {}
            st.session_state.user_answers = {}
            st.session_state.llm_explanation = {}
            st.success("All saved progress has been reset.")
            st.rerun()

        st.divider()
        st.subheader("Statistics")
        total = len(st.session_state.questions)
        answered = len(st.session_state.user_answers)
        st.write(f"Questions in subject: {total}")
        st.write(f"Answered: {answered}")
        st.write(f"Remaining: {max(total - answered, 0)}")

    questions = st.session_state.questions
    if not questions:
        st.warning("No questions are available for this subject.")
        return

    api_key = os.environ.get("GEMINI_API_KEY", "")

    for idx, question in enumerate(questions):
        st.write("---")

        if "heading" in question:
            st.caption(f"Assessment: {question['heading']}")

        question_text = question.get("question", "Question text is not available.")
        st.markdown(f"**Question {idx + 1}: {question_text}**")

        choices = question.get("choices", [])
        correct_answers = question.get("answer", [])
        if isinstance(correct_answers, str):
            correct_answers = [correct_answers]

        is_multiple = len(correct_answers) > 1

        if choices:
            current_saved = st.session_state.user_answers.get(idx, [])
            if isinstance(current_saved, str):
                current_saved = [current_saved]

            current_selection: list[str] = []

            if is_multiple:
                st.caption("This question may have more than one correct option.")
                for choice_idx, choice in enumerate(choices):
                    if st.checkbox(
                        choice,
                        value=choice in current_saved,
                        key=f"chk_{idx}_{choice_idx}",
                    ):
                        current_selection.append(choice)
            else:
                default_index = None
                if current_saved and current_saved[0] in choices:
                    default_index = choices.index(current_saved[0])
                selected = st.radio(
                    "Select one option",
                    choices,
                    index=default_index,
                    key=f"radio_{idx}",
                    label_visibility="collapsed",
                )
                if selected:
                    current_selection.append(selected)

            col_submit, col_ai = st.columns([1, 2])

            with col_submit:
                if st.button("Submit Answer", key=f"submit_{idx}", type="primary"):
                    if not current_selection:
                        st.warning("Select at least one option before submitting.")
                    else:
                        st.session_state.user_answers[idx] = current_selection
                        _persist_current_subject_answers()
                        st.rerun()

            with col_ai:
                if st.button("Explain with AI", key=f"llm_{idx}"):
                    if not api_key:
                        st.error("Set GEMINI_API_KEY in your environment to use AI explanations.")
                    elif not GENAI_AVAILABLE:
                        st.error("Install google-genai to enable AI explanations.")
                    else:
                        with st.spinner("Generating explanation..."):
                            try:
                                client = genai.Client(api_key=api_key)
                                correct_text = " and ".join(correct_answers)
                                prompt = (
                                    "Explain why the following answer is correct for this exam question. "
                                    "Keep the explanation concise and concept-focused.\\n\\n"
                                    f"Question: {question_text}\\n"
                                    f"Correct Answer: {correct_text}"
                                )
                                response = client.models.generate_content(
                                    model="gemini-3.1-flash-lite-preview",
                                    contents=prompt,
                                )
                                st.session_state.llm_explanation[idx] = response.text
                            except Exception as exc:
                                st.error(f"AI explanation failed: {exc}")

        if idx in st.session_state.user_answers:
            user_answer = st.session_state.user_answers[idx]
            if set(user_answer) == set(correct_answers):
                st.success("Correct response.")
            else:
                st.error("Response is not correct.")

            st.info(f"Accepted answer: {' and '.join(correct_answers)}")

        if idx in st.session_state.llm_explanation:
            st.markdown("### AI Explanation")
            st.write(st.session_state.llm_explanation[idx])


def _initialize_state() -> None:
    if "subjects" not in st.session_state:
        st.session_state.subjects = discover_subjects(PROJECT_ROOT)

    if "progress_store" not in st.session_state:
        st.session_state.progress_store = load_progress(PROGRESS_KEY)

    if "active_subject_key" not in st.session_state:
        default_subject = st.session_state.subjects[0] if st.session_state.subjects else None
        st.session_state.active_subject_key = default_subject.key if default_subject else None

    if "questions" not in st.session_state:
        st.session_state.questions = []

    if "user_answers" not in st.session_state:
        st.session_state.user_answers = {}

    if "llm_explanation" not in st.session_state:
        st.session_state.llm_explanation = {}

    if st.session_state.active_subject_key and not st.session_state.questions:
        active_subject = next(
            subject
            for subject in st.session_state.subjects
            if subject.key == st.session_state.active_subject_key
        )
        _switch_subject(active_subject)


def _switch_subject(subject: Subject) -> None:
    st.session_state.active_subject_key = subject.key
    st.session_state.questions = load_questions(subject)
    st.session_state.llm_explanation = {}

    saved = st.session_state.progress_store.get(subject.key, {})
    answers = saved.get("answers", {}) if isinstance(saved, dict) else {}
    normalized: dict[int, list[str]] = {}

    for key, value in answers.items():
        try:
            q_idx = int(key)
        except (TypeError, ValueError):
            continue

        if isinstance(value, str):
            normalized[q_idx] = [value]
        elif isinstance(value, list):
            normalized[q_idx] = [item for item in value if isinstance(item, str)]

    st.session_state.user_answers = normalized


def _persist_current_subject_answers() -> None:
    subject_key = st.session_state.active_subject_key
    if not subject_key:
        return

    answers = {
        str(question_idx): answer_list
        for question_idx, answer_list in st.session_state.user_answers.items()
    }
    st.session_state.progress_store[subject_key] = {"answers": answers}
    save_progress(PROGRESS_KEY, st.session_state.progress_store)


def _subject_index(subjects: list[Subject], key: str | None) -> int:
    if not key:
        return 0

    for idx, subject in enumerate(subjects):
        if subject.key == key:
            return idx
    return 0
