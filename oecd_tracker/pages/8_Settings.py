"""Settings — key dates, targets, today-override, export/import, reset."""

from __future__ import annotations

import json

import streamlit as st

import logic
from store import STATE_FILE, get_state, reset_state, save_state
from ui import page_header, saved_toast, setup

setup("Settings", "⚙️")
state = get_state()
cfg = state.setdefault("settings", {})
page_header("Settings",
            "Change the project parameters that everything else reads from. "
            "'Today override' lets you run what-if scenarios against a fixed date.")

# ---------------------------------------------------------------- today / dates
st.markdown("#### Dates & clock")
c1, c2 = st.columns(2)
with c1:
    use_override = st.checkbox(
        "Override 'today' (what-if)", value=bool(cfg.get("today_override")))
    if use_override:
        d = logic.parse_date(cfg.get("today_override")) or logic.today(state)
        cfg["today_override"] = st.date_input("Today =", value=d).strftime("%Y-%m-%d")
    else:
        cfg["today_override"] = None
    st.caption(f"Live today resolves to **{logic.today(state):%d %b %Y}**.")
with c2:
    cfg["assignment_date"] = st.text_input("Assignment date", cfg.get("assignment_date", ""))
    cfg["kickoff"] = st.text_input("Kick-off", cfg.get("kickoff", ""))

c3, c4 = st.columns(2)
cfg["final_contract"] = c3.text_input("Final delivery (contract)", cfg.get("final_contract", ""))
cfg["final_shadow"] = c4.text_input("Final delivery (shadow)", cfg.get("final_shadow", ""))

# ---------------------------------------------------------------------- targets
st.markdown("#### Targets")
c5, c6, c7 = st.columns(3)
cfg["sample_target"] = c5.number_input(
    "Sample target (n)", min_value=0, value=int(cfg.get("sample_target", 1000)), step=50)
cfg["booster_threshold_pct"] = c6.number_input(
    "Booster threshold (%)", min_value=0, max_value=100,
    value=int(cfg.get("booster_threshold_pct", 70)))
cfg["booster_decision_date"] = c7.text_input(
    "Booster decision date", cfg.get("booster_decision_date", ""))
cfg["qa_target_pct"] = c5.number_input(
    "QA verification target (%)", min_value=0.0, max_value=100.0,
    value=float(cfg.get("qa_target_pct", 12.5)), step=0.5)

if st.button("💾 Save settings", type="primary"):
    save_state()
    saved_toast()
    st.rerun()

st.markdown('<hr class="section-rule">', unsafe_allow_html=True)

# ----------------------------------------------------------- backup / restore
st.markdown("#### Backup & restore")
c8, c9 = st.columns(2)
with c8:
    st.download_button(
        "⬇️ Export all data (JSON)",
        data=json.dumps(state, ensure_ascii=False, indent=2),
        file_name="oecd_tracker_state.json", mime="application/json")
    st.caption("A full snapshot you can archive or move to another machine.")
with c9:
    up = st.file_uploader("⬆️ Import a JSON snapshot", type="json")
    if up is not None and st.button("Load this snapshot"):
        st.session_state["state"] = json.load(up)
        save_state()
        st.success("Snapshot loaded.")
        st.rerun()

st.markdown('<hr class="section-rule">', unsafe_allow_html=True)
st.markdown("#### Danger zone")
st.caption(f"State file: `{STATE_FILE}`")
if st.button("♻️ Reset everything to the original Excel data"):
    reset_state()
    st.warning("All edits discarded — reseeded from the original workbook.")
    st.rerun()
