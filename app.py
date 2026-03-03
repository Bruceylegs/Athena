"""
Athena — Female Governance. Untapped Alpha.

Entry point: top banner, sub-navigation tabs, page routing, custom CSS.
No sidebar — all navigation in the top ribbon.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import streamlit as st

ASSETS_DIR = Path(__file__).parent / "assets"

# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------
favicon_path = ASSETS_DIR / "favicon.png"
st.set_page_config(
    page_title="Athena — Female Governance. Untapped Alpha.",
    page_icon=str(favicon_path) if favicon_path.exists() else "♀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Custom CSS — single injection point
# ---------------------------------------------------------------------------
MARINE_BLUE = "#052a4e"
OXFORD_BLUE = "#002147"
INDIGO = "#3B4B8A"

CSS = f"""
<style>
    /* Global font colour */
    html, body, [class*="css"] {{
        color: {OXFORD_BLUE} !important;
    }}

    /* Hide Streamlit defaults */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header[data-testid="stHeader"] {{display: none;}}

    /* Hide sidebar toggle button */
    [data-testid="collapsedControl"] {{display: none;}}

    /* Remove top padding from main content area (Bug 1 — dead white space) */
    .stMainBlockContainer {{
        padding-top: 0 !important;
    }}
    section[data-testid="stMain"] > div:first-child {{
        padding-top: 0 !important;
    }}

    /* Top banner — marine blue */
    .athena-banner {{
        display: flex;
        align-items: center;
        justify-content: flex-start;
        padding: 4px 0 4px 24px;
        background: {MARINE_BLUE};
        border-bottom: 3px solid {INDIGO};
        overflow: hidden;
    }}
    .athena-banner img {{
        height: 54px;
        width: auto;
        object-fit: contain;
        display: block;
    }}

    /* Metric labels */
    [data-testid="stMetricLabel"] {{
        color: {OXFORD_BLUE} !important;
    }}
    [data-testid="stMetricValue"] {{
        color: {OXFORD_BLUE} !important;
    }}

    /* Compact menu bar — remove gap between columns */
    .stMainBlockContainer > div > div > div:nth-child(2) .stColumns {{
        gap: 0 !important;
    }}

    /* Button styling */
    .stButton > button {{
        background-color: {MARINE_BLUE};
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
    }}
    .stButton > button:hover {{
        background-color: {OXFORD_BLUE};
        color: white;
    }}

    /* Dataframe header */
    .stDataFrame th {{
        background-color: {INDIGO} !important;
        color: white !important;
    }}

    /* Section dividers */
    hr {{
        border-top: 1px solid #E0E4E8;
    }}

    /* Selectbox */
    .stSelectbox label {{
        color: {OXFORD_BLUE} !important;
        font-weight: 600;
    }}

    /* Tooltip icon styling */
    span[title] {{
        cursor: help;
        color: {INDIGO};
        font-size: 0.9em;
    }}

    /* Tab styling to look like sub-ribbon */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0px;
        background-color: #F0F2F6;
        border-radius: 0;
        padding: 0 16px;
    }}
    .stTabs [data-baseweb="tab"] {{
        padding: 10px 24px;
        font-weight: 600;
        color: {OXFORD_BLUE};
        border-radius: 0;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: white;
        border-bottom: 3px solid {INDIGO};
        color: {INDIGO} !important;
    }}

    /* Multiselect pills — fix invisible text (Bug 8) */
    [data-baseweb="tag"] {{
        background-color: {INDIGO} !important;
    }}
    [data-baseweb="tag"] span {{
        color: white !important;
    }}

    /* Popover styling */
    .stPopover > div {{
        color: {OXFORD_BLUE};
    }}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Top Banner (Bug 1)
# ---------------------------------------------------------------------------
import base64


def _img_to_base64(path: Path) -> str:
    """Convert image file to base64 data URI for inline HTML."""
    if not path.exists():
        return ""
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    suffix = path.suffix.lower().strip(".")
    mime = "jpeg" if suffix in ("jpg", "jpeg") else "png"
    return f"data:image/{mime};base64,{data}"


logo_b64 = _img_to_base64(ASSETS_DIR / "logo_banner.jpg")

