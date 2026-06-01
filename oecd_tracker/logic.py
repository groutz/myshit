"""Derived metrics for the PM Tracker.

Tasks are the single source of truth: every phase sub-task (and the pre-kickoff
prep tasks) carries a weight, a type (binary / percent), a shadow-based due date
and an effort estimate. From those we derive phase %, milestone %, the weekly
to-do buckets, per-owner workloads, and the status of critical-path items and
risks — so the user only ever reports task progress and the rest fills in.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

# Status vocabulary mapped to the README colour code.
STATUS_DONE = "Done"
STATUS_ON_TRACK = "On track"
STATUS_AT_RISK = "At risk"
STATUS_SLIPPING = "Slipping"
STATUS_NOT_STARTED = "Not started"

STATUS_COLOUR = {
    STATUS_DONE: "#1e8e3e",
    STATUS_ON_TRACK: "#1e8e3e",
    STATUS_AT_RISK: "#f9a825",
    STATUS_SLIPPING: "#d93025",
    STATUS_NOT_STARTED: "#9aa0a6",
    "Open": "#f9a825", "Closed": "#1e8e3e", "In progress": "#f9a825",
    "Blocked": "#d93025", "Not started ": "#9aa0a6",
}


# --------------------------------------------------------------- date helpers
def parse_date(s) -> date | None:
    if s is None or s == "":
        return None
    if isinstance(s, date) and not isinstance(s, datetime):
        return s
    if isinstance(s, datetime):
        return s.date()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(str(s)[:19], fmt).date()
        except ValueError:
            continue
    return None


def today(state: dict) -> date:
    override = state.get("settings", {}).get("today_override")
    return parse_date(override) or date.today()


def days_between(a: date | None, b: date | None) -> int | None:
    if a is None or b is None:
        return None
    return (b - a).days


def _assignment(state: dict) -> date:
    return parse_date(state.get("settings", {}).get("assignment_date")) or date(2026, 5, 14)


def project_week(state: dict, d: date | None) -> int | None:
    """1-based project week from the assignment date (7-day blocks)."""
    if d is None:
        return None
    delta = (d - _assignment(state)).days
    return max(1, delta // 7 + 1)


def week_range(state: dict, week_no: int) -> tuple[date, date]:
    start = _assignment(state) + timedelta(days=7 * (week_no - 1))
    return start, start + timedelta(days=6)


def assign_by_date(due, effort_days: int, state: dict) -> str:
    """Back-calculate the 'assign by' date: due − effort − 1 buffer day, snapped
    to a weekday and not before the assignment date."""
    d = parse_date(due)
    if d is None:
        return ""
    ab = d - timedelta(days=(effort_days or 1) + 1)
    floor = _assignment(state)
    if ab < floor:
        ab = floor
    while ab.weekday() >= 5:          # nudge weekends back to Friday
        ab -= timedelta(days=1)
    return ab.isoformat()


# ------------------------------------------------------------------- statuses
def derive_status(pct: float, shadow: date | None, contract: date | None,
                  now: date) -> str:
    pct = pct or 0
    if pct >= 100:
        return STATUS_DONE
    if pct <= 0:
        if contract and now > contract:
            return STATUS_SLIPPING
        if shadow and now > shadow:
            return STATUS_AT_RISK
        return STATUS_NOT_STARTED
    if contract and now > contract:
        return STATUS_SLIPPING
    if shadow and now > shadow:
        return STATUS_AT_RISK
    return STATUS_ON_TRACK


# ----------------------------------------------------------------- task model
def _task_pct(t: dict) -> float:
    """Normalised 0-100 for any task (prep tasks use the done flag)."""
    if "pct" in t and t.get("type") != "_prep":
        return float(t.get("pct", 0) or 0)
    return 100.0 if t.get("done") else 0.0


def tasks(state: dict) -> list[dict]:
    """Flat list of every reportable task with computed week / assign-by."""
    now = today(state)
    out: list[dict] = []

    # pre-kickoff prep tasks
    for t in state.get("this_week", []):
        due = parse_date(t.get("due"))
        pct = 100.0 if t.get("done") else 0.0
        out.append({
            "id": f"PREP-{t['id']}", "group": "PREP", "group_name": "Pre-kickoff prep",
            "title": t.get("action", ""), "owner": t.get("owner", ""),
            "type": "binary", "weight": t.get("weight", 1), "pct": pct,
            "done": bool(t.get("done")), "due": due,
            "assign_by": parse_date(t.get("assign_by")),
            "effort_days": t.get("effort_days", 1),
            "week": project_week(state, due), "ref": ("this_week", t["id"]),
            "overdue": bool(due and due < now and pct < 100),
        })

    # phase sub-tasks
    for pi, p in enumerate(state.get("phases", [])):
        for si, s in enumerate(p.get("subtasks", [])):
            due = parse_date(s.get("due"))
            pct = float(s.get("pct", 0) or 0)
            out.append({
                "id": s.get("id", f"{p['id']}-{si+1}"), "group": p["id"],
                "group_name": p["name"], "title": s.get("task", ""),
                "owner": s.get("owner", ""), "type": s.get("type", "percent"),
                "weight": s.get("weight", 1), "pct": pct,
                "done": pct >= 100, "due": due,
                "assign_by": parse_date(s.get("assign_by")),
                "effort_days": s.get("effort_days", 1),
                "week": project_week(state, due), "ref": ("phase", pi, si),
                "overdue": bool(due and due < now and pct < 100),
            })
    return out


def set_task_pct(state: dict, ref, pct: float) -> None:
    """Write a reported value back to the right place in state."""
    kind = ref[0]
    if kind == "this_week":
        for t in state["this_week"]:
            if t["id"] == ref[1]:
                t["done"] = pct >= 100
    elif kind == "phase":
        _, pi, si = ref
        state["phases"][pi]["subtasks"][si]["pct"] = int(round(pct))


# -------------------------------------------------------------- weekly to-do
def _todo_sort(t: dict):
    """Categorise: first by due date, then by owner, then by importance
    (heavier sub-tasks first)."""
    return (t["due"] or date.max, (t["owner"] or "").lower(), -t.get("weight", 1))


def weekly_view(state: dict) -> dict:
    """Pending tasks (current-week + carried-over overdue) plus a preview of
    upcoming weeks, all ordered by due date -> owner -> importance."""
    cw = project_week(state, today(state))
    all_tasks = tasks(state)
    open_tasks = [t for t in all_tasks if t["pct"] < 100]

    carried = sorted([t for t in open_tasks if (t["week"] or 0) < cw], key=_todo_sort)
    this_week = sorted([t for t in all_tasks if t["week"] == cw], key=_todo_sort)
    upcoming = sorted([t for t in open_tasks if (t["week"] or 0) > cw], key=_todo_sort)
    # combined pending list (everything due by the end of this week, still open)
    pending = sorted([t for t in open_tasks if (t["week"] or 0) <= cw], key=_todo_sort)
    return {"current_week": cw, "range": week_range(state, cw), "pending": pending,
            "carried": carried, "this_week": this_week, "upcoming": upcoming}


def set_phase_complete(state: dict, phase_id: str, done: bool) -> None:
    """Mark a contractual deliverable submitted/withdrawn: bulk-set every
    sub-task of the matching phase to 100% (done) or 0% (not done)."""
    for p in state.get("phases", []):
        if p["id"] == phase_id:
            for s in p.get("subtasks", []):
                s["pct"] = 100 if done else 0


# --------------------------------------------------------------- phase rollup
def _weighted(items: list[dict]) -> float:
    tot = sum(i.get("weight", 1) for i in items)
    if not tot:
        return 0.0
    return round(sum(i.get("weight", 1) * _phase_sub_pct(i) for i in items) / tot, 1)


def _phase_sub_pct(s: dict) -> float:
    return float(s.get("pct", 0) or 0)


def phase_rows(state: dict) -> list[dict]:
    now = today(state)
    milestones = state.get("milestones", [])
    out = []
    for idx, p in enumerate(state.get("phases", [])):
        subs = p.get("subtasks", [])
        pct = _weighted(subs)
        shadow = contract = None
        if idx < len(milestones):
            shadow = parse_date(milestones[idx].get("shadow"))
            contract = parse_date(milestones[idx].get("contract"))
        out.append({
            "id": p["id"], "name": p["name"], "window": p.get("window", ""),
            "pct": pct, "n_sub": len(subs),
            "n_done": sum(1 for s in subs if _phase_sub_pct(s) >= 100),
            "status": derive_status(pct, shadow, contract, now),
        })
    return out


def phase_pct_map(state: dict) -> dict[str, float]:
    return {r["id"]: r["pct"] for r in phase_rows(state)}


def overall_progress(state: dict) -> float:
    """Weighted mean across every phase sub-task (the implementation work)."""
    subs = [s for p in state.get("phases", []) for s in p.get("subtasks", [])]
    return _weighted(subs)


# ----------------------------------------------------------------- milestones
def milestone_rows(state: dict) -> list[dict]:
    """Milestone % is DERIVED from its matching phase (P1->M1 …), so reporting a
    task instantly moves the milestone and clears stale Attention items."""
    now = today(state)
    phases = phase_rows(state)
    out = []
    for idx, m in enumerate(state.get("milestones", [])):
        shadow = parse_date(m.get("shadow"))
        contract = parse_date(m.get("contract"))
        pct = phases[idx]["pct"] if idx < len(phases) else m.get("pct", 0)
        out.append({
            **m, "pct": pct,
            "status": derive_status(pct, shadow, contract, now),
            "days_to_shadow": days_between(now, shadow),
            "days_to_contract": days_between(now, contract),
        })
    return out


# ------------------------------------------------------ critical path & risks
def critical_path_rows(state: dict) -> list[dict]:
    now = today(state)
    pmap = phase_pct_map(state)
    phases = {r["id"]: r for r in phase_rows(state)}
    out = []
    for c in state.get("critical_path", []):
        ph = c.get("phase", "")
        pct = pmap.get(ph, 0)
        st = phases.get(ph, {}).get("status", STATUS_NOT_STARTED)
        if pct >= 100:
            status = "Closed"
        elif st == STATUS_SLIPPING:
            status = "Blocked"
        elif st == STATUS_AT_RISK:
            status = "At risk"
        elif pct > 0:
            status = "In progress"
        else:
            status = "Not started"
        out.append({**c, "pct": pct, "status": status,
                    "open": status not in ("Closed",)})
    return out


def risk_rows(state: dict) -> list[dict]:
    pmap = phase_pct_map(state)
    phases = {r["id"]: r for r in phase_rows(state)}
    out = []
    for r in state.get("risks", []):
        ph = r.get("phase", "")
        pct = pmap.get(ph, None)
        st = phases.get(ph, {}).get("status")
        if pct is None or ph == "":
            status = "Open – monitored"
        elif pct >= 100:
            status = "Closed"
        elif st == STATUS_SLIPPING:
            status = "Open – elevated"
        elif st == STATUS_AT_RISK:
            status = "Open – active"
        else:
            status = "Open – monitored"
        out.append({**r, "auto_status": status, "open": status != "Closed"})
    return out


def open_counts(state: dict) -> dict:
    cp = critical_path_rows(state)
    rk = risk_rows(state)
    return {
        "cp_open": sum(1 for c in cp if c["open"]),
        "cp": cp,
        "risk_open": sum(1 for r in rk if r["open"]),
        "risk_high_open": sum(1 for r in rk if r["open"] and r.get("likelihood") == "High"),
        "risks": rk,
    }


# ----------------------------------------------------------- team workloads
def member_workload(state: dict) -> dict[str, list[dict]]:
    """Open tasks grouped by owner, each with due + assign-by, soonest assign first."""
    now = today(state)
    grouped: dict[str, list[dict]] = {}
    for t in tasks(state):
        if t["pct"] >= 100:
            continue
        owner = (t["owner"] or "Unassigned").strip()
        item = {**t, "assign_overdue": bool(t["assign_by"] and t["assign_by"] < now)}
        grouped.setdefault(owner, []).append(item)
    for k in grouped:
        # within a member: soonest due first, then most important
        grouped[k].sort(key=lambda x: (x["due"] or date.max, -x.get("weight", 1)))
    return dict(sorted(grouped.items(), key=lambda kv: -len(kv[1])))


# ----------------------------------------------------------- upcoming (short)
def upcoming_tasks(state: dict, limit: int = 8) -> list[dict]:
    now = today(state)
    items = [t for t in tasks(state) if t["pct"] < 100]
    items.sort(key=lambda t: (t["due"] or date.max))
    return items[:limit]


# ---------------------------------------------------------------- sample
def sample_rows(state: dict) -> list[dict]:
    thr = state.get("settings", {}).get("booster_threshold_pct", 70)
    bdate = parse_date(state.get("settings", {}).get("booster_decision_date"))
    now = today(state)
    window_open = bool(bdate and now >= bdate)
    out = []
    for r in state.get("sample", []):
        target = r.get("target", 0) or 0
        comp = r.get("completes", 0) or 0
        pct = round(100 * comp / target, 1) if target else 0
        under = pct < thr
        out.append({**r, "pct": pct, "booster": under and window_open,
                    "under_threshold": under})
    return out


def sample_totals(state: dict) -> dict:
    rows = sample_rows(state)
    target = sum(r["target"] for r in rows)
    comp = sum(r["completes"] for r in rows)
    return {
        "target": target, "completes": comp,
        "pct": round(100 * comp / target, 1) if target else 0,
        "refusals": sum(r.get("refusals", 0) for r in rows),
        "calls": sum(r.get("calls", 0) for r in rows),
        "boosters": sum(1 for r in rows if r["booster"]),
        "under": sum(1 for r in rows if r["under_threshold"]),
    }
