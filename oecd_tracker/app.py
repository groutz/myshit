"""OECD/INFE 2026 — Greece · PM Tracker — Dashboard (home page).

Run with:  streamlit run app.py   (from inside the oecd_tracker/ folder)

This is the at-a-glance rollup. Everything here is derived live from the data
you enter on the other pages, so ticking a task or typing a number instantly
moves the progress bars, statuses, countdowns and the Upcoming list below.
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

import logic
from store import get_state
from ui import badge, page_header, setup, status_emoji

setup("Dashboard", "📊")
state = get_state()
now = logic.today(state)
meta = state.get("meta", {})
cfg = state.get("settings", {})

page_header(
    "OECD/INFE 2026 — Greece · PM Tracker",
    f"{meta.get('Project', '')}",
)

# --------------------------------------------------------------- headline KPIs
overall = logic.overall_progress(state)
tw_done, tw_total = logic.thisweek_summary(state)
assignment = logic.parse_date(cfg.get("assignment_date"))
kickoff = logic.parse_date(cfg.get("kickoff"))
final_c = logic.parse_date(cfg.get("final_contract"))
final_s = logic.parse_date(cfg.get("final_shadow"))
totals = logic.sample_totals(state)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Overall progress", f"{overall:.0f}%")
c2.metric("This-week tasks", f"{tw_done} / {tw_total}")
c3.metric("Days to kick-off", logic.days_between(now, kickoff))
c4.metric("Days to delivery (contract)", logic.days_between(now, final_c),
          help=f"Shadow delivery: {logic.days_between(now, final_s)} days")
c5.metric("Sample completes", f"{totals['completes']} / {totals['target']}",
          f"{totals['pct']:.0f}% of target")

c6, c7, c8, c9 = st.columns(4)
open_cp = sum(1 for c in state.get("critical_path", [])
              if str(c.get("status", "")).lower() not in ("done", "closed", "ok"))
risks = state.get("risks", [])
high = sum(1 for r in risks if r.get("likelihood") == "High"
           and str(r.get("status", "")).lower() == "open")
med = sum(1 for r in risks if r.get("likelihood") == "Medium"
          and str(r.get("status", "")).lower() == "open")
c6.metric("Days since assignment", logic.days_between(assignment, now))
c7.metric("Open critical-path items", open_cp)
c8.metric("Open risks (High)", high)
c9.metric("Strata triggering booster", totals["boosters"],
          help=f"{totals['under']} strata under "
               f"{cfg.get('booster_threshold_pct', 70)}% of target")

# ---------------------------------------------------------- alerts / warnings
alerts = []
for m in logic.milestone_rows(state):
    if m["status"] == logic.STATUS_SLIPPING:
        alerts.append(f"🔴 **{m['name']}** is past its contract date and not complete.")
    elif m["status"] == logic.STATUS_AT_RISK:
        alerts.append(f"🟠 **{m['name']}** is past its shadow date "
                      f"({m['days_to_shadow']:+d}d) — early warning.")
if totals["boosters"]:
    alerts.append(f"🔴 **{totals['boosters']} strata** are under target inside the "
                  "booster window — trigger a booster.")
overdue = [t for t in state.get("this_week", [])
           if not t.get("done") and (d := logic.parse_date(t.get("due"))) and d < now]
if overdue:
    alerts.append(f"🟠 **{len(overdue)} This-Week task(s)** overdue.")

if alerts:
    with st.container(border=True):
        st.markdown("#### ⚠️ Attention")
        for a in alerts:
            st.markdown(a)

st.markdown('<hr class="section-rule">', unsafe_allow_html=True)

# ----------------------------------------------------------------- milestones
left, right = st.columns([1.15, 1])

with left:
    st.markdown("#### Milestones — run to the Shadow date")
    for m in logic.milestone_rows(state):
        bar, lab = st.columns([3, 2])
        with bar:
            st.markdown(f"**{m['name']}**", help=m.get("why", ""))
            st.progress(min(int(m.get("pct", 0)), 100))
        with lab:
            dts = m["days_to_shadow"]
            dts_txt = f"{dts:+d}d to shadow" if dts is not None else ""
            st.markdown(f"{badge(m['status'])} &nbsp; "
                        f"<span class='kpi-note'>{m.get('pct', 0):.0f}% · {dts_txt}</span>",
                        unsafe_allow_html=True)

with right:
    st.markdown("#### Phase progress (P1 → P6)")
    rows = logic.phase_rows(state)
    fig = go.Figure(go.Bar(
        x=[r["pct"] for r in rows],
        y=[f"{r['id']} · {r['name']}" for r in rows],
        orientation="h",
        marker_color=[logic.STATUS_COLOUR.get(r["status"], "#9aa0a6") for r in rows],
        text=[f"{r['pct']:.0f}%" for r in rows],
        textposition="outside",
        hovertext=[f"{r['n_done']}/{r['n_sub']} sub-tasks done · {r['status']}"
                   for r in rows],
    ))
    fig.update_layout(
        xaxis=dict(range=[0, 100], title="% complete", ticksuffix="%"),
        yaxis=dict(autorange="reversed"),
        height=300, margin=dict(l=0, r=20, t=10, b=10),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)

st.markdown('<hr class="section-rule">', unsafe_allow_html=True)

# ------------------------------------------------------------- upcoming tasks
st.markdown("#### 🔜 Upcoming / next actions")
st.caption("Auto-built from incomplete This-Week tasks and unfinished phase "
           "sub-tasks, soonest first. Complete items on their pages and they "
           "drop off here automatically.")

up = logic.upcoming_tasks(state, limit=12)
if not up:
    st.success("Nothing outstanding — every tracked task is complete. 🎉")
else:
    for item in up:
        due = item["due"].strftime("%a %d %b") if item["due"] else "—"
        flag = "🔴 " if item["overdue"] else ""
        pct = f" · {item['pct']:.0f}%" if item["pct"] else ""
        cols = st.columns([0.13, 0.62, 0.12, 0.13])
        cols[0].markdown(f"`{item['source']}`")
        cols[1].markdown(f"{flag}{item['what']}")
        cols[2].markdown(f"<span class='kpi-note'>{item['owner']}</span>",
                         unsafe_allow_html=True)
        cols[3].markdown(f"<span class='kpi-note'>{due}{pct}</span>",
                         unsafe_allow_html=True)

st.markdown('<hr class="section-rule">', unsafe_allow_html=True)
st.caption(f"Today (live): **{now:%A %d %B %Y}**  ·  "
           f"Source of truth: this app's `state.json` (seeded from the Excel). "
           f"Use the sidebar pages to enter status; the dashboard re-rolls on every edit.")
