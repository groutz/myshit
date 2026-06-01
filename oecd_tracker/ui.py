"""Shared UI helpers: page config, header, status badges, small CSS."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from logic import STATUS_COLOUR

PROJECT = "OECD/INFE 2026 — Greece"
LOGO = Path(__file__).resolve().parent / "assets" / "kapa_logo.png"

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
</style>
"""


def setup(title: str, icon: str = "📊") -> None:
    st.set_page_config(page_title=f"{title} · PM Tracker", page_icon=icon,
                       layout="wide", initial_sidebar_state="expanded")
    # Kapa Research logo, upper-left (and atop the sidebar).
    if LOGO.exists() and hasattr(st, "logo"):
        try:
            st.logo(str(LOGO), size="large")
        except TypeError:        # older Streamlit without the size kwarg
            st.logo(str(LOGO))
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
