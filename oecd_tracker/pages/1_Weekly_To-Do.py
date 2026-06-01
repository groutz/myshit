"""Weekly To-Do — the one place you report progress.

Shows this project-week's tasks plus anything overdue and carried over from
earlier weeks. Each task is either a tick-box (binary) or a 0–100% slider.
Saving here re-rolls phases, milestones, critical paths and risks automatically.
"""

from __future__ import annotations

import streamlit as st

import logic
from store import get_state, save_state
from ui import page_header, saved_toast, setup

setup("Weekly To-Do", "🗓️")
state = get_state()
view = logic.weekly_view(state)
cw = view["current_week"]
start, end = view["range"]

page_header(
    f"Weekly To-Do — Week {cw} ({start:%d %b} – {end:%d %b})",
    "Report only these tasks; the rest of the app fills itself in. Tasks are "
    "scheduled to their internal (shadow) due dates. Tick the box or drag the "
    "slider, then Save.",
)

ov = logic.overall_progress(state)
c1, c2, c3 = st.columns([1, 1, 2])
c1.metric("Overall project progress", f"{ov:.0f}%")
c2.metric("Open this week", f"{sum(1 for t in view['this_week'] if t['pct'] < 100)}"
          f" / {len(view['this_week'])}")
c3.metric("Carried over (overdue)", len(view["carried"]))
st.progress(min(ov / 100, 1.0))
st.markdown('<hr class="section-rule">', unsafe_allow_html=True)

# collected widget values -> (ref, pct)
pending: dict[str, tuple] = {}


def render_task(t: dict, key_prefix: str) -> None:
    tag = t["group"]
    due = t["due"].strftime("%a %d %b") if t["due"] else "—"
    assign = t["assign_by"].strftime("%d %b") if t["assign_by"] else "—"
    now = logic.today(state)
    flag = "🔴 " if t["overdue"] else ""
    meta = (f"`{tag}` · {t['owner'] or '—'} · due **{due}** · "
            f"assign by {assign}")

    col_ctrl, col_body = st.columns([0.28, 0.72])
    key = f"{key_prefix}_{t['id']}"
    with col_ctrl:
        if t["type"] == "binary":
            val = st.checkbox("Done", value=t["pct"] >= 100, key=key)
            pending[t["id"]] = (t["ref"], 100.0 if val else 0.0)
        else:
            val = st.slider("% complete", 0, 100, int(t["pct"]), step=5,
                            key=key, label_visibility="collapsed")
            pending[t["id"]] = (t["ref"], float(val))
    with col_body:
        st.markdown(f"{flag}**{t['title']}**")
        st.caption(meta)


if view["carried"]:
    st.markdown("#### ⚠️ Carried over from earlier weeks")
    st.caption("Overdue and still open — clear these first.")
    for t in view["carried"]:
        render_task(t, "carry")
        st.divider()

st.markdown(f"#### This week (Week {cw})")
if not view["this_week"]:
    st.info("No tasks are scheduled to land this week.")
else:
    for t in view["this_week"]:
        render_task(t, "week")
        st.divider()

if st.button("💾 Save progress", type="primary"):
    for _id, (ref, pct) in pending.items():
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
