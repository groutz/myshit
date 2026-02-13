"""
Theme management for Survey Agency PM.
Provides preset themes, custom color/font selection, and live CSS injection.
"""

import streamlit as st
import json
import os

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
THEME_PATH = os.path.join(ASSETS_DIR, "theme.json")
CONFIG_PATH = os.path.join(os.path.dirname(__file__), ".streamlit", "config.toml")

# ---------------------------------------------------------------------------
# Preset themes
# ---------------------------------------------------------------------------
PRESETS = {
    "Default Blue": {
        "primary": "#1f77b4",
        "success": "#2ca02c",
        "warning": "#ff7f0e",
        "danger": "#d62728",
        "light": "#aec7e8",
        "background": "#ffffff",
        "secondary_bg": "#f0f2f6",
        "text": "#262730",
        "font": "sans serif",
    },
    "Corporate Navy": {
        "primary": "#1B3A5C",
        "success": "#28A745",
        "warning": "#FFC107",
        "danger": "#DC3545",
        "light": "#6C9BC4",
        "background": "#FAFBFC",
        "secondary_bg": "#E8ECF1",
        "text": "#1A1A2E",
        "font": "sans serif",
    },
    "Forest Green": {
        "primary": "#2D6A4F",
        "success": "#40916C",
        "warning": "#E9C46A",
        "danger": "#E76F51",
        "light": "#95D5B2",
        "background": "#FEFEF9",
        "secondary_bg": "#EDF2E9",
        "text": "#1B4332",
        "font": "serif",
    },
    "Sunset Warm": {
        "primary": "#E76F51",
        "success": "#2A9D8F",
        "warning": "#E9C46A",
        "danger": "#E63946",
        "light": "#F4A261",
        "background": "#FFFBF5",
        "secondary_bg": "#FFF0E0",
        "text": "#264653",
        "font": "sans serif",
    },
    "Dark Mode": {
        "primary": "#4FC3F7",
        "success": "#66BB6A",
        "warning": "#FFA726",
        "danger": "#EF5350",
        "light": "#546E7A",
        "background": "#0E1117",
        "secondary_bg": "#1E1E2E",
        "text": "#FAFAFA",
        "font": "sans serif",
    },
    "Royal Purple": {
        "primary": "#7C3AED",
        "success": "#10B981",
        "warning": "#F59E0B",
        "danger": "#EF4444",
        "light": "#A78BFA",
        "background": "#FAFAFE",
        "secondary_bg": "#F0ECFA",
        "text": "#1E1B4B",
        "font": "sans serif",
    },
}

FONTS = ["sans serif", "serif", "monospace"]

FONT_CSS = {
    "sans serif": '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
    "serif": 'Georgia, "Times New Roman", Times, serif',
    "monospace": '"SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", monospace',
}

# ---------------------------------------------------------------------------
# Load / Save
# ---------------------------------------------------------------------------

def load_theme():
    """Load saved theme from disk, or return default."""
    if os.path.exists(THEME_PATH):
        try:
            with open(THEME_PATH, "r") as f:
                data = json.load(f)
            # Ensure all keys exist (backwards-compat)
            default = PRESETS["Default Blue"]
            for k, v in default.items():
                data.setdefault(k, v)
            data.setdefault("preset", "Default Blue")
            return data
        except (json.JSONDecodeError, IOError):
            pass
    return {"preset": "Default Blue", **PRESETS["Default Blue"]}


def save_theme(theme_data):
    """Persist theme to JSON file and update Streamlit config.toml."""
    os.makedirs(ASSETS_DIR, exist_ok=True)
    with open(THEME_PATH, "w") as f:
        json.dump(theme_data, f, indent=2)
    _update_config_toml(theme_data)


