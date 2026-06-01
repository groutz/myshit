"""This Week — pre-kick-off prep tasks. Tick Done; completion % updates live."""

from __future__ import annotations

import pandas as pd
import streamlit as st

import logic
from store import get_state, save_state
from ui import page_header, saved_toast, setup

setup("This Week", "✅")
state = get_state()
page_header("This Week — prep tasks",
            "The contract clock runs from assignment (14 May). Tick each task "
            "as you finish it; the Dashboard completion % and Upcoming list "
            "update immediately.")

tasks = state.get("this_week", [])
done = sum(1 for t in tasks if t.get("done"))
total = len(tasks)
pct = round(100 * done / total) if total else 0

c1, c2 = st.columns([1, 3])
c1.metric("Completion", f"{done} / {total}", f"{pct}%")
c2.progress(pct / 100 if total else 0)

df = pd.DataFrame(tasks)
df["due"] = pd.to_datetime(df["due"], errors="coerce")

edited = st.data_editor(
    df,
    column_config={
        "id": st.column_config.NumberColumn("#", disabled=True, width="small"),
        "action": st.column_config.TextColumn("Action", width="large"),
        "owner": st.column_config.TextColumn("Owner", width="small"),
        "due": st.column_config.DateColumn("Due", format="ddd DD MMM", width="small"),
        "done": st.column_config.CheckboxColumn("Done?", width="small"),
        "notes": st.column_config.TextColumn("Notes", width="medium"),
    },
    column_order=["id", "action", "owner", "due", "done", "notes"],
    hide_index=True, use_container_width=True, key="thisweek_editor",
)

if st.button("💾 Save", type="primary"):
    out = edited.copy()
    out["due"] = out["due"].apply(
        lambda d: d.strftime("%Y-%m-%d") if pd.notna(d) else "")
    state["this_week"] = out.to_dict("records")
    save_state()
    saved_toast()
    st.rerun()

st.caption("Tip: edit a cell, then click **Save**. Overdue, incomplete tasks "
           "are flagged on the Dashboard.")
