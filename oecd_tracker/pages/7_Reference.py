"""Reference — read-mostly context: Team, Buffers, Kickoff Playbook, Project info."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from store import get_state, save_state
from ui import page_header, saved_toast, setup

setup("Reference", "📚")
state = get_state()
page_header("Reference",
            "Standing context for the project — who needs what, what's flexible "
            "vs protected, the kickoff playbook, and the project header.")

tabs = st.tabs(["👥 Team", "🛡️ Buffers", "🤝 Kickoff Playbook", "ℹ️ Project info"])

with tabs[0]:
    st.dataframe(pd.DataFrame(state.get("team", [])), hide_index=True,
                 use_container_width=True,
                 column_config={
                     "person": "Person", "role": "Role", "read": "Read",
                     "need": "What I need", "give": "What I give", "backup": "Backup"})

with tabs[1]:
    st.caption("Flexible items absorb pressure; Protected items are non-negotiable.")
    st.dataframe(pd.DataFrame(state.get("buffers", [])), hide_index=True,
                 use_container_width=True,
                 column_config={"category": "Category", "item": "Item",
                                "status": "Status", "notes": "Notes"})

with tabs[2]:
    st.caption("Tick 'Minuted?' as items are confirmed in the meeting minutes.")
    kp = pd.DataFrame(state.get("kickoff_playbook", []))
    e = st.data_editor(
        kp,
        column_config={
            "category": st.column_config.TextColumn("Category", disabled=True),
            "item": st.column_config.TextColumn("Item", width="large", disabled=True),
            "outcome": st.column_config.TextColumn("Outcome / state"),
            "minuted": st.column_config.CheckboxColumn("Minuted?"),
            "notes": st.column_config.TextColumn("Notes"),
        },
        column_order=["category", "item", "outcome", "minuted", "notes"],
        hide_index=True, use_container_width=True, key="kp_editor",
    )
    if st.button("💾 Save playbook", type="primary"):
        state["kickoff_playbook"] = e.to_dict("records")
        save_state(); saved_toast(); st.rerun()

with tabs[3]:
    meta = state.get("meta", {})
    for k, v in meta.items():
        st.markdown(f"**{k}** — {v}")
