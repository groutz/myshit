"""Shared UI helpers: page config, header, status badges, small CSS."""

from __future__ import annotations

import streamlit as st

from logic import STATUS_COLOUR

PROJECT = "OECD/INFE 2026 — Greece"

# Arial across the whole app (UI, widgets, headings, tables) + small styling.
_CSS = """
<style>
html, body, [class*="css"], .stApp, [data-testid="stAppViewContainer"],
[data-testid="stSidebar"], button, input, textarea, select,
h1, h2, h3, h4, h5, h6, p, div, span, label, .stMarkdown, .stDataFrame {
    font-family: Arial, Helvetica, sans-serif !important;
}
.block-container {padding-top: 1.6rem; max-width: 1200px;}
.badge {display:inline-block; padding:2px 10px; border-radius:12px;
        color:#fff; font-size:0.78rem; font-weight:600; white-space:nowrap;}
.kpi-note {color:#5f6368; font-size:0.8rem; margin-top:-8px;}
.section-rule {border:none; border-top:2px solid #e8eaed; margin:1.2rem 0 0.6rem;}
.accent {border-left:4px solid #0b2e59; padding-left:10px;}
/* Hide the Material Symbols chevron on popover triggers, which can render as
   raw text ("expand_more") when the icon font isn't available. */
[data-testid="stPopover"] button span[data-testid="stIconMaterial"],
[data-testid="stPopoverButton"] span[data-testid="stIconMaterial"],
[data-testid="stPopover"] button span.material-symbols-rounded,
[data-testid="stPopover"] button span.material-symbols-outlined {
    display: none !important;
}
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
