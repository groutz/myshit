# OECD/INFE 2026 — Greece · PM Tracker (web app)

A simple, interactive web app version of the Excel PM tracker for the
**OECD/INFE International Survey of Adult Financial Literacy, Inclusion and
Well-Being 2026 — Greece**. You enter task-completion status on any page and
the app instantly re-rolls overall progress, milestone/phase status, countdowns
and the **Upcoming / next actions** list on the Dashboard.

It is self-contained in this folder and does not touch the rest of the repo.

## Run it

```bash
cd oecd_tracker
pip install -r requirements.txt
streamlit run app.py
```

Then open the URL Streamlit prints (default http://localhost:8501).

## Pages

| Page | What you do | What it drives |
|------|-------------|----------------|
| **Dashboard** | (read-only rollup) | KPIs, milestone & phase bars, alerts, upcoming tasks |
| **This Week** | tick prep tasks Done | completion %, overdue alerts, upcoming list |
| **Phases** | set % complete per sub-task | phase bars + overall progress + phase status |
| **Milestones** | set % complete / dates | Green/Amber/Red/Grey status + days-to-shadow |
| **Sample** | enter completes per stratum | % of target, booster flags, totals |
| **Critical Path & Risks** | update status | open-item counts on the Dashboard |
| **Logs** | Friday reports, daily KPIs, interviewer bench, QA log | running operational record |
| **Reference** | Team, Buffers, Kickoff Playbook, Project info | standing context |
| **Settings** | dates, targets, today-override, export/import, reset | what-if scenarios + backup |

## How status is derived

- **Shadow date** = internal early-warning trigger (~7–10 days before contract).
- A milestone/phase is **Done** at 100%, **Slipping** (🔴) if past its contract
  date and not complete, **At risk** (🟠) if past its shadow date, **Not
  started** (⚪) otherwise, **On track** (🟢) while in progress and ahead of dates.
- **Overall progress** = mean % across every phase sub-task (equal weight).
- **Booster flag** fires for a stratum under the threshold (default 70%) once
  today is on/after the booster decision date.

## Data & persistence

- `seed_data.json` — the clean baseline extracted from the original workbook
  (`OECD_INFE_2026_PM_Tracker_v1.xlsx`). Committed; this is the reset point.
- `state.json` — your live working data, created on first run and updated on
  every **Save**. Git-ignored so the repo keeps the clean baseline.
- **Settings → Export/Import** gives you JSON snapshots for backup or moving
  between machines; **Reset** restores the original Excel data.
