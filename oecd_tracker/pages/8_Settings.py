"""Settings — key dates, targets, today-override, export/import, reset."""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st

import logic
from store import backend_label, get_state, reset_state, save_state
from ui import page_header, saved_toast, setup


def _s(v) -> str:
    """Clean a possibly-NaN data_editor cell to a string."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return str(v).strip()


def _i(v, default: int) -> int:
    try:
        if v is None or pd.isna(v):
            return default
        return int(v)
    except (TypeError, ValueError):
        return default


def _fd(v) -> str:
    return v.strftime("%Y-%m-%d") if (v is not None and not pd.isna(v)) else ""

setup("Settings", "⚙️")
state = get_state()
cfg = state.setdefault("settings", {})
page_header("Settings",
            "Change the project parameters that everything else reads from. "
            "'Today override' lets you run what-if scenarios against a fixed date.")

# ---------------------------------------------------------------- today / dates
st.markdown("#### Dates & clock")
c1, c2 = st.columns(2)
with c1:
    use_override = st.checkbox(
        "Override 'today' (what-if)", value=bool(cfg.get("today_override")))
    if use_override:
        d = logic.parse_date(cfg.get("today_override")) or logic.today(state)
        cfg["today_override"] = st.date_input("Today =", value=d).strftime("%Y-%m-%d")
    else:
        cfg["today_override"] = None
    st.caption(f"Live today resolves to **{logic.today(state):%d %b %Y}**.")
with c2:
    cfg["assignment_date"] = st.text_input("Assignment date", cfg.get("assignment_date", ""))
    cfg["kickoff"] = st.text_input("Kick-off", cfg.get("kickoff", ""))

c3, c4 = st.columns(2)
cfg["final_contract"] = c3.text_input("Final delivery (contract)", cfg.get("final_contract", ""))
cfg["final_shadow"] = c4.text_input("Final delivery (shadow)", cfg.get("final_shadow", ""))

# ---------------------------------------------------------------------- targets
st.markdown("#### Targets")
c5, c6, c7 = st.columns(3)
cfg["sample_target"] = c5.number_input(
    "Sample target (n)", min_value=0, value=int(cfg.get("sample_target", 1000)), step=50)
cfg["booster_threshold_pct"] = c6.number_input(
    "Booster threshold (%)", min_value=0, max_value=100,
    value=int(cfg.get("booster_threshold_pct", 70)))
cfg["booster_decision_date"] = c7.text_input(
    "Booster decision date", cfg.get("booster_decision_date", ""))
cfg["qa_target_pct"] = c5.number_input(
    "QA verification target (%)", min_value=0.0, max_value=100.0,
    value=float(cfg.get("qa_target_pct", 12.5)), step=0.5)

if st.button("💾 Save settings", type="primary"):
    save_state()
    saved_toast()
    st.rerun()

st.markdown('<hr class="section-rule">', unsafe_allow_html=True)

# =====================================================================
# PROJECT SET-UP — restructure milestones, phases, tasks, owners, dates
# =====================================================================
st.markdown("## 🛠️ Project set-up")
st.caption("Reshape the project itself. Changes here flow through the whole app "
           "— progress, milestones, the dashboard, pending tasks and the team "
           "workload all recompute from this. Each **stage** is one milestone "
           "plus the phase of work behind it. Add rows with the ＋ at the "
           "bottom of a table, or tick a row and use ⌫ to delete.")

setup_tabs = st.tabs(["🎯 Stages (milestones & phases)", "✅ Tasks", "🗒️ Prep tasks"])

# ----------------------------------------------------------- Stages
with setup_tabs[0]:
    st.caption("Rename, re-date, add or remove stages. Deleting a stage removes "
               "its phase and all its tasks. Stage IDs are assigned automatically "
               "for new rows. Edit dates run-to-shadow as usual.")
    phases = state.get("phases", [])
    miles = state.get("milestones", [])
    stage_rows = []
    for i, p in enumerate(phases):
        m = miles[i] if i < len(miles) else {}
        stage_rows.append({
            "id": p["id"], "milestone": m.get("name", ""), "phase": p.get("name", ""),
            "window": p.get("window", ""),
            "contract": logic.parse_date(m.get("contract")),
            "shadow": logic.parse_date(m.get("shadow")),
        })
    sdf = pd.DataFrame(stage_rows, columns=["id", "milestone", "phase", "window",
                                            "contract", "shadow"])
    sed = st.data_editor(
        sdf, num_rows="dynamic", hide_index=True, use_container_width=True,
        key="stages_editor",
        column_config={
            "id": st.column_config.TextColumn("Stage", disabled=True, width="small"),
            "milestone": st.column_config.TextColumn("Milestone name", width="medium"),
            "phase": st.column_config.TextColumn("Phase (work) name", width="medium"),
            "window": st.column_config.TextColumn("Window"),
            "contract": st.column_config.DateColumn("Contract date", format="DD MMM YYYY"),
            "shadow": st.column_config.DateColumn("Shadow date", format="DD MMM YYYY"),
        })
    if st.button("💾 Save stages", type="primary", key="save_stages"):
        old_phases = {p["id"]: p for p in phases}
        old_mile_by_pid = {p["id"]: (miles[i] if i < len(miles) else {})
                           for i, p in enumerate(phases)}
        used = [int(p["id"][1:]) for p in phases if p["id"][1:].isdigit()]
        next_n = max(used) if used else 0
        new_phases, new_miles, mid = [], [], 1
        for r in sed.to_dict("records"):
            if not (_s(r.get("milestone")) or _s(r.get("phase"))):
                continue
            pid = _s(r.get("id"))
            if not pid:
                next_n += 1
                pid = f"P{next_n}"
            ph = old_phases.get(pid, {"id": pid, "subtasks": []})
            ph["id"] = pid
            ph["name"] = _s(r.get("phase")) or pid
            ph["window"] = _s(r.get("window"))
            new_phases.append(ph)
            oldm = old_mile_by_pid.get(pid, {})
            new_miles.append({"id": mid, "name": _s(r.get("milestone")) or pid,
                              "contract": _fd(r.get("contract")),
                              "shadow": _fd(r.get("shadow")), "why": oldm.get("why", "")})
            mid += 1
        state["phases"] = new_phases
        state["milestones"] = new_miles
        save_state(); saved_toast(); st.rerun()

# ----------------------------------------------------------- Tasks
with setup_tabs[1]:
    st.caption("Add, rename, reassign, re-date or delete tasks. 'Stage' picks "
               "which milestone/phase a task belongs to (save Stages first if you "
               "added one). 'Assign by' is recomputed from due − effort. Reported "
               "% is preserved for existing tasks.")
    phase_ids = [p["id"] for p in state.get("phases", [])]
    trows = []
    for p in state.get("phases", []):
        for s in p.get("subtasks", []):
            trows.append({
                "phase": p["id"], "id": s.get("id", ""), "task": s.get("task", ""),
                "owner": s.get("owner", ""), "type": s.get("type", "percent"),
                "weight": s.get("weight", 1), "effort_days": s.get("effort_days", 1),
                "due": logic.parse_date(s.get("due")), "notes": s.get("notes", ""),
            })
    tdf = pd.DataFrame(trows, columns=["phase", "id", "task", "owner", "type",
                                       "weight", "effort_days", "due", "notes"])
    ted = st.data_editor(
        tdf, num_rows="dynamic", hide_index=True, use_container_width=True,
        key="tasks_editor",
        column_config={
            "phase": st.column_config.SelectboxColumn("Stage", options=phase_ids,
                                                      required=True, width="small"),
            "id": st.column_config.TextColumn("ID", disabled=True, width="small"),
            "task": st.column_config.TextColumn("Task / sub-task", width="large"),
            "owner": st.column_config.TextColumn("Owner"),
            "type": st.column_config.SelectboxColumn("Type", options=["percent", "binary"]),
            "weight": st.column_config.NumberColumn("Weight", min_value=1, max_value=5, step=1),
            "effort_days": st.column_config.NumberColumn("Effort (d)", min_value=0, step=1),
            "due": st.column_config.DateColumn("Due (shadow)", format="DD MMM YYYY"),
            "notes": st.column_config.TextColumn("Notes"),
        })
    if st.button("💾 Save tasks", type="primary", key="save_tasks"):
        old_sub = {s.get("id"): s for p in state["phases"] for s in p.get("subtasks", [])}
        by_pid = {p["id"]: p for p in state["phases"]}
        counters = {}
        for p in state["phases"]:
            nums = [int(str(s.get("id", "")).split("-")[-1])
                    for s in p.get("subtasks", [])
                    if str(s.get("id", "")).split("-")[-1].isdigit()]
            counters[p["id"]] = max(nums) if nums else 0
            p["subtasks"] = []
        for r in ted.to_dict("records"):
            pid = _s(r.get("phase"))
            if pid not in by_pid or not _s(r.get("task")):
                continue
            sid = _s(r.get("id"))
            if not sid:
                counters[pid] = counters.get(pid, 0) + 1
                sid = f"{pid}-{counters[pid]}"
            eff = _i(r.get("effort_days"), 1)
            due = _fd(r.get("due"))
            by_pid[pid]["subtasks"].append({
                "id": sid, "task": _s(r.get("task")), "owner": _s(r.get("owner")),
                "type": _s(r.get("type")) or "percent", "weight": _i(r.get("weight"), 1),
                "effort_days": eff, "due": due,
                "assign_by": logic.assign_by_date(due, eff, state),
                "notes": _s(r.get("notes")), "pct": old_sub.get(sid, {}).get("pct", 0),
            })
        save_state(); saved_toast(); st.rerun()

# ----------------------------------------------------------- Prep tasks
with setup_tabs[2]:
    st.caption("Pre-kickoff prep tasks (binary). Add, rename, reassign, re-date "
               "or delete.")
    prows = [{"id": t["id"], "action": t.get("action", ""), "owner": t.get("owner", ""),
              "due": logic.parse_date(t.get("due")), "done": bool(t.get("done")),
              "notes": t.get("notes", "")} for t in state.get("this_week", [])]
    pdf = pd.DataFrame(prows, columns=["id", "action", "owner", "due", "done", "notes"])
    ped = st.data_editor(
        pdf, num_rows="dynamic", hide_index=True, use_container_width=True,
        key="prep_editor",
        column_config={
            "id": st.column_config.NumberColumn("#", disabled=True, width="small"),
            "action": st.column_config.TextColumn("Task", width="large"),
            "owner": st.column_config.TextColumn("Owner"),
            "due": st.column_config.DateColumn("Due", format="DD MMM YYYY"),
            "done": st.column_config.CheckboxColumn("Done?"),
            "notes": st.column_config.TextColumn("Notes"),
        })
    if st.button("💾 Save prep tasks", type="primary", key="save_prep"):
        old_prep = {t["id"]: t for t in state.get("this_week", [])}
        used = [int(t["id"]) for t in state.get("this_week", []) if str(t["id"]).isdigit()]
        next_id = max(used) if used else 0
        new_prep = []
        for r in ped.to_dict("records"):
            if not _s(r.get("action")):
                continue
            tid = _i(r.get("id"), 0)
            if not tid:
                next_id += 1
                tid = next_id
            due = _fd(r.get("due"))
            new_prep.append({
                "id": tid, "action": _s(r.get("action")), "owner": _s(r.get("owner")),
                "due": due, "done": bool(r.get("done")), "notes": _s(r.get("notes")),
                "type": "binary", "weight": old_prep.get(tid, {}).get("weight", 1),
                "effort_days": 1, "assign_by": logic.assign_by_date(due, 1, state),
            })
        state["this_week"] = new_prep
        save_state(); saved_toast(); st.rerun()

st.markdown('<hr class="section-rule">', unsafe_allow_html=True)

# ----------------------------------------------------------- backup / restore
st.markdown("#### Backup & restore")
c8, c9 = st.columns(2)
with c8:
    st.download_button(
        "⬇️ Export all data (JSON)",
        data=json.dumps(state, ensure_ascii=False, indent=2),
        file_name="oecd_tracker_state.json", mime="application/json")
    st.caption("A full snapshot you can archive or move to another machine.")
with c9:
    up = st.file_uploader("⬆️ Import a JSON snapshot", type="json")
    if up is not None and st.button("Load this snapshot"):
        st.session_state["state"] = json.load(up)
        save_state()
        st.success("Snapshot loaded.")
        st.rerun()

st.markdown('<hr class="section-rule">', unsafe_allow_html=True)
st.markdown("#### Danger zone")
st.caption(f"Storage backend: **{backend_label()}**")
if st.button("♻️ Reset everything to the original Excel data"):
    reset_state()
    st.warning("All edits discarded — reseeded from the original workbook.")
    st.rerun()
