"""Phases P1–P6 — set % complete per sub-task; phase rollup + status auto-derive."""

from __future__ import annotations

import pandas as pd
import streamlit as st

import logic
from store import get_state, save_state
from ui import badge, page_header, saved_toast, setup

setup("Phases", "🗂️")
state = get_state()
page_header("Phases — P1 to P6",
            "Set each sub-task's % complete. The phase bar is the mean of its "
            "sub-tasks, and status auto-derives from that vs the phase's "
            "shadow/contract dates. This drives the Dashboard phase chart and "
            "overall progress.")

st.metric("Overall implementation progress", f"{logic.overall_progress(state):.0f}%")
st.markdown('<hr class="section-rule">', unsafe_allow_html=True)

rollups = {r["id"]: r for r in logic.phase_rows(state)}

for pi, phase in enumerate(state.get("phases", [])):
    roll = rollups[phase["id"]]
    head = st.columns([3, 1, 1.4])
    head[0].markdown(f"### {phase['id']} · {phase['name']}")
    head[0].caption(phase.get("window", ""))
    head[1].metric("Phase", f"{roll['pct']:.0f}%")
    head[2].markdown(badge(roll["status"]) +
                     f" &nbsp;<span class='kpi-note'>{roll['n_done']}/{roll['n_sub']} "
                     "sub-tasks done</span>", unsafe_allow_html=True)

    df = pd.DataFrame(phase["subtasks"])
    edited = st.data_editor(
        df,
        column_config={
            "id": st.column_config.TextColumn("ID", disabled=True, width="small"),
            "task": st.column_config.TextColumn("Sub-task", width="large"),
            "owner": st.column_config.TextColumn("Owner", width="small"),
            "pct": st.column_config.NumberColumn("% complete", min_value=0,
                                                 max_value=100, step=5, width="small"),
            "notes": st.column_config.TextColumn("Notes", width="medium"),
        },
        column_order=["id", "task", "owner", "pct", "notes"],
        hide_index=True, use_container_width=True, key=f"phase_{phase['id']}",
    )
    state["phases"][pi]["subtasks"] = edited.to_dict("records")
    st.markdown('<hr class="section-rule">', unsafe_allow_html=True)

if st.button("💾 Save all phases", type="primary"):
    save_state()
    saved_toast()
    st.rerun()
