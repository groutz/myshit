"""Project Status — a client-ready weekly progress email.

Written in the register of a weekly update to the Contracting Authority and
derived from current task/milestone status. It contains NO internal task
descriptions, shadow dates, risks or buffers — only a high-level overview that
is safe to send. An optional internal annex (for the PM only) is off by default.
"""

from __future__ import annotations

import streamlit as st

import logic
from store import get_state
from ui import page_header, setup

setup("Project Status", "📧")
state = get_state()
now = logic.today(state)
meta = state.get("meta", {})
cfg = state.get("settings", {})

page_header("Weekly status — client email",
            "Auto-drafted from current progress, in weekly-update language. "
            "Safe to send: no internal task detail, shadow dates, risks or "
            "buffers. Review before sending.")

include_internal = st.toggle("Append internal annex (PM only — DO NOT send)",
                             value=False)

# ----------------------------------------------------------------- inputs
overall = logic.overall_progress(state)
ms = logic.milestone_rows(state)
phases = logic.phase_rows(state)
done_ms = [m for m in ms if m["status"] == logic.STATUS_DONE]
final_c = logic.parse_date(cfg.get("final_contract"))
totals = logic.sample_totals(state)
fw_start = logic.parse_date(cfg.get("fieldwork_start"))
fw_end = logic.parse_date(cfg.get("fieldwork_end"))
in_fieldwork = bool(fw_start and fw_end and fw_start <= now <= fw_end)

# current focus = first phase in progress, else first not-yet-complete
current_idx = next((i for i, p in enumerate(phases) if 0 < p["pct"] < 100), None)
if current_idx is None:
    current_idx = next((i for i, p in enumerate(phases) if p["pct"] < 100), len(phases) - 1)
current_phase = phases[current_idx]["name"]
next_idx = next((i for i, p in enumerate(phases) if p["pct"] < 100), None)

PM = meta.get("PM", "")
subject = (f"Weekly Progress Update — OECD/INFE 2026 Survey of Adult Financial "
           f"Literacy (Greece) — {now:%d %B %Y}")

# ----------------------------------------------------------------- body
L: list[str] = []
L.append(f"**To:** {meta.get('Contracting Authority', 'Contracting Authority')}")
L.append(f"**From:** {PM}, Project Manager — Κάπα Research")
L.append(f"**Date:** {now:%d %B %Y}")
L.append(f"**Subject:** {subject}")
L.append("")
L.append("Dear Sir/Madam,")
L.append("")
L.append("Please find below this week's progress update on the OECD/INFE 2026 "
         "International Survey of Adult Financial Literacy, Inclusion and "
         "Well-Being in Greece.")
L.append("")

# overall
if overall >= 99:
    L.append("All contracted activities have now been completed and the project "
             "is being finalised for delivery. The project has proceeded fully "
             "in line with the agreed timetable.")
elif overall < 5 and not done_ms:
    L.append("The project has been initiated and preparatory activities are "
             "under way, proceeding in line with the agreed timetable.")
else:
    L.append(f"Project implementation is progressing in line with the agreed "
             f"timetable. To date, {len(done_ms)} of {len(ms)} contractual "
             f"milestones have been completed, and overall progress stands at "
             f"approximately {overall:.0f}%. Work is currently centred on the "
             f"{current_phase} phase.")
L.append("")

# milestones (high level, names only)
if done_ms:
    names = ", ".join(m["name"].split(" (")[0] for m in done_ms)
    L.append(f"Milestones completed to date: {names}.")
    L.append("")

# fieldwork, only while it is meaningful
if in_fieldwork or totals["completes"] > 0:
    L.append(f"Fieldwork is under way. As at the date of this report, "
             f"{totals['completes']} interviews have been completed against a "
             f"target of {totals['target']} ({totals['pct']:.0f}%), with data "
             f"collection proceeding across all 26 sampling strata (NUTS-2 "
             f"region × urban/rural). Sample balance is being monitored "
             f"continuously to ensure representativeness.")
    L.append("")

# outlook (phase-level, no task detail)
if next_idx is not None and overall < 99:
    nxt = phases[next_idx]["name"]
    if 0 < phases[next_idx]["pct"] < 100:
        L.append(f"Over the coming period, work will continue on the {nxt} phase.")
    else:
        L.append(f"Over the coming period, the project will move into the "
                 f"{nxt} phase.")
    L.append("")

if final_c:
    L.append(f"The project remains on schedule for final delivery on "
             f"{final_c:%d %B %Y}.")
    L.append("")

L.append("We remain at your disposal for any clarification you may require.")
L.append("")
L.append("Kind regards,")
L.append(f"{PM}")
L.append("Project Manager — Κάπα Research – Consulting AE")

email = "\n".join(L)

# ----------------------------------------------------------------- internal annex
if include_internal:
    A = ["", "---", "## INTERNAL ANNEX — NOT FOR DISTRIBUTION", ""]
    A.append(f"Internal (shadow) final date: "
             f"{logic.parse_date(cfg.get('final_shadow')):%d %B %Y}")
    A.append("")
    A.append("### Critical path")
    for c in logic.critical_path_rows(state):
        A.append(f"- [{c['status']}] {c['item']} — {c['owner']} ({c['pct']:.0f}%)")
    A.append("")
    A.append("### Risk watchlist")
    for r in logic.risk_rows(state):
        A.append(f"- [{r['auto_status']}] {r['risk']} "
                 f"(L:{r['likelihood']}/I:{r['impact']})")
    email += "\n".join(A)

st.markdown('<hr class="section-rule">', unsafe_allow_html=True)
st.markdown(email)

st.markdown('<hr class="section-rule">', unsafe_allow_html=True)
st.download_button("⬇️ Download email (.txt)", data=email,
                   file_name=f"weekly_update_{now:%Y%m%d}.txt", mime="text/plain")
with st.expander("📋 Copy the email text"):
    st.code(email, language="text")
