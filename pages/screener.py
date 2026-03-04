"""
Page 1 — Screener: Universe snapshot, quadrant chart, summary table, quick screens.

Universe-level view. Answers: "Where are the opportunities?"
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
import numpy as np

from data_loader import build_scored_dataset, load_benchmark, load_ai_analysis
from charts import build_quadrant_chart, PLOTLY_CONFIG, OXFORD_BLUE, RAG_COLOURS


def render_screener(weights: dict[str, float] | None = None) -> None:
    """Render the full screener page."""
    scored = build_scored_dataset(weights=None)
    benchmark_tsr = load_benchmark()
    ai_data = load_ai_analysis()
    mean_governance = scored["governance_score"].mean()

    # === (Bug 18) Universe Snapshot — moved to top ===
    st.markdown("#### Universe Snapshot")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Companies", len(scored))
    with m2:
        sweet = scored[
            (scored["governance_score"] > mean_governance)
            & (scored["tsr_3yr"] > benchmark_tsr)
        ]
        st.metric("Sweet Spot", len(sweet.dropna(subset=["tsr_3yr"])))
    with m3:
        underval = scored[scored["fgag_label"] == "Undervalued Quality"]
        st.metric("Undervalued Quality", len(underval))
    with m4:
        genuine = scored[scored["classification"] == "Genuine Structural Depth"]
        st.metric("Genuine Depth", len(genuine))

    # === Quick Screen Buttons ===
    st.markdown("---")
    st.markdown("#### Quick Screens")

    # Initialise state
    if "quick_screen" not in st.session_state:
        st.session_state["quick_screen"] = None

    qcol1, qcol2, qcol3, qcol4 = st.columns(4)
    with qcol1:
        if st.button("Top 5 Undervalued", use_container_width=True, key="qs_undervalued"):
            st.session_state["quick_screen"] = "undervalued"
            st.rerun()
        st.caption(
            "Top 5 companies where governance quality, growth, and value converge. "
            "Ranked by the **Female Governance Alpha Gap (FGAG)**, a 3-input composite: "
            "(1) Governance Score normalised to 0-1, (2) 3-Year TSR percentile "
            "rank within the universe, and (3) a value score (1 minus valuation "
            "percentile based on Forward P/E within sector). A high positive FGAG "
            "means strong governance + strong growth + attractive valuation."
        )
    with qcol2:
        if st.button("Sweet Spot", use_container_width=True, key="qs_sweet"):
            st.session_state["quick_screen"] = "sweet_spot"
            st.rerun()
        st.caption(
            "Companies in the top-right quadrant: above-average Female Governance "
            "Score AND above-benchmark 3-Year Total Shareholder Return."
        )
    with qcol3:
        if st.button("Genuine Depth", use_container_width=True, key="qs_genuine"):
            st.session_state["quick_screen"] = "genuine"
            st.rerun()
        st.caption(
            "Genuine Structural Depth — Companies where female board representation "
            "reflects real positional power (e.g., Board Chair, committee chairs) "
            "and strong retention rates. Requires Female Governance Composite Score >= 80 "
            "and Positional Power > 70."
        )
    with qcol4:
        if st.button("Show All", use_container_width=True, key="qs_all"):
            st.session_state["quick_screen"] = None
            st.rerun()
        st.caption("Remove all filters and show the full company universe.")

    # Apply quick screen filter
    display_df = scored.copy()
    active_screen = st.session_state.get("quick_screen")

    if active_screen == "undervalued":
        display_df = display_df[display_df["fgag_label"] == "Undervalued Quality"]
        display_df = display_df.nlargest(5, "fgag")
    elif active_screen == "sweet_spot":
        display_df = display_df[
            (display_df["governance_score"] > mean_governance)
            & (display_df["tsr_3yr"] > benchmark_tsr)
        ]
    elif active_screen == "genuine":
        display_df = display_df[
            display_df["classification"] == "Genuine Structural Depth"
        ]

    # Show active filter with factual explanation
    if active_screen:
        filter_explanations = {
            "undervalued": (
                "**Top 5 Undervalued Quality** — These companies have the highest "
                "Female Governance Alpha Gap (FGAG) scores. FGAG combines three inputs: "
                "governance quality, 3-year TSR growth rank, and sector-relative valuation. "
                "A high score means strong governance coinciding with strong growth at an "
                "attractive price. They represent potential mispricing opportunities."
            ),
            "sweet_spot": (
                "**Sweet Spot** — Companies with a Female Governance Composite Score above the "
                "universe average AND a 3-Year Total Shareholder Return above the "
                "NASDAQ-100 benchmark. These sit in the top-right quadrant of the chart: "
                "strong governance coinciding with strong returns."
            ),
            "genuine": (
                "**Genuine Structural Depth** — Companies where female board representation "
                "reflects real positional power (e.g., Board Chair, committee chairs) and strong "
                "retention rates. Requires composite score >= 80 and positional power > 70."
            ),
        }
        explanation = filter_explanations.get(active_screen, active_screen)
        st.info(f"{explanation}\n\n"
                f"Showing **{len(display_df)}** companies. Click **Show All** to reset.")

    # === Quadrant Chart — filters with quick screen selection ===
    st.markdown("---")

    # --- Y-axis view toggle ---
    view_option = st.radio(
        "Y-Axis Metric",
        ["3-Year Total Shareholder Return (%)", "Growth + Value Composite Score (0-100)"],
        horizontal=True,
        key="chart_y_toggle",
    )

    if view_option == "3-Year Total Shareholder Return (%)":
        y_col = "tsr_3yr"
        y_label = "3-Year Total Shareholder Return (%)"
        hline_label = "NASDAQ-100 Mean"
        y_format = ".1f"
        y_suffix = "%"
        benchmark_y = benchmark_tsr
        required_cols = ["tsr_3yr", "governance_score"]
    else:
        # Compute Growth + Value Composite: (TSR percentile + value score) / 2 * 100
        # TSR percentile: rank within universe; value score: 1 - valuation_percentile
        tsr_vals = scored["tsr_3yr"].dropna()
        if not tsr_vals.empty:
            scored["_tsr_pctile"] = scored["tsr_3yr"].rank(pct=True)
        else:
            scored["_tsr_pctile"] = np.nan
        scored["gv_composite"] = np.where(
            scored["_tsr_pctile"].notna() & scored["valuation_percentile"].notna(),
            (scored["_tsr_pctile"] + (1.0 - scored["valuation_percentile"])) / 2.0 * 100,
            np.nan,
        )
        # Re-apply to display_df (which is a copy/subset of scored)
        display_df = display_df.merge(
            scored[["ticker", "gv_composite"]],
            on="ticker", how="left", suffixes=("", "_new"),
        )
        if "gv_composite_new" in display_df.columns:
            display_df["gv_composite"] = display_df["gv_composite_new"]
            display_df.drop(columns=["gv_composite_new"], inplace=True)

        y_col = "gv_composite"
        y_label = "Growth + Value Composite Score (0-100)"
        hline_label = "Universe Mean"
        y_format = ".0f"
        y_suffix = "/100"
        benchmark_y = float(scored["gv_composite"].mean())
        required_cols = ["gv_composite", "governance_score"]

    chart_data = display_df.dropna(subset=required_cols)

    if not chart_data.empty:
        fig = build_quadrant_chart(
            chart_data, benchmark_y, mean_governance,
            y_col=y_col, y_label=y_label, hline_label=hline_label,
            y_format=y_format, y_suffix=y_suffix,
        )
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

        # (Bug 12) Axis tooltips — shown as expandable help
        with st.expander("How to read this chart", expanded=False):
            x_axis_help = (
                "**X-Axis — Female Governance Composite Score (0-100):** "
                "Weighted combination of Numeric Dominance (25%), Positional Power (43.75%), "
                "and Structural Depth (31.25%). Measures the quality and depth of female "
                "board representation, not just headcount. See individual company report for "
                "full details in the **Company Deep Dive** tab."
            )
            if y_col == "tsr_3yr":
                y_axis_help = (
                    "**Y-Axis — 3-Year Total Shareholder Return (%):** "
                    "Price-only return from Q1 2023 to Q4 2025: "
                    "`(price_end - price_start) / price_start x 100`.\n\n"
                    "**Dividing Lines:** Vertical = mean governance score across all companies "
                    "in this company universe. "
                    "Horizontal = NASDAQ-100 average 3-year TSR."
                )
            else:
                y_axis_help = (
                    "**Y-Axis — Growth + Value Composite Score (0-100):** "
                    "Combines two signals: (1) the company's TSR percentile rank within this "
                    "universe, and (2) a value score derived from how cheaply the stock trades "
                    "relative to its sector (1 minus valuation percentile). "
                    "Formula: `(TSR percentile + value score) / 2 x 100`. "
                    "A score of 75 means the company ranks well on both growth and value.\n\n"
                    "**Dividing Lines:** Vertical = mean governance score across all companies. "
                    "Horizontal = universe mean Growth + Value Composite."
                )
            st.markdown(
                f"{x_axis_help}\n\n{y_axis_help}\n\n---\n\n"
                "**The Four Quadrants:**\n\n"
                "- **Top-Right — Sweet Spot:** Strong female governance AND above-market returns. "
                "These companies combine governance quality with shareholder value.\n"
                "- **Top-Left — Returns Without Governance:** Above-market returns but below-average "
                "female governance. Strong financially but not supported by this governance thesis.\n"
                "- **Bottom-Right — Governance Without Returns:** Strong female governance but "
                "below-market returns. Good governance that has not yet translated into share price performance — "
                "potential future opportunity if the market re-rates.\n"
                "- **Bottom-Left — Neither:** Below-average governance and below-market returns. "
                "No governance edge and no financial outperformance.\n\n"
                "Use the **Top 5 Undervalued** quick screen above to find companies where "
                "governance quality is not yet reflected in the share price."
            )
    else:
        st.warning("No companies with both governance scores and Y-axis data.")

    # === AI Summary — explains categories clearly ===
    genuine_count = len(scored[scored["classification"] == "Genuine Structural Depth"])
    sweet_count = len(sweet.dropna(subset=["tsr_3yr"]))
    underval_count = len(underval)

    st.markdown(
        f"**Summary (AI driven):** Of {len(scored)} companies in this universe:\n\n"
        f"- **{sweet_count} sit in the Sweet Spot** (top-right quadrant) — these have "
        f"above-average female governance AND above-benchmark 3-year returns. "
        f"Use the **Sweet Spot** button above to filter to these.\n"
        f"- **{genuine_count} are classified as 'Genuine Structural Depth'** — women hold "
        f"real power roles (Board Chair, committee chairs) with strong retention, not just "
        f"headcount. This is a governance quality classification, independent of share price. "
        f"Use the **Genuine Depth** button above to filter.\n"
        f"- **{underval_count} show as 'Undervalued Quality'** — they score highly across all three "
        f"FGAG inputs: governance quality, shareholder returns, and sector-relative valuation. "
        f"These are potential mispricing opportunities. Use the **Top 5 Undervalued** button.\n\n"
        f"*These three screens overlap but measure different things: Sweet Spot = governance + returns, "
        f"Genuine Depth = governance quality, Undervalued = governance + growth + value.*"
    )

    # === Company Rankings Table (Bugs 14-17, 19) ===
    st.markdown("---")
    st.markdown("#### Company Rankings")
    st.caption(
        "Click any column header to sort. Use the filters below to narrow results. "
        "Select a row checkbox to navigate to that company's Deep Dive."
    )

    if display_df.empty:
        st.info("No companies match the current filter.")
        return

    # Build table columns
    table_cols = [
        "ticker", "company", "sector", "rag_label",
        "governance_score", "classification", "tsr_3yr", "fgag", "fgag_label",
    ]
    available = [c for c in table_cols if c in display_df.columns]
    table_df = display_df[available].copy()

    # Sort by FGAG descending
    if "fgag" in table_df.columns:
        table_df = table_df.sort_values("fgag", ascending=False, na_position="last")

    # Rename columns for display
    rename_map = {
        "ticker": "Ticker",
        "company": "Company",
        "sector": "Sector",
        "rag_label": "Female Board Representation",
        "governance_score": "Female Governance Composite Score",
        "classification": "AI Classification",
        "tsr_3yr": "3yr TSR (%)",
        "fgag": "Female Governance Alpha Gap",
        "fgag_label": "Signal",
    }
    table_df = table_df.rename(columns=rename_map)

    # --- Table Filters ---
    with st.expander("Filter Table", expanded=False):
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            sectors = sorted(table_df["Sector"].dropna().unique().tolist())
            sel_sectors = st.multiselect("Sector", sectors, default=[], key="filter_sector")
        with fc2:
            rag_opts = sorted(table_df["Female Board Representation"].dropna().unique().tolist())
            sel_rag = st.multiselect("Female Board Representation", rag_opts, default=[], key="filter_rag")
        with fc3:
            signal_opts = sorted(table_df["Signal"].dropna().unique().tolist())
            sel_signal = st.multiselect("Signal", signal_opts, default=[], key="filter_signal")

        if sel_sectors:
            table_df = table_df[table_df["Sector"].isin(sel_sectors)]
        if sel_rag:
            table_df = table_df[table_df["Female Board Representation"].isin(sel_rag)]
        if sel_signal:
            table_df = table_df[table_df["Signal"].isin(sel_signal)]

    st.caption(f"Showing {len(table_df)} of {len(display_df)} companies.")

    # Display table — show all rows with generous height
    event = st.dataframe(
        table_df,
        use_container_width=True,
        hide_index=True,
        height=min(len(table_df) * 38 + 40, 1200),
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "Ticker": st.column_config.TextColumn(
                width="small",
                help="Stock ticker symbol. Select a row to view the full company deep dive.",
            ),
            "Company": st.column_config.TextColumn(
                width="medium",
                help="Company name.",
            ),
            "Sector": st.column_config.TextColumn(
                help="Industry sector classification.",
            ),
            "Female Board Representation": st.column_config.TextColumn(
                help="Nil = no female board members. Minimal = 1-2 female. "
                     "Critical Mass = 3+ female board members. Majority = >50% female.",
            ),
            "Female Governance Composite Score": st.column_config.NumberColumn(
                format="%.1f",
                help="Female Governance Composite Score (0-100): Weighted combination of Numeric Dominance (25%), "
                     "Positional Power (43.75%), and Structural Depth (31.25%). Excludes financial pillar.",
            ),
            "AI Classification": st.column_config.TextColumn(
                width="medium",
                help="AI-generated governance classification: 'Genuine Structural Depth' (real power + retention), "
                     "'Cosmetic / Token Risk' (surface-level representation), or "
                     "'Insufficient Data / Neutral' (not enough signal to classify).",
            ),
            "3yr TSR (%)": st.column_config.NumberColumn(
                format="%.1f%%",
                help="3-Year Total Shareholder Return: (Q4 2025 price - Q1 2023 price) / Q1 2023 price x 100.",
            ),
            "Female Governance Alpha Gap": st.column_config.NumberColumn(
                format="%+.2f",
                help="Female Governance Alpha Gap (FGAG): 3-input composite combining "
                     "(1) Governance Score / 100, (2) 3-Year TSR percentile rank, and "
                     "(3) Value Score (1 - valuation percentile within sector). "
                     "Formula: (Gov + TSR rank + Value) / 3 x 2 - 1. "
                     "Range: -1 to +1. Positive = strong governance + growth + value. "
                     "Negative = weak governance, poor growth, or expensive valuation.",
            ),
            "Signal": st.column_config.TextColumn(
                width="medium",
                help="Trading signal derived from the Female Governance Alpha Gap (FGAG): "
                     "Undervalued Quality (>+0.4), Efficient Quality (+0.1 to +0.4), "
                     "Fair Value (-0.1 to +0.1), Overvalued vs. Governance (-0.4 to -0.1), "
                     "Governance Trap (<-0.4).",
            ),
        },
    )

    # Handle row selection — navigate to Company Deep Dive tab
    if event and event.selection and event.selection.rows:
        selected_row_idx = event.selection.rows[0]
        selected_ticker = table_df.iloc[selected_row_idx]["Ticker"]
        st.session_state["selected_ticker"] = selected_ticker
        company_name = table_df.iloc[selected_row_idx].get("Company", selected_ticker)
        st.success(
            f"Selected **{selected_ticker}** ({company_name}). "
            f"Click the **Company Deep Dive** tab above to view the full analysis."
        )
