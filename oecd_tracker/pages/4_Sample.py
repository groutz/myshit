"""Sample tracker — 26 strata. Daily Excel upload from Survey Solutions, or
enter completes → % of target + booster flags."""

from __future__ import annotations

import pandas as pd
import streamlit as st

import logic
import sample_io
from store import get_state, save_state
from ui import page_header, saved_toast, setup

setup("Sample", "📞")
state = get_state()
cfg = state.get("settings", {})
page_header("Sample tracker — 26 strata (NUTS-2 × Urban/Rural)",
            f"Update daily by uploading Sakis's Survey Solutions file, or edit "
            f"the table directly. Booster fires when a stratum is under "
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

# ---------------------------------------------------- daily upload workflow
st.markdown("#### 📤 Daily update — upload Sakis's raw responses file")
st.caption("One row per completed interview (all interviews so far). The app "
           "counts rows per region × urbanity stratum. Strata absent from the "
           "file are treated as 0, since the file is the full cumulative set.")
dl, up = st.columns([1, 2])
with dl:
    st.download_button(
        "⬇️ Template for Sakis (.xlsx)", data=sample_io.build_template(state),
        file_name="Sample_Daily_Responses_Template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        help="Defines the columns to keep (Interview ID, Region, Urban/Rural, "
             "optional Status) and lists the valid region/urbanity values.")
with up:
    uploaded = st.file_uploader("Upload the responses file (.xlsx or .csv)",
                                type=["xlsx", "xls", "csv"], key="sample_upload")

if uploaded is not None:
    try:
        result = sample_io.parse_upload(uploaded, state)
    except Exception as exc:  # surface a friendly message rather than a trace
        st.error(f"Couldn't read that file: {exc}")
    else:
        note = f"Detected format: **{result['mode']}** · {result['counted']} completes counted"
        if result["excluded"]:
            note += (f" · {result['excluded']} row(s) excluded "
                     "(incomplete or no region)")
        st.caption(note)
        if result["warnings"]:
            with st.expander(f"⚠️ {len(result['warnings'])} row(s) not matched"):
                for w in result["warnings"][:50]:
                    st.write("- " + w)
        prev = pd.DataFrame([{
            "Region": u["region"], "Urban/Rural": u["type"],
            "Completes (now)": u["old_completes"],
            "Completes (new)": u["new_completes"],
            "Δ": u["new_completes"] - u["old_completes"],
        } for u in result["updates"]])
        changed = prev[prev["Δ"] != 0]
        st.markdown(f"**Preview** — {len(changed)} strata change. "
                    f"New total completes: **{result['counted']}**")
        st.dataframe(changed if not changed.empty else prev,
                     hide_index=True, use_container_width=True)
        if st.button("✅ Apply this update", type="primary"):
            sample_io.apply_updates(state, result["updates"])
            save_state()
            saved_toast()
            st.rerun()

st.markdown('<hr class="section-rule">', unsafe_allow_html=True)
st.markdown("#### Or edit the table directly")

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
