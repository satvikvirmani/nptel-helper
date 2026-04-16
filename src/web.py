from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from flask import Flask, Response, jsonify, request

from src.data import build_subject_catalog

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROGRESS_KEY = "nptel_helper_progress_v2"
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional local dev dependency
    load_dotenv = None

try:
    from google import genai

    GENAI_AVAILABLE = True
except ImportError:  # pragma: no cover - optional deployment dependency
    genai = None
    GENAI_AVAILABLE = False


def _load_local_environment() -> None:
    if load_dotenv is None:
        return

    for candidate in (PROJECT_ROOT / ".env.local", PROJECT_ROOT / ".env"):
        if candidate.exists():
            load_dotenv(candidate)


_load_local_environment()

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False


@lru_cache(maxsize=1)
def get_catalog() -> list[dict[str, Any]]:
    return build_subject_catalog(PROJECT_ROOT)


def _get_subject(subject_key: str) -> dict[str, Any] | None:
    return next((subject for subject in get_catalog() if subject["key"] == subject_key), None)


def _build_index_payload() -> dict[str, Any]:
    return {
        "progressKey": PROGRESS_KEY,
        "aiEnabled": GENAI_AVAILABLE and bool(os.getenv("GEMINI_API_KEY", "").strip()),
        "model": DEFAULT_MODEL,
        "subjects": get_catalog(),
    }


