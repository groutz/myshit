"""State storage for the OECD/INFE 2026 PM Tracker app.

Two interchangeable backends, chosen automatically:

* **Local file** (default): edits persist to ``state.json`` next to this file.
  Used when you run the app on your own machine.
* **Google Sheet** (cloud): used automatically when Streamlit secrets contain a
  ``[gcp_service_account]`` block and ``[sheets] spreadsheet_key``. The whole
  state is gzip+base64 encoded and stored in a private Sheet, so edits survive
  the ephemeral filesystem of Streamlit Community Cloud.

In both cases the Excel-derived ``seed_data.json`` is the baseline used on first
run and by Settings -> Reset.
"""

from __future__ import annotations

import base64
import copy
import gzip
import json
from pathlib import Path

import streamlit as st

BASE = Path(__file__).resolve().parent
SEED_FILE = BASE / "seed_data.json"
STATE_FILE = BASE / "state.json"

# Google Sheets caps a single cell at 50k chars; we chunk the encoded blob down
# column A and re-join on read, so it scales safely as the logs fill up.
_CHUNK = 45000


def _load_seed() -> dict:
    with open(SEED_FILE, encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------- backend pick
def using_sheets() -> bool:
    """True when Google-Sheets credentials are present in Streamlit secrets."""
    try:
        return "gcp_service_account" in st.secrets and "sheets" in st.secrets
    except Exception:
        return False


def backend_label() -> str:
    if using_sheets():
        return "Google Sheet (cloud, persistent)"
    return f"Local file · {STATE_FILE.name}"


# ----------------------------------------------------- (de)serialisation
def _encode(data: dict) -> str:
    raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
    return base64.b64encode(gzip.compress(raw)).decode("ascii")


def _decode(blob: str) -> dict:
    raw = gzip.decompress(base64.b64decode(blob.encode("ascii")))
    return json.loads(raw.decode("utf-8"))


# --------------------------------------------------------- local-file backend
def _file_read() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    data = _load_seed()
    _file_write(data)
    return data


def _file_write(data: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


# ------------------------------------------------------ google-sheets backend
@st.cache_resource(show_spinner=False)
def _worksheet():
    import gspread
    from google.oauth2.service_account import Credentials

    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    sh = gspread.authorize(creds).open_by_key(st.secrets["sheets"]["spreadsheet_key"])
    try:
        return sh.worksheet("state")
    except Exception:
        return sh.add_worksheet(title="state", rows=200, cols=1)


def _sheet_read() -> dict:
    ws = _worksheet()
    blob = "".join(ws.col_values(1)).strip()
    if not blob:
        data = _load_seed()
        _sheet_write(data)
        return data
    return _decode(blob)


def _sheet_write(data: dict) -> None:
    import gspread

    ws = _worksheet()
    blob = _encode(data)
    chunks = [blob[i:i + _CHUNK] for i in range(0, len(blob), _CHUNK)] or [""]
    ws.clear()
    cells = [gspread.Cell(i + 1, 1, c) for i, c in enumerate(chunks)]
    # RAW so the base64 text is never interpreted as a formula/number.
    ws.update_cells(cells, value_input_option="RAW")


# ----------------------------------------------------------------- public API
def _read() -> dict:
    return _sheet_read() if using_sheets() else _file_read()


def _write(data: dict) -> None:
    if using_sheets():
        _sheet_write(data)
    else:
        _file_write(data)


def _migrate(state: dict) -> dict:
    """Backfill task-model fields onto data saved by an older app version, so
    existing state.json files gain due/assign-by dates, weights, etc. without
    touching the user's reported progress (pct / done / text)."""
    seed = _load_seed()
    sub_fields = ("type", "weight", "effort_days", "due", "assign_by")

    seed_sub = {s["id"]: s for p in seed.get("phases", []) for s in p["subtasks"]}
    for p in state.get("phases", []):
        for s in p.get("subtasks", []):
            ref = seed_sub.get(s.get("id"))
            if ref:
                for k in sub_fields:
                    if not s.get(k):
                        s[k] = ref.get(k)

    seed_tw = {t["id"]: t for t in seed.get("this_week", [])}
    for t in state.get("this_week", []):
        ref = seed_tw.get(t.get("id"))
        if ref:
            for k in ("type", "weight", "effort_days", "assign_by"):
                if not t.get(k):
                    t[k] = ref.get(k)

    seed_cp = {c["id"]: c for c in seed.get("critical_path", [])}
    for c in state.get("critical_path", []):
        if not c.get("phase"):
            c["phase"] = seed_cp.get(c.get("id"), {}).get("phase", "")

    seed_rk = {r["id"]: r for r in seed.get("risks", [])}
    for r in state.get("risks", []):
        if not r.get("phase"):
            r["phase"] = seed_rk.get(r.get("id"), {}).get("phase", "")

    # weekly reports moved from Fridays (whole project) to Mondays during the
    # fieldwork window — adopt the new schedule + settings if not present yet.
    cfg = state.setdefault("settings", {})
    for k in ("fieldwork_start", "fieldwork_end", "report_day", "report_deadline"):
        if not cfg.get(k):
            cfg[k] = seed["settings"].get(k)
    if "weekly_reports" not in state:
        state["weekly_reports"] = seed.get("weekly_reports", [])
        state.pop("friday_reports", None)

    # ensure newly-added seed sub-tasks (e.g. Sakis's daily sample upload) land
    # in existing state, matched by phase + sub-task id.
    state_subs = {(p["id"], s.get("id"))
                  for p in state.get("phases", []) for s in p.get("subtasks", [])}
    state_phases = {p["id"]: p for p in state.get("phases", [])}
    for sp in seed.get("phases", []):
        for ss in sp.get("subtasks", []):
            if (sp["id"], ss.get("id")) not in state_subs and sp["id"] in state_phases:
                state_phases[sp["id"]]["subtasks"].append(dict(ss))
    return state


def get_state() -> dict:
    """Return the live state, loading it into the Streamlit session once."""
    if "state" not in st.session_state:
        st.session_state["state"] = _migrate(_read())
    return st.session_state["state"]


def save_state(data: dict | None = None) -> None:
    """Persist the current (or supplied) state to the active backend."""
    if data is not None:
        st.session_state["state"] = data
    _write(st.session_state["state"])


def reset_state() -> dict:
    """Discard all edits and reseed from the original Excel-derived data."""
    data = copy.deepcopy(_load_seed())
    st.session_state["state"] = data
    _write(data)
    return data
