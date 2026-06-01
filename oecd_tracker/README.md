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
| **Dashboard** | (read-only rollup) | overall progress bar, milestone & phase bars, clickable open critical-paths/risks, Attention, team workload |
| **Weekly To-Do** | tick / slide this week's + carried-over tasks | **everything** — phase %, milestone %, critical paths, risks |
| **Phases** | (advanced) edit % / see weights | weighted phase roll-up + overall progress |
| **Milestones** | edit dates only (% is derived) | Green/Amber/Red/Grey status + days-to-shadow |
| **Sample** | upload Sakis's daily file (or enter completes) | % of target, booster flags, totals |
| **Critical Path & Risks** | edit wording/mitigations (status auto) | open-item counts on the Dashboard |
| **Logs** | weekly reports (Mondays, fieldwork only), daily KPIs, interviewer bench, QA log | running operational record |
| **Reference** | Team, Buffers, Kickoff Playbook, Project info | standing context |
| **Project Status** | (read-only) | a client-safe written status note to download/share |
| **Settings** | dates, targets, today-override, export/import, reset | what-if scenarios + backup |

### Daily sample update (Survey Solutions → Excel → upload)

On the **Sample** page, **Download the template for Sakis** (Αθανάσιος) — a
pre-filled `.xlsx` with the 26 strata. Each fieldwork day he exports completion
data (region × urbanity) from Survey Solutions, enters the cumulative
**Completes** per stratum, and uploads the file. The app previews the changes
(old → new per stratum) before you **Apply**. The parser accepts either the
per-stratum template (matched by ID) or a raw per-interview export (one
completed interview per row, with Region + Urban/Rural columns), which it counts
per stratum automatically. A tracked task (`P4-7`, owner Αθανάσιος) covers this
daily delivery during fieldwork. A ready copy of the template lives in
[`templates/`](templates/).

### The task model (how "report one thing, the rest fills in" works)

Tasks are the single source of truth. Each task has a **type** (binary tick-box
or 0–100% slider), a **weight**, an **effort estimate**, and a **shadow-based
due date** from which an **"assign by" date** is computed (due − effort − buffer).

- **Phase %** = the weighted roll-up of its sub-tasks (heavier tasks move it more).
- **Milestone %** mirrors its phase (P1→M1 …) — so completing a task clears stale
  Attention items automatically.
- **Critical-path & risk status** derive from the phase each one depends on.
- The **Weekly To-Do** shows the current project week (7-day blocks from the
  assignment date) plus any overdue tasks carried over from earlier weeks.

## How status is derived

- **Shadow date** = internal early-warning trigger (~7–10 days before contract).
- A milestone/phase is **Done** at 100%, **Slipping** (🔴) if past its contract
  date and not complete, **At risk** (🟠) if past its shadow date, **Not
  started** (⚪) otherwise, **On track** (🟢) while in progress and ahead of dates.
- **Overall progress** = mean % across every phase sub-task (equal weight).
- **Booster flag** fires for a stratum under the threshold (default 70%) once
  today is on/after the booster decision date.

## Data & persistence

The app picks its storage backend automatically:

- **Local file** (default, when you run it on your machine): edits persist to
  `state.json` in this folder. Git-ignored, so the repo always keeps the clean
  baseline.
- **Google Sheet** (cloud): used automatically when Streamlit secrets contain a
  `[gcp_service_account]` block and `[sheets] spreadsheet_key`. The whole state
  is gzip+base64-encoded into a private Sheet so your inputs survive Streamlit
  Community Cloud's ephemeral filesystem.

`seed_data.json` is the clean baseline extracted from the original workbook
(`OECD_INFE_2026_PM_Tracker_v1.xlsx`) and is the **Settings → Reset** point.
**Settings → Export/Import** gives you JSON snapshots regardless of backend.
The active backend is shown at the bottom of the **Settings** page.

---

## Deploy as a private cloud web app

This gives you a URL you can open from anywhere, with your edits saved to a
private Google Sheet and the app visible only to people you invite.

### A. Create a Google Sheet + service account (persistence)

1. Create a new, empty Google Sheet. Copy the **ID** from its URL —
   `https://docs.google.com/spreadsheets/d/`**`THIS_PART`**`/edit`.
2. Go to <https://console.cloud.google.com> → create (or pick) a project.
3. **APIs & Services → Library** → enable **Google Sheets API**.
4. **APIs & Services → Credentials → Create credentials → Service account**.
   Give it a name (e.g. `tracker-bot`), create it, then under its **Keys** tab
   → **Add key → JSON**. A `.json` file downloads — keep it safe.
5. Open that JSON; copy the `client_email` (looks like
   `tracker-bot@…iam.gserviceaccount.com`). Back in your Google Sheet, click
   **Share** and give that email **Editor** access.

### B. Deploy on Streamlit Community Cloud

1. <https://share.streamlit.io> → **Sign in with GitHub** (the account that owns
   `groutz/myshit`).
2. **Create app → Deploy from GitHub**:
   - Repository: `groutz/myshit`
   - Branch: `main` (after merging PR #6) or `claude/funny-cannon-aieBW`
   - **Main file path:** `oecd_tracker/app.py`
3. Before/after deploying, open **Settings → Secrets** and paste the contents of
   [`.streamlit/secrets.toml.example`](.streamlit/secrets.toml.example), filled
   in from your service-account JSON, plus your `spreadsheet_key`. Save — the app
   restarts and now reads/writes the Sheet.

### C. Make it private (required — the data is confidential)

In the app's **Settings → Sharing**, set **"Who can view this app"** to
**specific people** and add the email addresses allowed in (Google sign-in).
The README of the source workbook is explicit: Shadow dates, the Risk Watchlist
and Buffers are **INTERNAL** — never leave the app on public sharing.

> Running locally instead? Copy `.streamlit/secrets.toml.example` to
> `.streamlit/secrets.toml` and fill it in to use the same Sheet from your Mac;
> omit it to keep using the local `state.json` file.
