"""Sample tracker — 26 strata. Enter completes → % of target + booster flags."""

from __future__ import annotations

import pandas as pd
import streamlit as st

import logic
from store import get_state, save_state
from ui import page_header, saved_toast, setup

setup("Sample", "📞")
state = get_state()
cfg = state.get("settings", {})
page_header("Sample tracker — 26 strata (NUTS-2 × Urban/Rural)",
            f"Enter completes/refusals/calls per stratum. % of target and the "
            f"booster flag update live. Booster fires when a stratum is under "
            f"{cfg.get('booster_threshold_pct', 70)}% AND today ≥ "
            f"{cfg.get('booster_decision_date', '')}.")

t = logic.sample_totals(state)
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Completes", f"{t['completes']} / {t['target']}", f"{t['pct']:.0f}%")
c2.metric("Calls placed", t["calls"])
c3.metric("Refusals", t["refusals"])
c4.metric("Strata under target", t["under"])
c5.metric("Boosters triggered", t["boosters"])
st.progress(min(t["pct"] / 100, 1.0))
st.markdown('<hr class="section-rule">', unsafe_allow_html=True)

rows = logic.sample_rows(state)
df = pd.DataFrame([{
    "id": r["id"], "region": r["region"], "type": r["type"], "target": r["target"],
    "completes": r["completes"], "pct": r["pct"], "refusals": r.get("refusals", 0),
    "calls": r.get("calls", 0), "flag": ("🔴 booster" if r["booster"]
             else ("🟠 under" if r["under_threshold"] else "🟢")),
} for r in rows])

edited = st.data_editor(
    df,
    column_config={
        "id": st.column_config.NumberColumn("#", disabled=True, width="small"),
        "region": st.column_config.TextColumn("NUTS-2 region", disabled=True),
        "type": st.column_config.TextColumn("Urban/Rural", disabled=True, width="small"),
        "target": st.column_config.NumberColumn("Target n", disabled=True, width="small"),
        "completes": st.column_config.NumberColumn("Completes", min_value=0, step=1),
        "pct": st.column_config.ProgressColumn("% of target", min_value=0,
                max_value=100, format="%.0f%%"),
        "refusals": st.column_config.NumberColumn("Refusals", min_value=0, step=1),
        "calls": st.column_config.NumberColumn("Calls", min_value=0, step=1),
        "flag": st.column_config.TextColumn("Flag", disabled=True, width="small"),
    },
    column_order=["id", "region", "type", "target", "completes", "pct",
                  "refusals", "calls", "flag"],
    hide_index=True, use_container_width=True, key="sample_editor",
)

if st.button("💾 Save", type="primary"):
    by_id = {int(r["id"]): r for r in edited.to_dict("records")}
    for r in state["sample"]:
        upd = by_id.get(r["id"])
        if upd:
            r["completes"] = int(upd["completes"] or 0)
            r["refusals"] = int(upd["refusals"] or 0)
            r["calls"] = int(upd["calls"] or 0)
    save_state()
    saved_toast()
    st.rerun()