st.markdown(
    f"""
    <div class="athena-banner">
        <img src="{logo_b64}" alt="Athena">
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Menu Bar: Home | Export | About (Bug 1, 3)
# ---------------------------------------------------------------------------
menu_cols = st.columns([1, 1, 1, 1, 12])

with menu_cols[0]:
    if st.button("Home", use_container_width=True, key="nav_home"):
        st.session_state["quick_screen"] = None
        if "selected_ticker" in st.session_state:
            del st.session_state["selected_ticker"]
        st.rerun()

with menu_cols[1]:
    with st.popover("Export"):
        st.markdown("**Export Options**")
        st.markdown("- CSV *(coming soon)*")
        st.markdown("- Excel *(coming soon)*")
        st.markdown("- PDF *(coming soon)*")
        st.caption("Export functionality is a planned feature.")

with menu_cols[2]:
    with st.popover("About"):
        st.markdown("**About Athena**")
        st.markdown(
            "Athena is an investment-grade solution that identifies companies where "
            "meaningful female board representation coincides with shareholder returns.\n\n"
            "Athena's proprietary **Female Governance Alpha Gap (FGAG)** metric "
            "transforms qualitative governance analysis into a quantitative trading signal.\n\n"
            "***Female-led, sharper edge.***\n\n"
            "Data: 15 real + 35 synthetic companies.\n\n"
            "Built for Forward-Deployed AI Engineer challenge."
        )

with menu_cols[3]:
    with st.popover("Log Out"):
        st.markdown("**Log Out**")
        st.markdown("Authentication is a planned feature.")
        st.caption("In production, this would end your session and redirect to the login page.")


# ---------------------------------------------------------------------------
# Sub-Navigation Tabs (Bug 2)
# ---------------------------------------------------------------------------
tab_screener, tab_company = st.tabs(["Screener", "Company Deep Dive"])

# ---------------------------------------------------------------------------
# Sticky header — JS injection via components.html (same-origin iframe)
# Dynamically walks the DOM to find & fix the actual ancestor chain.
# ---------------------------------------------------------------------------
import streamlit.components.v1 as components
components.html(
    """
    <script>
    (function() {
        var doc = window.parent.document;

        // 1. Inject persistent CSS into parent <head> for overflow fixes.
        //    This survives Streamlit re-renders (unlike inline styles).
        if (!doc.getElementById('athena-sticky-css')) {
            var style = doc.createElement('style');
            style.id = 'athena-sticky-css';
            style.textContent =
                'section[data-testid="stMain"] > div,' +
                '[data-testid="stMainBlockContainer"],' +
                '[data-testid="stMainBlockContainer"] > div,' +
                '[data-testid="stVerticalBlockBorderWrapper"],' +
                '[data-testid="stVerticalBlockBorderWrapper"] > div,' +
                '[data-testid="stVerticalBlock"],' +
                '[data-testid="stElementContainer"],' +
                '[data-testid="stTabs"],' +
                '[data-testid="stTabs"] > div' +
                '{ overflow: visible !important; }';
            doc.head.appendChild(style);
        }

        // 2. Find elements and apply sticky positioning
        function applySticky() {
            var banner = doc.querySelector('.athena-banner');
            var tabList = doc.querySelector('[data-baseweb="tab-list"]');
            if (!banner || !tabList) return false;

            // Find banner's Streamlit block wrapper using closest()
            var bannerBlock = banner.closest(
                '[data-testid="stVerticalBlockBorderWrapper"]'
            );
            if (!bannerBlock) return false;

            // Menu wrapper = next sibling block after the banner block
            var menuBlock = bannerBlock.nextElementSibling;
            // Verify it's the menu (has buttons), not the tabs container
            if (menuBlock && !menuBlock.querySelector('[data-testid="stHorizontalBlock"]')
                         && !menuBlock.querySelector('.stButton')) {
                menuBlock = null;
            }

            // Apply sticky: banner block
            var cumTop = 0;
            bannerBlock.style.setProperty('position', 'sticky', 'important');
            bannerBlock.style.setProperty('top', '0px', 'important');
            bannerBlock.style.setProperty('z-index', '999', 'important');
            bannerBlock.style.setProperty('background', 'white', 'important');
            cumTop = bannerBlock.getBoundingClientRect().height;

            // Apply sticky: menu block
            if (menuBlock) {
                menuBlock.style.setProperty('position', 'sticky', 'important');
                menuBlock.style.setProperty('top', cumTop + 'px', 'important');
                menuBlock.style.setProperty('z-index', '998', 'important');
                menuBlock.style.setProperty('background', 'white', 'important');
                cumTop += menuBlock.getBoundingClientRect().height;
            }

            // Apply sticky: tab header bar ITSELF (not the tabs container)
            tabList.style.setProperty('position', 'sticky', 'important');
            tabList.style.setProperty('top', cumTop + 'px', 'important');
            tabList.style.setProperty('z-index', '997', 'important');

            return true;
        }

        // 3. Retry until DOM is ready, then re-apply periodically for re-renders
        var attempts = 0;
        var timer = setInterval(function() {
            if (applySticky() || ++attempts > 20) {
                clearInterval(timer);
                // Re-apply every 3s to handle Streamlit re-renders
                setInterval(applySticky, 3000);
            }
        }, 300);
    })();
    </script>
    """,
    height=0,
)

with tab_screener:
    from pages.screener import render_screener
    render_screener()

with tab_company:
    from pages.company import render_company_page
    render_company_page()
