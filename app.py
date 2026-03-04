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
# Frozen header — JS injection via components.html
#
# HOW STREAMLIT'S OWN HEADER WORKS (verified from source):
#   stApp         (position:absolute, overflow:hidden, fills viewport)
#   ├── header    (position:absolute, top:0)  ← OUTSIDE scroll container
#   └── section   (overflow:auto, height:100dvh) ← scroll container
#       └── content
#
# The header is a SIBLING of the scroll container, not inside it.
# That's why it never scrolls.  Our banner is INSIDE the scroll container,
# buried in nested wrappers.  No amount of overflow fixes can make
# position:sticky work reliably through that wrapper chain.
#
# Solution: use JS to CLONE our header elements, place the clones outside
# the scroll container (as siblings, like Streamlit does), hide the
# originals, and push the content down with padding.  Click handlers on
# tabs are re-wired by delegating clicks from clones to originals.
# ---------------------------------------------------------------------------
import streamlit.components.v1 as components
components.html(
    """
    <script>
    (function() {
        var doc = window.parent.document;

        function freezeHeader() {
            // Bail if already applied
            if (doc.getElementById('athena-frozen-header')) return true;

            var banner = doc.querySelector('.athena-banner');
            var tabList = doc.querySelector('[data-baseweb="tab-list"]');
            if (!banner || !tabList) return false;

            // Find the scroll container — it's the <section> ancestor with
            // overflow:auto (Streamlit calls it StyledAppViewMain).
            var scrollContainer = banner.closest('section[data-testid]');
            if (!scrollContainer) {
                // Fallback: walk up until we find overflow:auto
                var node = banner.parentElement;
                while (node && node !== doc.body) {
                    var ov = window.parent.getComputedStyle(node).overflowY;
                    if (ov === 'auto' || ov === 'scroll') {
                        scrollContainer = node;
                        break;
                    }
                    node = node.parentElement;
                }
            }
            if (!scrollContainer) return false;

            // Find the menu bar by walking direct children of the
            // stVerticalBlock.  st.markdown, st.columns, st.tabs etc.
            // each create different wrapper types, so we can't rely on
            // stElementContainer — instead we walk the parent block.
            var verticalBlock = banner.closest(
                '[data-testid="stVerticalBlock"]'
            );
            if (!verticalBlock) return false;

            // Find which direct child of verticalBlock contains the banner
            var bannerChild = banner;
            while (bannerChild && bannerChild.parentElement !== verticalBlock) {
                bannerChild = bannerChild.parentElement;
            }

            // The menu bar is built with st.columns, which creates a
            // stHorizontalBlock.  Look for that specifically — not 'button',
            // because Streamlit tabs are also <button> elements.
            var menuBar = null;
            if (bannerChild) {
                var sib = bannerChild.nextElementSibling;
                while (sib) {
                    if (sib.querySelector('[data-testid="stHorizontalBlock"]') ||
                        sib.getAttribute('data-testid') === 'stHorizontalBlock') {
                        menuBar = sib;
                        break;
                    }
                    sib = sib.nextElementSibling;
                }
            }

            // Also grab the top-level wrapper for collapsing later
            var bannerWrapper = banner.closest(
                '[data-testid="stVerticalBlockBorderWrapper"]'
            );

            // --- Build the frozen header container ---
            // Order: banner (top) → menu bar (middle) → tabs (bottom)
            var header = doc.createElement('div');
            header.id = 'athena-frozen-header';
            header.style.cssText =
                'position:absolute;top:0;left:0;right:0;z-index:999;' +
                'pointer-events:auto;';

            // 1. Clone the banner
            var bannerClone = banner.cloneNode(true);
            header.appendChild(bannerClone);

            // 2. Clone the menu bar
            if (menuBar) {
                var menuClone = menuBar.cloneNode(true);
                menuClone.style.background = 'white';
                header.appendChild(menuClone);

                // Wire menu clone clicks → originals
                var origBtns = menuBar.querySelectorAll('button');
                var cloneBtns = menuClone.querySelectorAll('button');
                cloneBtns.forEach(function(btn, i) {
                    btn.addEventListener('click', function(e) {
                        e.preventDefault();
                        e.stopPropagation();
                        if (origBtns[i]) origBtns[i].click();
                    });
                });
            }

            // 3. Clone the tab list (AFTER menu, so tabs appear at bottom)
            var tabClone = tabList.cloneNode(true);
            tabClone.style.setProperty('background', 'white', 'important');
            header.appendChild(tabClone);

            // Wire tab clone clicks → original tabs
            var origTabs = tabList.querySelectorAll('[data-baseweb="tab"]');
            var cloneTabs = tabClone.querySelectorAll('[data-baseweb="tab"]');
            cloneTabs.forEach(function(tab, i) {
                tab.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    if (origTabs[i]) origTabs[i].click();
                });
            });

            // --- Insert the frozen header BEFORE the scroll container ---
            // (as a sibling, exactly like Streamlit's own header)
            scrollContainer.parentElement.insertBefore(header, scrollContainer);

            // --- Measure header height and push content down ---
            var headerHeight = header.getBoundingClientRect().height;

            // Add top padding to the scroll container so content starts
            // below the frozen header
            var existingPadding = parseInt(
                window.parent.getComputedStyle(scrollContainer).paddingTop, 10
            ) || 0;
            scrollContainer.style.setProperty(
                'padding-top', headerHeight + 'px', 'important'
            );

            // --- Hide the originals inside the scroll container ---
            // (they still exist in the DOM for React, just invisible)
            banner.style.setProperty('visibility', 'hidden', 'important');
            banner.style.setProperty('height', '0', 'important');
            banner.style.setProperty('overflow', 'hidden', 'important');
            banner.style.setProperty('padding', '0', 'important');
            banner.style.setProperty('border', 'none', 'important');
            if (bannerWrapper) {
                bannerWrapper.style.setProperty('height', '0', 'important');
                bannerWrapper.style.setProperty('overflow', 'hidden', 'important');
                bannerWrapper.style.setProperty('min-height', '0', 'important');
            }
            if (menuBar) {
                menuBar.style.setProperty('visibility', 'hidden', 'important');
                menuBar.style.setProperty('height', '0', 'important');
                menuBar.style.setProperty('overflow', 'hidden', 'important');
                menuBar.style.setProperty('min-height', '0', 'important');
            }
            tabList.style.setProperty('visibility', 'hidden', 'important');
            tabList.style.setProperty('height', '0', 'important');
            tabList.style.setProperty('overflow', 'hidden', 'important');
            tabList.style.setProperty('padding', '0', 'important');

            // --- Sync active tab styling on clone when tabs switch ---
            var observer = new MutationObserver(function() {
                var freshOrigTabs = tabList.querySelectorAll('[data-baseweb="tab"]');
                var freshCloneTabs = tabClone.querySelectorAll('[data-baseweb="tab"]');
                freshOrigTabs.forEach(function(ot, i) {
                    if (freshCloneTabs[i]) {
                        freshCloneTabs[i].setAttribute(
                            'aria-selected',
                            ot.getAttribute('aria-selected') || 'false'
                        );
                    }
                });
            });
            observer.observe(tabList, {
                attributes: true, subtree: true, attributeFilter: ['aria-selected']
            });

            return true;
        }

        // Retry until DOM is ready
        var attempts = 0;
        var timer = setInterval(function() {
            if (freezeHeader() || ++attempts > 30) {
                clearInterval(timer);
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
