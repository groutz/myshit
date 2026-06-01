"""Project Status — an auto-written status note, shareable with the client.

Generated from the live data in a credible, transparent, bureaucratic register.
Client-safe by default: it uses only externally-committed (contract) dates and
never exposes shadow dates, the risk watchlist or buffers (workbook rule).
"""

from __future__ import annotations

import streamlit as st

import logic
from store import get_state
from ui import page_header, setup

setup("Project Status", "📄")
state = get_state()
now = logic.today(state)
meta = state.get("meta", {})
cfg = state.get("settings", {})

page_header("Project Status note",
            "Auto-generated from current task reporting. Client-safe wording; "
            "review before sending. Internal annex is for your eyes only.")

include_internal = st.toggle("Include internal annex (risks / critical path) — "
                             "DO NOT send to client", value=False)

# client-facing phrasing for internal statuses
CLIENT = {
    logic.STATUS_DONE: "Completed",
    logic.STATUS_ON_TRACK: "On schedule",
    logic.STATUS_AT_RISK: "Underway",
    logic.STATUS_SLIPPING: "Underway",
    logic.STATUS_NOT_STARTED: "Scheduled (not yet commenced)",
}

overall = logic.overall_progress(state)
ms = logic.milestone_rows(state)
done = sum(1 for m in ms if m["status"] == logic.STATUS_DONE)
final_c = logic.parse_date(cfg.get("final_contract"))
days_to_final = logic.days_between(now, final_c)
totals = logic.sample_totals(state)

# ----------------------------------------------------------------- narrative
L: list[str] = []
L.append(f"# Project Status Report")
L.append(f"**Project:** {meta.get('Project', 'OECD/INFE 2026 — Greece')}")
L.append(f"**Contracting authority:** {meta.get('Contracting Authority', '')}")
L.append(f"**Contractor:** {meta.get('Contractor', '')}")
L.append(f"**Project Manager:** {meta.get('PM', '')}")
L.append(f"**Reporting date:** {now:%d %B %Y}")
L.append("")
L.append("## 1. Summary")

if overall >= 99:
    summ = ("All contracted work streams are complete. The project is being "
            "finalised for delivery.")
elif done == 0 and overall < 5:
    summ = ("The project is in its initial set-up phase. Preparatory work is "
            "proceeding in line with the agreed schedule.")
else:
    summ = (f"Implementation is progressing as planned, with overall completion "
            f"at approximately {overall:.0f}%. {done} of {len(ms)} contractual "
            f"milestones have been completed to date.")
if days_to_final is not None and days_to_final >= 0:
    summ += (f" Final delivery remains scheduled for "
             f"{final_c:%d %B %Y} ({days_to_final} days from this report).")
L.append(summ)
L.append("")

L.append("## 2. Milestone status")
L.append("| Milestone | Contractual date | Status | Completion |")
L.append("|---|---|---|---|")
for m in ms:
    cdate = logic.parse_date(m.get("contract"))
    L.append(f"| {m['name']} | {cdate:%d %b %Y} | {CLIENT.get(m['status'], m['status'])} "
             f"| {m['pct']:.0f}% |")
L.append("")

# fieldwork / sample, only once it is meaningful
if totals["completes"] > 0:
    L.append("## 3. Fieldwork progress")
    L.append(f"A total of {totals['completes']} completed interviews have been "
             f"recorded against a target of {totals['target']} "
             f"({totals['pct']:.0f}%). Sampling across the 26 NUTS-2 strata is "
             f"being monitored to ensure balanced representation.")
    L.append("")

# next steps from the next open tasks (generic, no internal detail)
nxt = [t for t in logic.upcoming_tasks(state, limit=4)]
if nxt:
    L.append("## 4. Next steps")
    for t in nxt:
        due = t["due"].strftime("%d %B %Y") if t["due"] else "the coming period"
        L.append(f"- {t['title']} (target: {due}).")
    L.append("")

L.append("## 5. Compliance")
L.append("Work continues in accordance with the OECD/INFE Toolkit 2026 "
         "methodology and the contractual data template. GDPR compliance is "
         "maintained throughout. Weekly progress reporting to the Contracting "
         "Authority is being provided as scheduled.")

narrative = "\n".join(L)

# ----------------------------------------------------------------- internal annex
if include_internal:
    A = ["", "---", "## INTERNAL ANNEX — NOT FOR DISTRIBUTION", ""]
    A.append("### Critical path")
    for c in logic.critical_path_rows(state):
        A.append(f"- [{c['status']}] {c['item']} — {c['owner']} ({c['pct']:.0f}%)")
    A.append("")
    A.append("### Risk watchlist")
    for r in logic.risk_rows(state):
        A.append(f"- [{r['auto_status']}] {r['risk']} "
                 f"(L:{r['likelihood']}/I:{r['impact']}) — {r['mitigation']}")
    A.append("")
    A.append(f"### Internal (shadow) final date: "
             f"{logic.parse_date(cfg.get('final_shadow')):%d %B %Y}")
    narrative += "\n".join(A)

st.markdown('<hr class="section-rule">', unsafe_allow_html=True)
st.markdown(narrative)

st.markdown('<hr class="section-rule">', unsafe_allow_html=True)
st.download_button("⬇️ Download as Markdown", data=narrative,
                   file_name=f"project_status_{now:%Y%m%d}.md", mime="text/markdown")
with st.expander("📋 Copy the raw text"):
    st.code(narrative, language="markdown")
