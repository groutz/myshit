"""Pending Tasks — the one place you report progress.

Top: a contractual-deliverables submission checklist. Ticking a deliverable
completes all of its sub-tasks at once (so it clears from Attention).

Below: every still-open task due by the end of this project week (plus any
carried over from earlier weeks), categorised by due date -> team member ->
importance. Each task is a tick-box (binary) or a 0-100% slider.
"""

from __future__ import annotations

import streamlit as st

import logic
from store import get_state, save_state
from ui import badge, page_header, saved_toast, setup

setup("Pending Tasks", "🗓️")
state = get_state()
view = logic.weekly_view(state)
cw = view["current_week"]
start, end = view["range"]

page_header(
    f"Pending Tasks — Week {cw} ({start:%d %b} – {end:%d %b})",
    "Report only these; the rest of the app fills itself in. Tasks are due to "
    "their internal (shadow) dates and ordered by due date, then owner, then "
    "importance.",
)

ov = logic.overall_progress(state)
c1, c2, c3 = st.columns([1, 1, 2])
c1.metric("Overall project progress", f"{ov:.0f}%")
c2.metric("Pending now", len(view["pending"]))
c3.metric("Carried over (overdue)", len(view["carried"]))
st.progress(min(ov / 100, 1.0))

# ---------------------------------------------------- deliverables checklist
st.markdown('<hr class="section-rule">', unsafe_allow_html=True)
st.markdown("#### 📦 Contractual deliverables — submission checklist")
st.caption("Tick a deliverable when it's been submitted. This completes ALL of "
           "its sub-tasks and marks the milestone done. Untick to reopen them.")

ms = logic.milestone_rows(state)
phases = state.get("phases", [])
deliverable_state: dict[str, tuple] = {}
for idx, m in enumerate(ms):
    pid = phases[idx]["id"] if idx < len(phases) else None
    if pid is None:
        continue
    submitted_now = m["pct"] >= 100
    cols = st.columns([0.12, 0.66, 0.22])
    val = cols[0].checkbox("Submitted", value=submitted_now, key=f"deliv_{pid}",
                           label_visibility="collapsed")
    deliverable_state[pid] = (val, submitted_now)
    cols[1].markdown(f"**{m['name']}**")
    cols[1].caption(f"Contract date: {logic.parse_date(m['contract']):%d %b %Y}")
    cols[2].markdown(badge(m["status"]) +
                     f" <span class='kpi-note'>{m['pct']:.0f}%</span>",
                     unsafe_allow_html=True)

if st.button("💾 Save deliverables", type="primary", key="save_deliv"):
    for pid, (val, was) in deliverable_state.items():
        if val != was:
            logic.set_phase_complete(state, pid, val)
    save_state()
    saved_toast()
    st.rerun()

# ----------------------------------------------------------- pending tasks
st.markdown('<hr class="section-rule">', unsafe_allow_html=True)
st.markdown("#### 📋 Pending tasks")

pending = view["pending"]
if not pending:
    st.success("Nothing pending — you're clear through the end of this week. 🎉")

now = logic.today(state)
collected: dict[str, tuple] = {}
last_due = object()

for t in pending:
    # date category header
    if t["due"] != last_due:
        last_due = t["due"]
        label = t["due"].strftime("%A %d %b") if t["due"] else "No due date"
        if t["due"] and t["due"] < now:
            label += "  ·  ⚠️ overdue"
        st.markdown(f"**{label}**")

    due = t["due"].strftime("%d %b") if t["due"] else "—"
    assign = t["assign_by"].strftime("%d %b") if t["assign_by"] else "—"
    flag = "🔴 " if t["overdue"] else ""
    imp = "★" * int(t.get("weight", 1))
    col_ctrl, col_body = st.columns([0.26, 0.74])
    key = f"pend_{t['id']}"
    with col_ctrl:
        if t["type"] == "binary":
            v = st.checkbox("Done", value=t["pct"] >= 100, key=key)
            collected[t["id"]] = (t["ref"], 100.0 if v else 0.0)
        else:
            v = st.slider("%", 0, 100, int(t["pct"]), step=5, key=key,
                          label_visibility="collapsed")
            collected[t["id"]] = (t["ref"], float(v))
    with col_body:
        st.markdown(f"{flag}**{t['title']}**")
        st.caption(f"`{t['group']}` · {t['owner'] or '—'} · importance {imp} · "
                   f"assign by {assign} · due {due}")
    st.divider()

if pending and st.button("💾 Save progress", type="primary", key="save_pend"):
    for _id, (ref, pct) in collected.items():
        logic.set_task_pct(state, ref, pct)
    save_state()
    saved_toast()
    st.rerun()

# read-only look-ahead
with st.expander(f"🔭 Upcoming weeks ({len(view['upcoming'])} open tasks ahead)"):
    if not view["upcoming"]:
        st.write("Nothing scheduled beyond this week.")
    for t in view["upcoming"]:
        due = t["due"].strftime("%a %d %b") if t["due"] else "—"
        st.markdown(f"- **W{t['week']}** · `{t['group']}` · {t['title']}  "
                    f"<span class='kpi-note'>({t['owner']} · due {due})</span>",
                    unsafe_allow_html=True)
