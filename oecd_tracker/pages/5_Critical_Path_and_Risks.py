"""Critical Path & Risks — update status; counts feed the Dashboard."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from store import get_state, save_state
from ui import page_header, saved_toast, setup, status_emoji

setup("Critical Path & Risks", "🧭")
state = get_state()
page_header("Critical Path & Risks",
            "The four items that actually gate the project, plus the PM's risk "
            "watchlist. Update status here; open counts show on the Dashboard.")

STATUS_OPTS = ["Not started", "In progress", "Blocked", "Done", "Closed"]
RISK_STATUS = ["Open", "Mitigating", "Closed"]
LIK = ["Low", "Medium", "High"]

# ----------------------------------------------------------- critical path
st.markdown("#### Hidden critical path — the 4 things that gate this project")
cp = pd.DataFrame(state.get("critical_path", []))
cp_edit = st.data_editor(
    cp,
    column_config={
        "id": st.column_config.NumberColumn("#", disabled=True, width="small"),
        "item": st.column_config.TextColumn("Item", width="medium"),
        "why": st.column_config.TextColumn("Why it gates", width="large"),
        "owner": st.column_config.TextColumn("Owner", width="small"),
        "status": st.column_config.SelectboxColumn("Status", options=STATUS_OPTS),
        "last_reviewed": st.column_config.TextColumn("Last reviewed", width="small"),
    },
    column_order=["id", "item", "why", "owner", "status", "last_reviewed"],
    hide_index=True, use_container_width=True, key="cp_editor",
)

st.markdown('<hr class="section-rule">', unsafe_allow_html=True)

# ------------------------------------------------------------------- risks
st.markdown("#### Risk watchlist (PM's eyes only)")
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
        "status": st.column_config.SelectboxColumn("Status", options=RISK_STATUS),
        "last_updated": st.column_config.TextColumn("Updated", width="small"),
    },
    column_order=["id", "risk", "mitigation", "owner", "likelihood", "impact",
                  "status", "last_updated"],
    hide_index=True, use_container_width=True, key="risk_editor",
)

if st.button("💾 Save", type="primary"):
    state["critical_path"] = cp_edit.to_dict("records")
    state["risks"] = rk_edit.to_dict("records")
    save_state()
    saved_toast()
    st.rerun()