def _update_config_toml(theme_data):
    """Rewrite .streamlit/config.toml so the theme persists across restarts."""
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    config = (
        "[theme]\n"
        f'primaryColor = "{theme_data["primary"]}"\n'
        f'backgroundColor = "{theme_data["background"]}"\n'
        f'secondaryBackgroundColor = "{theme_data["secondary_bg"]}"\n'
        f'textColor = "{theme_data["text"]}"\n'
        f'font = "{theme_data["font"]}"\n'
        "\n"
        "[server]\n"
        "headless = true\n"
    )
    with open(CONFIG_PATH, "w") as f:
        f.write(config)


# ---------------------------------------------------------------------------
# Runtime helpers
# ---------------------------------------------------------------------------

def get_theme():
    """Return current theme dict (cached in session_state)."""
    if "app_theme" not in st.session_state:
        st.session_state.app_theme = load_theme()
    return st.session_state.app_theme


def apply_theme():
    """Inject CSS overrides for immediate theme effect. Returns theme dict."""
    theme = get_theme()
    font_stack = FONT_CSS.get(theme["font"], FONT_CSS["sans serif"])

    # Derive a subtle tint from the primary color for card accents
    primary = theme["primary"]
    is_dark = theme["background"].lower() in ("#0e1117", "#000000", "#111111")

    css = f"""
    <style>
        /* ---- Base ---- */
        .stApp {{
            background-color: {theme['background']};
        }}
        section[data-testid="stSidebar"] {{
            background-color: {theme['secondary_bg']};
        }}

        /* ---- Typography ---- */
        .stApp, .stApp p, .stApp span, .stApp label,
        .stApp li, .stApp td, .stApp th {{
            color: {theme['text']};
        }}
        .stApp h1 {{
            color: {theme['text']};
            font-weight: 700;
            letter-spacing: -0.02em;
        }}
        .stApp h2, .stApp h3, .stApp h4 {{
            color: {theme['text']};
            font-weight: 600;
        }}
        .stApp, .stApp p, .stApp span, .stApp label,
        .stApp h1, .stApp h2, .stApp h3, .stApp h4,
        .stApp li, .stApp td, .stApp th, .stApp input,
        .stApp textarea, .stApp select, .stApp button {{
            font-family: {font_stack};
        }}

        /* ---- Primary accent ---- */
        .stApp a {{
            color: {primary};
        }}
        button[kind="primary"], .stButton > button[kind="primary"] {{
            background-color: {primary};
            border-color: {primary};
        }}

        /* ---- Metric cards ---- */
        [data-testid="stMetric"] {{
            background: {theme['secondary_bg']};
            border: 1px solid {"rgba(255,255,255,0.08)" if is_dark else "rgba(0,0,0,0.06)"};
            border-left: 4px solid {primary};
            border-radius: 8px;
            padding: 12px 16px;
        }}
        [data-testid="stMetricLabel"] {{
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            opacity: 0.75;
        }}
        [data-testid="stMetricValue"] {{
            font-weight: 700;
        }}

        /* ---- Sidebar polish ---- */
        section[data-testid="stSidebar"] .stMarkdown h1 {{
            font-size: 1.3rem;
        }}
        section[data-testid="stSidebar"] [data-testid="stExpander"] {{
            border: none;
            background: transparent;
        }}

        /* ---- Data tables ---- */
        .stDataFrame {{
            border-radius: 8px;
            overflow: hidden;
        }}

        /* ---- Expanders ---- */
        [data-testid="stExpander"] {{
            border-radius: 8px;
            border: 1px solid {"rgba(255,255,255,0.08)" if is_dark else "rgba(0,0,0,0.06)"};
        }}

        /* ---- Plotly charts container ---- */
        .stPlotlyChart {{
            border-radius: 8px;
        }}

        /* ---- Divider subtlety ---- */
        [data-testid="stHorizontalRule"] {{
            opacity: 0.4;
        }}

        /* ---- Page nav icons in sidebar ---- */
        section[data-testid="stSidebar"] nav a span {{
            font-weight: 500;
        }}

        /* ---- Buttons ---- */
        .stButton > button {{
            border-radius: 6px;
            font-weight: 500;
            transition: all 0.15s ease;
        }}
        .stButton > button:hover {{
            transform: translateY(-1px);
            box-shadow: 0 2px 8px rgba(0,0,0,0.12);
        }}

        /* ---- Info/Warning/Success/Error boxes ---- */
        .stAlert {{
            border-radius: 8px;
        }}

        /* ---- Tab styling ---- */
        .stTabs [data-baseweb="tab"] {{
            font-weight: 500;
        }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
    return theme


def utilization_color(value, theme):
    """Return the appropriate theme color for a utilization percentage."""
    if value > 100:
        return theme["danger"]
    elif value >= 80:
        return theme["success"]
    elif value >= 50:
        return theme["warning"]
    else:
        return theme["light"]


def margin_color(value, theme):
    """Return success or danger color based on positive/negative margin."""
    return theme["success"] if value >= 0 else theme["danger"]


def section_header(title, description=None, icon=None):
    """Render a styled section header with optional icon and description."""
    icon_html = f'<span style="margin-right:8px;">{icon}</span>' if icon else ""
    desc_html = (
        f'<p style="margin:4px 0 0 0;font-size:0.88rem;opacity:0.6;">{description}</p>'
        if description else ""
    )
    st.markdown(
        f'<div style="margin-bottom:12px;">'
        f'<h3 style="margin:0;display:flex;align-items:center;">'
        f'{icon_html}{title}</h3>{desc_html}</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Sidebar settings UI
# ---------------------------------------------------------------------------

def theme_sidebar():
    """Render theme settings in the sidebar. Call from app.py."""
    theme = get_theme()

    with st.sidebar.expander("Theme Settings"):
        preset_names = list(PRESETS.keys())
        all_options = preset_names + ["Custom"]

        current_preset = theme.get("preset", "Default Blue")
        if current_preset in all_options:
            default_idx = all_options.index(current_preset)
        else:
            default_idx = 0

        preset = st.selectbox(
            "Preset",
            all_options,
            index=default_idx,
            key="_theme_preset",
        )

        if preset != "Custom" and preset in PRESETS:
            new_theme = {"preset": preset, **PRESETS[preset]}
        else:
            st.caption("Pick your colors:")
            col1, col2 = st.columns(2)
            with col1:
                primary = st.color_picker("Primary", theme["primary"], key="_tp_pri")
                success = st.color_picker("Success", theme["success"], key="_tp_suc")
                warning = st.color_picker("Warning", theme["warning"], key="_tp_wrn")
                danger = st.color_picker("Danger", theme["danger"], key="_tp_dng")
            with col2:
                bg = st.color_picker("Background", theme["background"], key="_tp_bg")
                sec_bg = st.color_picker("Sidebar BG", theme["secondary_bg"], key="_tp_sbg")
                text = st.color_picker("Text", theme["text"], key="_tp_txt")
                light = st.color_picker("Light Accent", theme["light"], key="_tp_lt")

            new_theme = {
                "preset": "Custom",
                "primary": primary,
                "success": success,
                "warning": warning,
                "danger": danger,
                "light": light,
                "background": bg,
                "secondary_bg": sec_bg,
                "text": text,
                "font": theme.get("font", "sans serif"),
            }

        # Font selector
        current_font = new_theme.get("font", "sans serif")
        font_idx = FONTS.index(current_font) if current_font in FONTS else 0
        font = st.selectbox("Font", FONTS, index=font_idx, key="_theme_font")
        new_theme["font"] = font

        # Color preview
        st.caption("Preview:")
        swatches = "".join(
            f'<div style="width:28px;height:28px;border-radius:4px;'
            f'background:{new_theme[c]};display:inline-block;margin:2px;" '
            f'title="{c}"></div>'
            for c in ("primary", "success", "warning", "danger", "light")
        )
        st.markdown(
            f'<div style="display:flex;gap:2px;flex-wrap:wrap;">{swatches}</div>',
            unsafe_allow_html=True,
        )

        if st.button("Apply Theme", use_container_width=True, key="_apply_theme"):
            save_theme(new_theme)
            st.session_state.app_theme = new_theme
            st.rerun()