def _json_for_script(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def _page_template() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>NPTEL Question Practice</title>
  <style>
    :root {
      --bg: #f4efe7;
      --bg-alt: #ece3d5;
      --surface: rgba(255, 255, 255, 0.82);
      --surface-strong: #ffffff;
      --text: #1f2937;
      --muted: #5b6472;
      --border: rgba(31, 41, 55, 0.12);
      --accent: #0f766e;
      --accent-strong: #115e59;
      --accent-soft: rgba(15, 118, 110, 0.12);
      --success: #166534;
      --warning: #a16207;
      --danger: #b42318;
      --shadow: 0 20px 45px rgba(15, 23, 42, 0.12);
      --shadow-soft: 0 8px 20px rgba(15, 23, 42, 0.08);
      --radius-xl: 24px;
      --radius-lg: 18px;
      --radius-md: 14px;
      --radius-sm: 10px;
      --content-width: 1240px;
    }

    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(15, 118, 110, 0.14), transparent 35%),
        radial-gradient(circle at top right, rgba(233, 179, 132, 0.20), transparent 32%),
        linear-gradient(180deg, var(--bg), var(--bg-alt));
      min-height: 100vh;
    }

    body::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image: linear-gradient(rgba(31, 41, 55, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(31, 41, 55, 0.03) 1px, transparent 1px);
      background-size: 36px 36px;
      mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.08), rgba(0, 0, 0, 0.02));
    }

    a { color: inherit; }
    button, input, select { font: inherit; }

    .shell {
      width: min(calc(100% - 32px), var(--content-width));
      margin: 0 auto;
      padding: 24px 0 42px;
      position: relative;
      z-index: 1;
    }

    .hero {
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.92), rgba(255, 248, 240, 0.84));
      border: 1px solid rgba(255, 255, 255, 0.85);
      box-shadow: var(--shadow);
      border-radius: var(--radius-xl);
      padding: 28px;
      display: grid;
      gap: 20px;
      backdrop-filter: blur(18px);
      margin-bottom: 22px;
    }

    .hero-top {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }

    .eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-size: 0.85rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--accent-strong);
      background: var(--accent-soft);
      border-radius: 999px;
      padding: 8px 14px;
      width: fit-content;
    }

    h1 {
      margin: 10px 0 10px;
      font-size: clamp(2rem, 4vw, 3.5rem);
      line-height: 1.03;
      letter-spacing: -0.04em;
    }

    .lede {
      margin: 0;
      color: var(--muted);
      max-width: 66ch;
      line-height: 1.55;
      font-size: 1rem;
    }

    .hero-card {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
    }

    .metric {
      background: rgba(255, 255, 255, 0.8);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      padding: 16px;
      box-shadow: var(--shadow-soft);
    }

    .metric-label {
      display: block;
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
      margin-bottom: 8px;
    }

    .metric-value {
      font-size: 1.55rem;
      font-weight: 700;
      letter-spacing: -0.03em;
    }

    .toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
      justify-content: space-between;
      margin: 18px 0 22px;
    }

    .toolbar-left, .toolbar-right { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }

    .button {
      border: 1px solid transparent;
      border-radius: 999px;
      padding: 11px 16px;
      cursor: pointer;
      transition: transform 160ms ease, box-shadow 160ms ease, background 160ms ease, color 160ms ease, border-color 160ms ease;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      box-shadow: 0 1px 1px rgba(15, 23, 42, 0.04);
    }

    .button:hover { transform: translateY(-1px); }
    .button:active { transform: translateY(0); }
    .button-primary { background: var(--accent); color: white; }
    .button-primary:hover { background: var(--accent-strong); }
    .button-secondary { background: white; color: var(--text); border-color: var(--border); }
    .button-ghost { background: transparent; color: var(--accent-strong); border-color: rgba(15, 118, 110, 0.22); }

    .notice {
      border-radius: var(--radius-md);
      padding: 14px 16px;
      border: 1px solid transparent;
      display: none;
      margin: 0 0 18px;
      line-height: 1.45;
    }
    .notice.is-visible { display: block; }
    .notice.success { background: rgba(22, 101, 52, 0.08); border-color: rgba(22, 101, 52, 0.18); color: var(--success); }
    .notice.warning { background: rgba(161, 98, 7, 0.09); border-color: rgba(161, 98, 7, 0.18); color: var(--warning); }
    .notice.error { background: rgba(180, 35, 24, 0.08); border-color: rgba(180, 35, 24, 0.18); color: var(--danger); }

    .layout {
      display: grid;
      grid-template-columns: minmax(240px, 320px) minmax(0, 1fr);
      gap: 22px;
      align-items: start;
    }

    .panel {
      background: var(--surface);
      border: 1px solid rgba(255, 255, 255, 0.85);
      border-radius: var(--radius-xl);
      box-shadow: var(--shadow-soft);
      backdrop-filter: blur(16px);
    }

    .sidebar {
      padding: 18px;
      position: sticky;
      top: 18px;
    }

    .sidebar h2, .content h2 {
      margin: 0 0 12px;
      letter-spacing: -0.03em;
    }

    .sidebar p {
      margin: 0 0 14px;
      color: var(--muted);
      line-height: 1.55;
    }

    .subject-list {
      display: grid;
      gap: 10px;
    }

    .subject-pill {
      width: 100%;
      text-align: left;
      border: 1px solid var(--border);
      background: rgba(255, 255, 255, 0.7);
      border-radius: var(--radius-md);
      padding: 14px 16px;
      cursor: pointer;
      transition: border-color 160ms ease, background 160ms ease, transform 160ms ease;
    }

    .subject-pill:hover { transform: translateY(-1px); }
    .subject-pill.is-active {
      background: rgba(15, 118, 110, 0.09);
      border-color: rgba(15, 118, 110, 0.3);
      box-shadow: 0 8px 16px rgba(15, 118, 110, 0.08);
    }

    .subject-pill strong { display: block; margin-bottom: 4px; }
    .subject-pill span { color: var(--muted); font-size: 0.92rem; }

    .content {
      padding: 18px;
    }

    .content-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      flex-wrap: wrap;
      margin-bottom: 14px;
    }

    .content-head p { margin: 0; color: var(--muted); }

    .question-list {
      display: grid;
      gap: 16px;
    }

    .question-card {
      background: var(--surface-strong);
      border-radius: var(--radius-lg);
      border: 1px solid var(--border);
      padding: 18px;
      box-shadow: 0 10px 26px rgba(15, 23, 42, 0.06);
      animation: fadeUp 280ms ease both;
    }

    @keyframes fadeUp {
      from { opacity: 0; transform: translateY(12px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .question-meta {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 10px;
      color: var(--muted);
      font-size: 0.92rem;
    }

    .question-card h3 {
      margin: 0 0 14px;
      font-size: 1.08rem;
      line-height: 1.5;
    }

    .choices {
      display: grid;
      gap: 10px;
      margin-bottom: 16px;
    }

    .choice {
      display: flex;
      gap: 10px;
      align-items: flex-start;
      padding: 12px 14px;
      background: rgba(244, 239, 231, 0.55);
      border: 1px solid rgba(31, 41, 55, 0.08);
      border-radius: var(--radius-sm);
      cursor: pointer;
      transition: border-color 160ms ease, background 160ms ease, transform 160ms ease;
    }

    .choice:hover { border-color: rgba(15, 118, 110, 0.24); transform: translateY(-1px); }
    .choice input { margin-top: 2px; }

    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 14px;
    }

    .result {
      display: grid;
      gap: 10px;
    }

    .result-box {
      padding: 12px 14px;
      border-radius: var(--radius-sm);
      line-height: 1.5;
    }

    .result-box.success {
      background: rgba(22, 101, 52, 0.08);
      color: var(--success);
    }

    .result-box.error {
      background: rgba(180, 35, 24, 0.08);
      color: var(--danger);
    }

    .result-box.info {
      background: rgba(15, 118, 110, 0.08);
      color: var(--accent-strong);
    }

    .explanation {
      background: rgba(255, 255, 255, 0.92);
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      padding: 14px;
      line-height: 1.58;
      white-space: pre-wrap;
    }

    .footer-note {
      color: var(--muted);
      font-size: 0.92rem;
      margin-top: 20px;
    }

    @media (max-width: 980px) {
      .layout { grid-template-columns: 1fr; }
      .sidebar { position: static; }
      .hero-card { grid-template-columns: 1fr; }
    }

    @media (max-width: 640px) {
      .shell { width: min(calc(100% - 20px), var(--content-width)); padding-top: 14px; }
      .hero, .sidebar, .content { padding: 16px; }
      .button { width: 100%; justify-content: center; }
      .toolbar-left, .toolbar-right { width: 100%; }
      .toolbar-right .button { width: auto; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header class="hero">
      <div class="hero-top">
        <div>
          <div class="eyebrow">NPTEL helper</div>
          <h1>Question practice that feels fast, durable, and easy to resume.</h1>
          <p class="lede">Work through subjects, track answers in browser storage, shuffle when you want a clean run, and generate concise explanations when a Gemini key is configured.</p>
        </div>
      </div>
      <div class="hero-card" id="metrics"></div>
    </header>

    <div class="toolbar">
      <div class="toolbar-left">
        <button class="button button-primary" id="save-button" type="button">Save progress</button>
        <button class="button button-secondary" id="shuffle-button" type="button">Shuffle current subject</button>
      </div>
      <div class="toolbar-right">
        <button class="button button-ghost" id="reset-subject-button" type="button">Reset current subject</button>
        <button class="button button-ghost" id="reset-all-button" type="button">Reset all progress</button>
      </div>
    </div>

    <div id="banner" class="notice" role="status" aria-live="polite"></div>

    <main class="layout">
      <aside class="panel sidebar">
        <h2>Subjects</h2>
        <p>Select a subject to continue where you left off.</p>
        <div id="subject-list" class="subject-list"></div>
        <p class="footer-note" id="persistence-hint"></p>
      </aside>

      <section class="panel content">
        <div class="content-head">
          <div>
            <h2 id="subject-title">Loading subject...</h2>
            <p id="subject-description"></p>
          </div>
          <div id="subject-status" class="eyebrow"></div>
        </div>
        <div id="question-list" class="question-list"></div>
      </section>
    </main>
  </div>

  <script id="bootstrap-data" type="application/json">__BOOTSTRAP_JSON__</script>
  <script>
    const bootstrap = JSON.parse(document.getElementById('bootstrap-data').textContent);
    const subjects = bootstrap.subjects || [];
    const progressKey = bootstrap.progressKey;
    const aiEnabled = Boolean(bootstrap.aiEnabled);
    const aiModel = bootstrap.model || 'gemini-2.0-flash';
    const storageAvailable = canUseStorage();
    const appState = loadState(storageAvailable);
    let activeSubjectKey = resolveActiveSubjectKey();

    const elements = {
      banner: document.getElementById('banner'),
      metrics: document.getElementById('metrics'),
      subjectList: document.getElementById('subject-list'),
      subjectTitle: document.getElementById('subject-title'),
      subjectDescription: document.getElementById('subject-description'),
      subjectStatus: document.getElementById('subject-status'),
      questionList: document.getElementById('question-list'),
      persistenceHint: document.getElementById('persistence-hint'),
      saveButton: document.getElementById('save-button'),
      shuffleButton: document.getElementById('shuffle-button'),
      resetSubjectButton: document.getElementById('reset-subject-button'),
      resetAllButton: document.getElementById('reset-all-button'),
    };

    if (!subjects.length) {
      showBanner('No subjects were found in data/subjects.', 'warning');
      elements.questionList.innerHTML = '<div class="result-box error">Add at least one subject JSON file before deploying.</div>';
      elements.subjectTitle.textContent = 'No subjects available';
    }

    elements.persistenceHint.textContent = storageAvailable
      ? 'Progress is persisted in browser localStorage.'
      : 'Browser persistence is unavailable in this session; progress will remain in memory only.';

    elements.saveButton.addEventListener('click', () => {
      if (persistState()) {
        showBanner('Progress saved to browser storage.', 'success');
      }
    });

    elements.shuffleButton.addEventListener('click', () => {
      if (!activeSubjectKey) {
        return;
      }

      const subjectState = ensureSubjectState(activeSubjectKey);
      const subject = getSubject(activeSubjectKey);
      subjectState.order = shuffle(subject.questions.map((question) => question.id));
      subjectState.answers = {};
      subjectState.explanations = {};
      persistState();
      render();
      showBanner('Subject shuffled and cleared.', 'success');
    });

    elements.resetSubjectButton.addEventListener('click', () => {
      if (!activeSubjectKey) {
        return;
      }

      if (!confirm('Reset the current subject? This clears its saved answers and explanations.')) {
        return;
      }

      delete appState.subjects[activeSubjectKey];
      persistState();
      render();
      showBanner('Current subject reset.', 'success');
    });

    elements.resetAllButton.addEventListener('click', () => {
      if (!confirm('Reset all saved progress? This clears every subject in local storage.')) {
        return;
      }

      appState.subjects = {};
      appState.activeSubjectKey = subjects[0] ? subjects[0].key : null;
      activeSubjectKey = appState.activeSubjectKey;
      persistState();
      render();
      showBanner('All saved progress reset.', 'success');
    });

    document.addEventListener('click', async (event) => {
      const pill = event.target.closest('[data-subject-key]');
      if (pill) {
        selectSubject(pill.dataset.subjectKey);
        return;
      }

      const actionButton = event.target.closest('[data-action]');
      if (!actionButton) {
        return;
      }

      const card = actionButton.closest('[data-question-id]');
      const questionId = card?.dataset.questionId;
      const subject = getSubject(activeSubjectKey);
      const question = subject?.questions.find((item) => item.id === questionId);

      if (!subject || !question || !questionId) {
        return;
      }

      const subjectState = ensureSubjectState(subject.key);

      if (actionButton.dataset.action === 'submit') {
        const selectedChoices = collectSelectedChoices(card, question);
        if (!selectedChoices.length) {
          showBanner('Select at least one option before submitting.', 'warning');
          return;
        }

        subjectState.answers[questionId] = selectedChoices;
        persistState();
        render();
        showBanner('Answer saved.', 'success');
        return;
      }

      if (actionButton.dataset.action === 'explain') {
        if (!aiEnabled) {
          showBanner('Configure GEMINI_API_KEY to enable AI explanations.', 'warning');
          return;
        }

        actionButton.disabled = true;
        actionButton.textContent = 'Generating...';

        try {
          const response = await fetch('/api/explain', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              subject_key: subject.key,
              question_id: question.id,
              question: question.question,
              choices: question.choices,
              correct_answers: question.answer,
              model: aiModel,
            }),
          });

          const payload = await response.json();
          if (!response.ok) {
            throw new Error(payload.error || 'AI explanation failed.');
          }

          subjectState.explanations[questionId] = payload.explanation;
          persistState();
          render();
          showBanner('AI explanation generated.', 'success');
        } catch (error) {
          showBanner(error.message || 'AI explanation failed.', 'error');
        } finally {
          actionButton.disabled = false;
          actionButton.textContent = 'Explain with AI';
        }
      }
    });

    render();

    function canUseStorage() {
      try {
        const probe = '__nptel_probe__';
        window.localStorage.setItem(probe, '1');
        window.localStorage.removeItem(probe);
        return true;
      } catch (error) {
        return false;
      }
    }

    function loadState(hasStorage) {
      if (!hasStorage) {
        return { activeSubjectKey: null, subjects: {} };
      }

      try {
        const raw = window.localStorage.getItem(progressKey);
        if (!raw) {
          return { activeSubjectKey: null, subjects: {} };
        }

        const parsed = JSON.parse(raw);
        if (!parsed || typeof parsed !== 'object') {
          return { activeSubjectKey: null, subjects: {} };
        }

        if (!parsed.subjects || typeof parsed.subjects !== 'object') {
          parsed.subjects = {};
        }

        return parsed;
      } catch (error) {
        return { activeSubjectKey: null, subjects: {} };
      }
    }

    function persistState() {
      if (!storageAvailable) {
        showBanner('Browser storage is unavailable in this session.', 'warning');
        return false;
      }

      try {
        appState.activeSubjectKey = activeSubjectKey;
        window.localStorage.setItem(progressKey, JSON.stringify(appState));
        return true;
      } catch (error) {
        showBanner('Unable to save progress: ' + error.message, 'error');
        return false;
      }
    }

    function resolveActiveSubjectKey() {
      const saved = appState.activeSubjectKey;
      if (saved && subjects.some((subject) => subject.key === saved)) {
        return saved;
      }

      return subjects[0] ? subjects[0].key : null;
    }

    function selectSubject(subjectKey) {
      if (subjectKey === activeSubjectKey) {
        return;
      }

      activeSubjectKey = subjectKey;
      appState.activeSubjectKey = subjectKey;
      ensureSubjectState(subjectKey);
      persistState();
      render();
    }

    function ensureSubjectState(subjectKey) {
      const subject = getSubject(subjectKey);
      if (!subject) {
        return { order: [], answers: {}, explanations: {} };
      }

      if (!appState.subjects[subjectKey] || typeof appState.subjects[subjectKey] !== 'object') {
        appState.subjects[subjectKey] = {
          order: subject.questions.map((question) => question.id),
          answers: {},
          explanations: {},
        };
      }

      const subjectState = appState.subjects[subjectKey];
      const questionIds = new Set(subject.questions.map((question) => question.id));

      subjectState.order = Array.isArray(subjectState.order)
        ? subjectState.order.filter((questionId) => questionIds.has(questionId))
        : [];

      subject.questions.forEach((question) => {
        if (!subjectState.order.includes(question.id)) {
          subjectState.order.push(question.id);
        }
      });

      if (!subjectState.answers || typeof subjectState.answers !== 'object') {
        subjectState.answers = {};
      }

      if (!subjectState.explanations || typeof subjectState.explanations !== 'object') {
        subjectState.explanations = {};
      }

      return subjectState;
    }

    function getSubject(subjectKey) {
      return subjects.find((subject) => subject.key === subjectKey) || null;
    }

    function shuffle(items) {
      const output = items.slice();
      for (let index = output.length - 1; index > 0; index -= 1) {
        const randomIndex = Math.floor(Math.random() * (index + 1));
        [output[index], output[randomIndex]] = [output[randomIndex], output[index]];
      }
      return output;
    }

    function render() {
      if (!subjects.length) {
        return;
      }

      const subject = getSubject(activeSubjectKey) || subjects[0];
      activeSubjectKey = subject.key;
      const subjectState = ensureSubjectState(subject.key);
      const orderedQuestions = subjectState.order
        .map((questionId) => subject.questions.find((question) => question.id === questionId))
        .filter(Boolean);
      const answeredCount = Object.keys(subjectState.answers || {}).length;
      const remainingCount = Math.max(subject.questions.length - answeredCount, 0);

      elements.metrics.innerHTML = [
        metricMarkup('Questions', subject.questions.length),
        metricMarkup('Answered', answeredCount),
        metricMarkup('Remaining', remainingCount),
      ].join('');

      elements.subjectList.innerHTML = subjects.map((item) => subjectPillMarkup(item, item.key === subject.key)).join('');
      elements.subjectTitle.textContent = subject.label;
      elements.subjectDescription.textContent = `${subject.questions.length} questions in this subject.`;
      elements.subjectStatus.textContent = answeredCount > 0 ? `${answeredCount} saved` : 'No answers yet';

      if (!orderedQuestions.length) {
        elements.questionList.innerHTML = '<div class="result-box warning">No questions are available for this subject.</div>';
        return;
      }

      elements.questionList.innerHTML = orderedQuestions.map((question, position) => questionCardMarkup(subject, subjectState, question, position + 1)).join('');
    }

    function metricMarkup(label, value) {
      return `
        <div class="metric">
          <span class="metric-label">${escapeHtml(label)}</span>
          <div class="metric-value">${escapeHtml(String(value))}</div>
        </div>
      `;
    }

    function subjectPillMarkup(subject, isActive) {
      return `
        <button class="subject-pill ${isActive ? 'is-active' : ''}" type="button" data-subject-key="${escapeHtml(subject.key)}">
          <strong>${escapeHtml(subject.label)}</strong>
          <span>${escapeHtml(String(subject.questions.length))} questions</span>
        </button>
      `;
    }

    function questionCardMarkup(subject, subjectState, question, position) {
      const selectedAnswers = Array.isArray(subjectState.answers[question.id]) ? subjectState.answers[question.id] : [];
      const explanation = subjectState.explanations[question.id] || '';
      const isMultiple = question.answer.length > 1;
      const resultMarkup = buildResultMarkup(question, selectedAnswers);
      const choiceMarkup = question.choices.map((choice, index) => {
        const inputType = isMultiple ? 'checkbox' : 'radio';
        const name = `${question.id}-${inputType}`;
        const checked = selectedAnswers.includes(choice) ? 'checked' : '';
        const ariaLabel = `${isMultiple ? 'Select' : 'Choose'} option ${index + 1}`;

        return `
          <label class="choice">
            <input type="${inputType}" name="${escapeHtml(name)}" data-choice="${escapeHtml(choice)}" ${checked} aria-label="${escapeHtml(ariaLabel)}">
            <span>${escapeHtml(choice)}</span>
          </label>
        `;
      }).join('');

      return `
        <article class="question-card" data-question-id="${escapeHtml(question.id)}">
          <div class="question-meta">
            <span>Question ${position}</span>
            <span>${escapeHtml(question.heading || subject.label)}</span>
          </div>
          <h3>${escapeHtml(question.question)}</h3>
          ${isMultiple ? '<div class="eyebrow" style="margin-bottom: 12px;">Multiple correct answers</div>' : ''}
          <div class="choices">
            ${choiceMarkup}
          </div>
          <div class="actions">
            <button class="button button-primary" type="button" data-action="submit">Submit answer</button>
            <button class="button button-secondary" type="button" data-action="explain">Explain with AI</button>
          </div>
          <div class="result">
            ${resultMarkup}
            ${explanation ? `<div class="explanation"><strong>AI explanation</strong><div>${formatMultiline(explanation)}</div></div>` : ''}
          </div>
        </article>
      `;
    }

    function buildResultMarkup(question, selectedAnswers) {
      if (!selectedAnswers.length) {
        return '<div class="result-box info">Choose an option and submit to check your answer.</div>';
      }

      const correctAnswers = question.answer.slice().sort();
      const submittedAnswers = selectedAnswers.slice().sort();
      const isCorrect = arraysEqual(correctAnswers, submittedAnswers);
      const correctText = correctAnswers.join(' and ');
      const submittedText = submittedAnswers.join(' and ');

      return isCorrect
        ? `<div class="result-box success">Correct response. Accepted answer: ${escapeHtml(correctText)}</div>`
        : `<div class="result-box error">Response is not correct. You selected: ${escapeHtml(submittedText)}. Accepted answer: ${escapeHtml(correctText)}</div>`;
    }

    function collectSelectedChoices(card, question) {
      const selected = Array.from(card.querySelectorAll('input[data-choice]:checked'))
        .map((input) => input.dataset.choice)
        .filter(Boolean);

      if (question.answer.length > 1) {
        return selected;
      }

      return selected.slice(0, 1);
    }

    function arraysEqual(left, right) {
      if (left.length !== right.length) {
        return false;
      }

      return left.every((item, index) => item === right[index]);
    }

    function showBanner(message, tone) {
      elements.banner.textContent = message;
      elements.banner.className = `notice is-visible ${tone}`;
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
    }

    function formatMultiline(value) {
      return escapeHtml(value).replaceAll('\n', '<br>');
    }
  </script>
</body>
</html>
"""


@app.after_request
def _set_security_headers(response: Response) -> Response:
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    if response.mimetype == "text/html":
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/")
def index() -> Response:
  page = _page_template().replace("__BOOTSTRAP_JSON__", _json_for_script(_build_index_payload()))
  return Response(page, content_type="text/html; charset=utf-8")


@app.get("/api/health")
def health() -> Response:
    return jsonify({"status": "ok", "subjects": len(get_catalog())})


@app.get("/api/catalog")
def catalog() -> Response:
    return jsonify(_build_index_payload())


@app.get("/api/subjects/<subject_key>")
def subject_detail(subject_key: str) -> Response:
    subject = _get_subject(subject_key)
    if subject is None:
        return jsonify({"error": "Subject not found."}), 404

    return jsonify(subject)


@app.post("/api/explain")
def explain() -> Response:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return jsonify({"error": "Configure GEMINI_API_KEY in the Vercel environment."}), 503

    if not GENAI_AVAILABLE:
        return jsonify({"error": "google-genai is not available in this deployment."}), 503

    payload = request.get_json(silent=True) or {}
    question_text = str(payload.get("question", "")).strip()
    correct_answers = payload.get("correct_answers", [])

    if not question_text:
        return jsonify({"error": "question is required."}), 400

    if isinstance(correct_answers, str):
        correct_answers = [correct_answers]
    elif not isinstance(correct_answers, list):
        correct_answers = []

    answer_text = " and ".join(str(answer).strip() for answer in correct_answers if str(answer).strip())
    prompt = (
        "Explain why the following answer is correct for this exam question. "
        "Keep the explanation concise, factual, and concept-focused.\n\n"
        f"Question: {question_text}\n"
        f"Correct Answer: {answer_text}"
    )

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", DEFAULT_MODEL),
            contents=prompt,
        )
    except Exception as error:  # pragma: no cover - remote API failures are environment-specific
        return jsonify({"error": f"AI explanation failed: {error}"}), 502

    explanation = getattr(response, "text", "") or "No explanation was returned by the model."
    return jsonify({"explanation": explanation})


def run_dev_server() -> None:
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=True)
