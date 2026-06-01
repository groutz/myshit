"""Milestones — dates are editable; % complete is DERIVED from each phase.

Milestone i mirrors phase i (P1->M1 …), so reporting tasks moves the milestone
automatically. Run to the Shadow date; the Ministry only sees the Contract column.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

import logic
from store import get_state, save_state
from ui import badge, page_header, saved_toast, setup

setup("Milestones", "🎯")
state = get_state()
page_header("Milestones — Shadow vs Contract",
            "% complete is derived from the matching phase's weighted tasks — "
            "report progress on Weekly To-Do and these move on their own. Here "
            "you only adjust the dates if they change.")

# editable dates only
df = pd.DataFrame([{
    "id": m["id"], "name": m["name"],
    "contract": logic.parse_date(m.get("contract")),
    "shadow": logic.parse_date(m.get("shadow")),
} for m in state["milestones"]])

edited = st.data_editor(
    df,
    column_config={
        "id": st.column_config.NumberColumn("#", disabled=True, width="small"),
        "name": st.column_config.TextColumn("Milestone", width="large", disabled=True),
        "contract": st.column_config.DateColumn("Contract date", format="DD MMM YYYY"),
        "shadow": st.column_config.DateColumn("Shadow date", format="DD MMM YYYY"),
    },
    column_order=["id", "name", "contract", "shadow"],
    hide_index=True, use_container_width=True, key="ms_editor",
)

if st.button("💾 Save dates", type="primary"):
    by_id = {r["id"]: r for r in edited.to_dict("records")}
    for m in state["milestones"]:
        upd = by_id.get(m["id"])
        if upd:
            for col in ("contract", "shadow"):
                v = upd[col]
                m[col] = v.strftime("%Y-%m-%d") if pd.notna(v) else ""
    save_state()
    saved_toast()
    st.rerun()

st.markdown('<hr class="section-rule">', unsafe_allow_html=True)
st.markdown("#### Derived status & countdown")
for r in logic.milestone_rows(state):
    cols = st.columns([2.4, 1.1, 1, 1.4])
    with cols[0]:
        st.markdown(f"**{r['name']}**", help=r.get("why", ""))
        st.progress(min(int(r["pct"]), 100))
    cols[1].markdown(badge(r["status"]), unsafe_allow_html=True)
    dts = r["days_to_shadow"]
    dtc = r["days_to_contract"]
    cols[2].markdown(f"<span class='kpi-note'>{dts:+d}d → shadow</span>"
                     if dts is not None else "—", unsafe_allow_html=True)
    cols[3].markdown(f"<span class='kpi-note'>{dtc:+d}d → contract · {r['pct']:.0f}%</span>"
                     if dtc is not None else "—", unsafe_allow_html=True)
