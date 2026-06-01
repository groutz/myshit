"""OECD/INFE 2026 — Greece · PM Tracker — Dashboard (home page).

Run with:  streamlit run app.py   (from inside the oecd_tracker/ folder)

At-a-glance rollup, fully derived from the tasks you report on the Weekly
To-Do page: progress, milestone/phase status, open critical-paths & risks
(click the numbers), team workload and the next actions.
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

import logic
from store import get_state
from ui import badge, page_header, setup

setup("Dashboard", "📊")
state = get_state()
now = logic.today(state)
meta = state.get("meta", {})
cfg = state.get("settings", {})

page_header("OECD/INFE 2026 — Greece · PM Tracker", meta.get("Project", ""))

# ----------------------------------------------------- overall progress bar
overall = logic.overall_progress(state)
final_s = logic.parse_date(cfg.get("final_shadow"))
final_c = logic.parse_date(cfg.get("final_contract"))
ms = logic.milestone_rows(state)
on_track = sum(1 for m in ms if m["status"] in (logic.STATUS_DONE, logic.STATUS_ON_TRACK))
oc = logic.open_counts(state)
totals = logic.sample_totals(state)

st.markdown(f"#### Overall project progress — **{overall:.0f}%**")
st.progress(min(overall / 100, 1.0))

# --------------------------------------------------------------- key metrics
c1, c2, c3, c4 = st.columns(4)
c1.metric("Milestones on track", f"{on_track} / {len(ms)}")
c2.metric("Days to delivery (shadow)", logic.days_between(now, final_s),
          help=f"Contract deadline: {logic.days_between(now, final_c)} days")
c3.metric("Sample completes", f"{totals['completes']} / {totals['target']}",
          f"{totals['pct']:.0f}% of target")
c4.metric("Booster strata", totals["boosters"],
          help=f"{totals['under']} strata under "
               f"{cfg.get('booster_threshold_pct', 70)}% of target")

# clickable open critical-paths / risks (popover — no navigation needed)
p1, p2, _ = st.columns([1, 1, 2])
with p1:
    with st.popover(f"🧭 Open critical-path items: {oc['cp_open']}",
                    use_container_width=True):
        st.markdown("**Hidden critical path — what's gating the project now**")
        for c in oc["cp"]:
            if not c["open"]:
                continue
            st.markdown(f"{badge(c['status'])} &nbsp; **{c['item']}** "
                        f"<span class='kpi-note'>· {c['owner']} · {c['pct']:.0f}%</span>",
                        unsafe_allow_html=True)
            st.caption(c["why"])
        if oc["cp_open"] == 0:
            st.success("All critical-path items closed.")
with p2:
    with st.popover(f"⚠️ Open risks: {oc['risk_open']}  "
                    f"(High: {oc['risk_high_open']})", use_container_width=True):
        st.markdown("**Risk watchlist (internal)**")
        for r in oc["risks"]:
            if not r["open"]:
                continue
            st.markdown(f"{badge('Open')} **{r['risk']}** "
                        f"<span class='kpi-note'>· L:{r['likelihood']} / "
                        f"I:{r['impact']} · {r['auto_status']}</span>",
                        unsafe_allow_html=True)
            st.caption(f"Mitigation: {r['mitigation']}")
        if oc["risk_open"] == 0:
            st.success("No open risks.")

# ---------------------------------------------------------- attention panel
alerts = []
for m in ms:
    if m["status"] == logic.STATUS_SLIPPING:
        alerts.append(f"🔴 **{m['name']}** — {m['pct']:.0f}% and past its contract date.")
    elif m["status"] == logic.STATUS_AT_RISK:
        alerts.append(f"🟠 **{m['name']}** — {m['pct']:.0f}%, past its shadow date "
                      f"({m['days_to_shadow']:+d}d).")
if totals["boosters"]:
    alerts.append(f"🔴 **{totals['boosters']} strata** under target inside the "
                  "booster window — trigger a booster.")
carried = logic.weekly_view(state)["carried"]
if carried:
    alerts.append(f"🟠 **{len(carried)} task(s)** overdue and carried over — "
                  "see Weekly To-Do.")

if alerts:
    with st.container(border=True):
        st.markdown("#### ⚠️ Attention")
        for a in alerts:
            st.markdown(a)
else:
    st.success("✅ Nothing flagged — every milestone is on track and no tasks overdue.")

st.markdown('<hr class="section-rule">', unsafe_allow_html=True)

# ----------------------------------------------------- milestones + phases
left, right = st.columns([1.15, 1])
with left:
    st.markdown("#### Milestones (run to Shadow)")
    for m in ms:
        bar, lab = st.columns([3, 2])
        with bar:
            st.markdown(f"**{m['name']}**", help=m.get("why", ""))
            st.progress(min(int(m.get("pct", 0)), 100))
        with lab:
            dts = m["days_to_shadow"]
            dts_txt = f"{dts:+d}d to shadow" if dts is not None else ""
            st.markdown(f"{badge(m['status'])} &nbsp;"
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
        text=[f"{r['pct']:.0f}%" for r in rows], textposition="outside",
        hovertext=[f"{r['n_done']}/{r['n_sub']} sub-tasks · {r['status']}" for r in rows],
    ))
    fig.update_layout(
        xaxis=dict(range=[0, 100], title="% complete", ticksuffix="%"),
        yaxis=dict(autorange="reversed"), height=300,
        margin=dict(l=0, r=20, t=10, b=10),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

st.markdown('<hr class="section-rule">', unsafe_allow_html=True)

# ----------------------------------------------------- team workload
st.markdown("#### 👥 Team — key open tasks, with assign-by dates")
st.caption("'Assign by' is back-calculated from each task's due date minus the "
           "estimated effort, so work starts early enough to finish on time.")
workload = logic.member_workload(state)
if not workload:
    st.success("No open tasks assigned.")
else:
    cols = st.columns(2)
    for i, (owner, items) in enumerate(workload.items()):
        with cols[i % 2]:
            with st.container(border=True):
                st.markdown(f"**{owner}** · {len(items)} open")
                for t in items[:5]:
                    due = t["due"].strftime("%d %b") if t["due"] else "—"
                    ab = t["assign_by"].strftime("%d %b") if t["assign_by"] else "—"
                    warn = "🔴 " if t["assign_overdue"] else ""
                    st.markdown(
                        f"- {t['title'][:70]}  \n"
                        f"<span class='kpi-note'>`{t['group']}` · "
                        f"{warn}assign by **{ab}** · due {due} · {t['pct']:.0f}%</span>",
                        unsafe_allow_html=True)

st.markdown('<hr class="section-rule">', unsafe_allow_html=True)
st.caption(f"Today (live): **{now:%A %d %B %Y}**  ·  Week "
           f"{logic.project_week(state, now)} from assignment. Report progress "
           f"on **Weekly To-Do**; this dashboard re-rolls on every save.")
