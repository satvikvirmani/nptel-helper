from __future__ import annotations

import json
from uuid import uuid4

from streamlit_js_eval import streamlit_js_eval


def load_progress(storage_key: str) -> dict:
    """Read progress JSON from browser localStorage."""
    expression = f"localStorage.getItem({json.dumps(storage_key)})"
    raw = streamlit_js_eval(js_expressions=expression, key=f"load_{uuid4().hex}")

    if not raw or not isinstance(raw, str):
        return {}

    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}

    return value if isinstance(value, dict) else {}


def save_progress(storage_key: str, progress: dict) -> None:
    """Persist progress JSON to browser localStorage."""
    serialized = json.dumps(progress, separators=(",", ":"))
    expression = (
        f"localStorage.setItem({json.dumps(storage_key)}, {json.dumps(serialized)})"
    )
    streamlit_js_eval(js_expressions=expression, key=f"save_{uuid4().hex}")


def clear_progress(storage_key: str) -> None:
    """Delete progress from browser localStorage."""
    expression = f"localStorage.removeItem({json.dumps(storage_key)})"
    streamlit_js_eval(js_expressions=expression, key=f"clear_{uuid4().hex}")
