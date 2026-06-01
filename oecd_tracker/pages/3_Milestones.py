"""Milestones — % complete + live dates → status & days-to-shadow countdown."""

from __future__ import annotations

import pandas as pd
import streamlit as st

import logic
from store import get_state, save_state
from ui import badge, page_header, saved_toast, setup

setup("Milestones", "🎯")
state = get_state()
page_header("Milestones — Shadow vs Contract",
            "Run to the Shadow column (internal trigger ~7–10 days ahead). The "
            "Ministry only ever sees the Contract column. Status auto-derives "
            "from % complete vs today's date.")

rows = logic.milestone_rows(state)

# editable %; dates shown read-only here (change them in Settings if needed)
df = pd.DataFrame([{
    "id": r["id"], "name": r["name"], "contract": r["contract"],
    "shadow": r["shadow"], "pct": r["pct"],
} for r in state["milestones"]])
df["contract"] = pd.to_datetime(df["contract"], errors="coerce")
df["shadow"] = pd.to_datetime(df["shadow"], errors="coerce")

edited = st.data_editor(
    df,
    column_config={
        "id": st.column_config.NumberColumn("#", disabled=True, width="small"),
        "name": st.column_config.TextColumn("Milestone", width="large", disabled=True),
        "contract": st.column_config.DateColumn("Contract", format="DD MMM YYYY"),
        "shadow": st.column_config.DateColumn("Shadow", format="DD MMM YYYY"),
        "pct": st.column_config.NumberColumn("% complete", min_value=0,
                                             max_value=100, step=5),
    },
    column_order=["id", "name", "contract", "shadow", "pct"],
    hide_index=True, use_container_width=True, key="ms_editor",
)

if st.button("💾 Save", type="primary"):
    out = edited.copy()
    for col in ("contract", "shadow"):
        out[col] = out[col].apply(lambda d: d.strftime("%Y-%m-%d") if pd.notna(d) else "")
    by_id = {r["id"]: r for r in out.to_dict("records")}
    for m in state["milestones"]:
        upd = by_id.get(m["id"])
        if upd:
            m.update({"contract": upd["contract"], "shadow": upd["shadow"],
                      "pct": int(upd["pct"] or 0)})
    save_state()
    saved_toast()
    st.rerun()

st.markdown('<hr class="section-rule">', unsafe_allow_html=True)
st.markdown("#### Status & countdown")
for r in logic.milestone_rows(state):
    cols = st.columns([2.6, 1, 1, 1.4])
    cols[0].markdown(f"**{r['name']}**", help=r.get("why", ""))
    cols[1].markdown(badge(r["status"]), unsafe_allow_html=True)
    dts = r["days_to_shadow"]
    dtc = r["days_to_contract"]
    cols[2].markdown(f"<span class='kpi-note'>{dts:+d}d → shadow</span>"
                     if dts is not None else "—", unsafe_allow_html=True)
    cols[3].markdown(f"<span class='kpi-note'>{dtc:+d}d → contract · {r['pct']:.0f}%</span>"
                     if dtc is not None else "—", unsafe_allow_html=True)
