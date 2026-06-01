"""Derived metrics for the PM Tracker.

Everything the dashboard shows is computed here from the live state, so that
ticking a task or typing a number anywhere in the app instantly re-rolls
progress, statuses, countdowns and the "upcoming tasks" list.
"""

from __future__ import annotations

from datetime import date, datetime

# Status vocabulary mapped to the README colour code.
STATUS_DONE = "Done"            # green
STATUS_ON_TRACK = "On track"    # green
STATUS_AT_RISK = "At risk"      # amber
STATUS_SLIPPING = "Slipping"    # red
STATUS_NOT_STARTED = "Not started"  # grey

STATUS_COLOUR = {
    STATUS_DONE: "#1e8e3e",
    STATUS_ON_TRACK: "#1e8e3e",
    STATUS_AT_RISK: "#f9a825",
    STATUS_SLIPPING: "#d93025",
    STATUS_NOT_STARTED: "#9aa0a6",
    # critical-path / risk vocab
    "Open": "#f9a825",
    "Closed": "#1e8e3e",
    "In progress": "#f9a825",
    "Blocked": "#d93025",
}


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
    """Live 'today', overridable from Settings for what-if scenarios."""
    override = state.get("settings", {}).get("today_override")
    d = parse_date(override)
    return d or date.today()


def days_between(a: date | None, b: date | None) -> int | None:
    if a is None or b is None:
        return None
    return (b - a).days


def derive_status(pct: float, shadow: date | None, contract: date | None,
                  now: date) -> str:
    """Status from % complete vs the internal (shadow) and external (contract)
    dates. Shadow is the early-warning trigger; slipping past contract is red."""
    pct = pct or 0
    if pct >= 100:
        return STATUS_DONE
    if pct <= 0:
        if contract and now > contract:
            return STATUS_SLIPPING
        if shadow and now > shadow:
            return STATUS_AT_RISK
        return STATUS_NOT_STARTED
    # in progress
    if contract and now > contract:
        return STATUS_SLIPPING
    if shadow and now > shadow:
        return STATUS_AT_RISK
    return STATUS_ON_TRACK


# ---------------------------------------------------------------- milestones
def milestone_rows(state: dict) -> list[dict]:
    now = today(state)
    out = []
    for m in state.get("milestones", []):
        shadow = parse_date(m.get("shadow"))
        contract = parse_date(m.get("contract"))
        out.append({
            **m,
            "status": derive_status(m.get("pct", 0), shadow, contract, now),
            "days_to_shadow": days_between(now, shadow),
            "days_to_contract": days_between(now, contract),
        })
    return out


# -------------------------------------------------------------------- phases
def phase_rows(state: dict) -> list[dict]:
    """Each phase rolls up to the mean of its sub-task %s; status derives from
    that and the matching milestone date (phase order maps to milestone order)."""
    now = today(state)
    milestones = state.get("milestones", [])
    out = []
    for idx, p in enumerate(state.get("phases", [])):
        subs = p.get("subtasks", [])
        pct = round(sum(s.get("pct", 0) for s in subs) / len(subs), 1) if subs else 0
        shadow = contract = None
        if idx < len(milestones):
            shadow = parse_date(milestones[idx].get("shadow"))
            contract = parse_date(milestones[idx].get("contract"))
        out.append({
            "id": p["id"], "name": p["name"], "window": p.get("window", ""),
            "pct": pct, "n_sub": len(subs),
            "n_done": sum(1 for s in subs if s.get("pct", 0) >= 100),
            "status": derive_status(pct, shadow, contract, now),
        })
    return out


def overall_progress(state: dict) -> float:
    """Project-wide implementation progress = mean % across every phase
    sub-task (each sub-task weighted equally)."""
    subs = [s for p in state.get("phases", []) for s in p.get("subtasks", [])]
    if not subs:
        return 0.0
    return round(sum(s.get("pct", 0) for s in subs) / len(subs), 1)


# ---------------------------------------------------------------- this week
def thisweek_summary(state: dict) -> tuple[int, int]:
    tasks = state.get("this_week", [])
    done = sum(1 for t in tasks if t.get("done"))
    return done, len(tasks)


# ----------------------------------------------------------- upcoming tasks
def upcoming_tasks(state: dict, limit: int = 12) -> list[dict]:
    """Surface the next things to do: incomplete This-Week actions (with due
    dates) plus in-flight / not-started phase sub-tasks, soonest first."""
    now = today(state)
    items: list[dict] = []

    for t in state.get("this_week", []):
        if t.get("done"):
            continue
        due = parse_date(t.get("due"))
        items.append({
            "source": "This Week",
            "what": t.get("action", ""),
            "owner": t.get("owner", ""),
            "due": due,
            "overdue": bool(due and due < now),
            "pct": 100 if t.get("done") else 0,
        })

    milestones = state.get("milestones", [])
    for idx, p in enumerate(state.get("phases", [])):
        # use the phase's milestone shadow date as the soft due date
        due = parse_date(milestones[idx]["shadow"]) if idx < len(milestones) else None
        for s in p.get("subtasks", []):
            if s.get("pct", 0) >= 100:
                continue
            items.append({
                "source": p["id"],
                "what": s.get("task", ""),
                "owner": s.get("owner", ""),
                "due": due,
                "overdue": bool(due and due < now),
                "pct": s.get("pct", 0),
            })

    far = date.max
    items.sort(key=lambda x: (x["due"] or far))
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
        out.append({
            **r,
            "pct": pct,
            "booster": under and window_open,
            "under_threshold": under,
        })
    return out


def sample_totals(state: dict) -> dict:
    rows = sample_rows(state)
    target = sum(r["target"] for r in rows)
    comp = sum(r["completes"] for r in rows)
    return {
        "target": target,
        "completes": comp,
        "pct": round(100 * comp / target, 1) if target else 0,
        "refusals": sum(r.get("refusals", 0) for r in rows),
        "calls": sum(r.get("calls", 0) for r in rows),
        "boosters": sum(1 for r in rows if r["booster"]),
        "under": sum(1 for r in rows if r["under_threshold"]),
    }
