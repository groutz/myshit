"""Operational logs — Weekly Reports, Fieldwork Daily, Interviewers, QA Log."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from store import get_state, save_state
from ui import page_header, saved_toast, setup

setup("Logs", "🗒️")
state = get_state()
page_header("Operational logs",
            "Working logs you fill in as the project runs. Weekly-report and "
            "interviewer-bench counts surface on their summaries below.")

tabs = st.tabs(["📅 Weekly Reports", "📈 Fieldwork Daily", "🧑‍💼 Interviewers", "🔎 QA Log"])

# ----------------------------------------------------------- Weekly Reports
with tabs[0]:
    cfg = state.get("settings", {})
    st.caption(f"Sent to the client **{cfg.get('report_deadline', 'Monday 14:00 Athens')}**, "
               f"**only during the fieldwork period** "
               f"({cfg.get('fieldwork_start', '')} → {cfg.get('fieldwork_end', '')}).")
    fr = state.get("weekly_reports", [])
    sent = sum(1 for r in fr if r.get("sent"))
    st.metric("Reports sent", f"{sent} / {len(fr)}")
    df = pd.DataFrame(fr)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    e = st.data_editor(
        df,
        column_config={
            "date": st.column_config.DateColumn("Monday", format="DD MMM YYYY", disabled=True),
            "sent": st.column_config.CheckboxColumn("Sent?"),
            "sent_at": st.column_config.TextColumn("Sent at"),
            "highlights": st.column_config.TextColumn("Highlights / KPI", width="large"),
            "link": st.column_config.TextColumn("Link / version"),
        },
        column_order=["date", "sent", "sent_at", "highlights", "link"],
        hide_index=True, use_container_width=True, key="wr_editor",
    )
    if st.button("💾 Save Weekly Reports", type="primary", key="save_wr"):
        e["date"] = e["date"].apply(lambda d: d.strftime("%Y-%m-%d") if pd.notna(d) else "")
        state["weekly_reports"] = e.to_dict("records")
        save_state(); saved_toast(); st.rerun()

# ----------------------------------------------------------- Fieldwork Daily
with tabs[1]:
    fd = pd.DataFrame(state.get("fieldwork_daily", []))
    fd["date"] = pd.to_datetime(fd["date"], errors="coerce")
    e = st.data_editor(
        fd,
        column_config={
            "date": st.column_config.DateColumn("Date", format="DD MMM", disabled=True),
            "day": st.column_config.TextColumn("Day", disabled=True, width="small"),
            "new_completes": st.column_config.NumberColumn("New", min_value=0),
            "cum_completes": st.column_config.NumberColumn("Cumulative", min_value=0),
            "calls": st.column_config.NumberColumn("Calls", min_value=0),
            "coop_rate": st.column_config.NumberColumn("Coop %", min_value=0, max_value=100),
            "refusal_rate": st.column_config.NumberColumn("Refusal %", min_value=0, max_value=100),
            "mean_len": st.column_config.NumberColumn("Mean len (min)", min_value=0),
            "qa_pct": st.column_config.NumberColumn("QA %", min_value=0, max_value=100),
        },
        hide_index=True, use_container_width=True, key="fd_editor",
    )
    if st.button("💾 Save Fieldwork Daily", type="primary", key="save_fd"):
        e["date"] = e["date"].apply(lambda d: d.strftime("%Y-%m-%d") if pd.notna(d) else "")
        state["fieldwork_daily"] = e.to_dict("records")
        save_state(); saved_toast(); st.rerun()

# -------------------------------------------------------------- Interviewers
with tabs[2]:
    iv = state.get("interviewers", [])
    named = [r for r in iv if str(r.get("name", "")).strip()]
    confirmed = sum(1 for r in named if r.get("confirmed"))
    st.metric("Bench", f"{confirmed} confirmed of {len(named)} named")
    e = st.data_editor(
        pd.DataFrame(iv),
        column_config={
            "id": st.column_config.NumberColumn("#", disabled=True, width="small"),
            "name": st.column_config.TextColumn("Name", width="medium"),
            "confirmed": st.column_config.CheckboxColumn("Confirmed (written)?"),
            "conflicts": st.column_config.TextColumn("July conflicts"),
            "retainer": st.column_config.CheckboxColumn("Retainer paid?"),
            "shift": st.column_config.TextColumn("Shift pref", width="small"),
            "notes": st.column_config.TextColumn("Notes", width="medium"),
        },
        column_order=["id", "name", "confirmed", "conflicts", "retainer", "shift", "notes"],
        hide_index=True, use_container_width=True, key="iv_editor",
    )
    if st.button("💾 Save Interviewers", type="primary", key="save_iv"):
        state["interviewers"] = e.to_dict("records")
        save_state(); saved_toast(); st.rerun()

# -------------------------------------------------------------------- QA Log
with tabs[3]:
    ql = state.get("qa_log", [])
    logged = [r for r in ql if str(r.get("interview_id", "")).strip()]
    st.metric("Verifications logged", len(logged))
    e = st.data_editor(
        pd.DataFrame(ql),
        column_config={
            "id": st.column_config.NumberColumn("#", disabled=True, width="small"),
            "date": st.column_config.TextColumn("Date", width="small"),
            "interview_id": st.column_config.TextColumn("Interview ID"),
            "verifier": st.column_config.TextColumn("Verifier"),
            "result": st.column_config.SelectboxColumn(
                "Result", options=["", "Pass", "Fail", "Flag"]),
            "issue_type": st.column_config.TextColumn("Issue type"),
            "notes": st.column_config.TextColumn("Notes", width="large"),
        },
        column_order=["id", "date", "interview_id", "verifier", "result",
                      "issue_type", "notes"],
        hide_index=True, use_container_width=True, key="qa_editor",
        num_rows="dynamic",
    )
    if st.button("💾 Save QA Log", type="primary", key="save_qa"):
        state["qa_log"] = e.to_dict("records")
        save_state(); saved_toast(); st.rerun()
