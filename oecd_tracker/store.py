"""State storage for the OECD/INFE 2026 PM Tracker app.

The Excel workbook is the original source; on first run we seed a human-readable
``state.json`` from ``seed_data.json``. From then on, every edit the user makes in
the app is written straight back to ``state.json`` so progress persists between
sessions. Delete ``state.json`` (or use Settings -> Reset) to start over.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import streamlit as st

BASE = Path(__file__).resolve().parent
SEED_FILE = BASE / "seed_data.json"
STATE_FILE = BASE / "state.json"


def _load_seed() -> dict:
    with open(SEED_FILE, encoding="utf-8") as fh:
        return json.load(fh)


def _read_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    data = _load_seed()
    _write_state(data)
    return data


def _write_state(data: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def get_state() -> dict:
    """Return the live state, loading it into the Streamlit session once."""
    if "state" not in st.session_state:
        st.session_state["state"] = _read_state()
    return st.session_state["state"]


def save_state(data: dict | None = None) -> None:
    """Persist the current (or supplied) state to disk."""
    if data is not None:
        st.session_state["state"] = data
    _write_state(st.session_state["state"])


def reset_state() -> dict:
    """Discard all edits and reseed from the original Excel-derived data."""
    data = copy.deepcopy(_load_seed())
    st.session_state["state"] = data
    _write_state(data)
    return data
