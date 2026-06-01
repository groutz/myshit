"""Shared UI helpers: page config, header, status badges, small CSS."""

from __future__ import annotations

import streamlit as st

from logic import STATUS_COLOUR

PROJECT = "OECD/INFE 2026 — Greece"

_CSS = """
<style>
.block-container {padding-top: 2.2rem; max-width: 1200px;}
.badge {display:inline-block; padding:2px 10px; border-radius:12px;
        color:#fff; font-size:0.78rem; font-weight:600; white-space:nowrap;}
.kpi-note {color:#5f6368; font-size:0.8rem; margin-top:-8px;}
.section-rule {border:none; border-top:2px solid #e8eaed; margin:1.2rem 0 0.6rem;}
.accent {border-left:4px solid #1a73e8; padding-left:10px;}
</style>
"""


def setup(title: str, icon: str = "📊") -> None:
    st.set_page_config(page_title=f"{title} · PM Tracker", page_icon=icon,
                       layout="wide", initial_sidebar_state="expanded")
    st.markdown(_CSS, unsafe_allow_html=True)


def badge(status: str) -> str:
    colour = STATUS_COLOUR.get(status, "#5f6368")
    return f'<span class="badge" style="background:{colour}">{status}</span>'


def status_emoji(status: str) -> str:
    return {
        "Done": "🟢", "On track": "🟢", "At risk": "🟠",
        "Slipping": "🔴", "Not started": "⚪",
        "Open": "🟠", "Closed": "🟢", "Blocked": "🔴", "In progress": "🟠",
    }.get(status, "⚪")


def page_header(title: str, subtitle: str = "") -> None:
    st.markdown(f'<div class="accent"><h2 style="margin:0">{title}</h2>'
                f'<div class="kpi-note">{subtitle}</div></div>',
                unsafe_allow_html=True)
    st.write("")


def saved_toast() -> None:
    st.toast("Saved ✓", icon="💾")
