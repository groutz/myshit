"""Critical Path & Risks — status is auto-derived from the linked phase.

You maintain the narrative (item text, why, mitigation, owner); the status and
open/closed counts update themselves from task progress, and feed the Dashboard.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

import logic
from store import get_state, save_state
from ui import badge, page_header, saved_toast, setup

setup("Critical Path & Risks", "🧭")
state = get_state()
page_header("Critical Path & Risks",
            "Statuses are derived automatically from the phase each item depends "
            "on — report tasks on Weekly To-Do and these follow. Edit the wording "
            "and mitigations here.")

LIK = ["Low", "Medium", "High"]

# ---------------------------------------------------------- critical path
st.markdown("#### Hidden critical path — what gates the project")
for c in logic.critical_path_rows(state):
    cols = st.columns([3.2, 1.2, 1])
    cols[0].markdown(f"**{c['item']}**")
    cols[0].caption(c["why"])
    cols[1].markdown(badge(c["status"]), unsafe_allow_html=True)
    cols[2].markdown(f"<span class='kpi-note'>{c['owner']} · {c['pct']:.0f}% "
                     f"({c.get('phase','')})</span>", unsafe_allow_html=True)

with st.expander("✏️ Edit critical-path wording"):
    cp = pd.DataFrame(state.get("critical_path", []))
    cp_edit = st.data_editor(
        cp,
        column_config={
            "id": st.column_config.NumberColumn("#", disabled=True, width="small"),
            "item": st.column_config.TextColumn("Item", width="medium"),
            "why": st.column_config.TextColumn("Why it gates", width="large"),
            "owner": st.column_config.TextColumn("Owner", width="small"),
            "phase": st.column_config.TextColumn("Linked phase", width="small"),
        },
        column_order=["id", "item", "why", "owner", "phase"],
        hide_index=True, use_container_width=True, key="cp_editor",
    )
    if st.button("💾 Save critical path", key="save_cp"):
        # preserve any fields not shown in the editor
        by_id = {r["id"]: r for r in cp_edit.to_dict("records")}
        for c in state["critical_path"]:
            c.update(by_id.get(c["id"], {}))
        save_state(); saved_toast(); st.rerun()

st.markdown('<hr class="section-rule">', unsafe_allow_html=True)

# ------------------------------------------------------------------- risks
st.markdown("#### Risk watchlist (internal) — auto-status")
for r in logic.risk_rows(state):
    cols = st.columns([3.2, 1.2, 1])
    cols[0].markdown(f"**{r['risk']}**")
    cols[0].caption(f"Mitigation: {r['mitigation']}")
    badge_status = "Closed" if not r["open"] else "Open"
    cols[1].markdown(badge(badge_status) +
                     f" <span class='kpi-note'>{r['auto_status']}</span>",
                     unsafe_allow_html=True)
    cols[2].markdown(f"<span class='kpi-note'>L:{r['likelihood']} / "
                     f"I:{r['impact']}</span>", unsafe_allow_html=True)

with st.expander("✏️ Edit risks"):
    rk = pd.DataFrame(state.get("risks", []))
    rk_edit = st.data_editor(
        rk,
        column_config={
            "id": st.column_config.NumberColumn("#", disabled=True, width="small"),
            "risk": st.column_config.TextColumn("Risk", width="medium"),
            "mitigation": st.column_config.TextColumn("Mitigation", width="large"),
            "owner": st.column_config.TextColumn("Owner", width="small"),
            "likelihood": st.column_config.SelectboxColumn("Likelihood", options=LIK),
            "impact": st.column_config.SelectboxColumn("Impact", options=LIK),
            "phase": st.column_config.TextColumn("Linked phase", width="small"),
        },
        column_order=["id", "risk", "mitigation", "owner", "likelihood",
                      "impact", "phase"],
        hide_index=True, use_container_width=True, key="risk_editor",
    )
    if st.button("💾 Save risks", key="save_risks"):
        by_id = {r["id"]: r for r in rk_edit.to_dict("records")}
        for r in state["risks"]:
            r.update(by_id.get(r["id"], {}))
        save_state(); saved_toast(); st.rerun()
