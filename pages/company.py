"""
Page 2 — Company Deep Dive: single-ticker view with 3 main sections.

Sections: Company Overview, Female Governance, Corporate Financial Performance.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
import numpy as np

from data_loader import (
    build_scored_dataset,
    load_board_data,
    load_ai_analysis,
    load_valuations,
    get_company_financials,
    get_company_share_prices,
)
from charts import (
    build_board_donut,
    build_power_donut,
    build_share_price_chart,
    build_female_pct_sparkline,
    build_fgag_gauge,
    PLOTLY_CONFIG,
    OXFORD_BLUE,
    RAG_COLOURS,
    FGAG_COLOURS,
)

# Board diversity legislation summaries by jurisdiction
JURISDICTION_LEGISLATION = {
    # US states with mandates or disclosure requirements
    "California": "California SB 826 (2018) required publicly traded companies headquartered in the state to have at least one female director by end of 2019, and two or three (depending on board size) by end of 2021. Though struck down by courts in 2022, many companies voluntarily maintain compliance.",
    "Washington": "Washington HB 1116 (2020) requires public companies to have at least 25% female directors, with annual diversity disclosure requirements.",
    "Illinois": "Illinois HB 3394 requires publicly traded companies to report board demographics annually. No hard quota but strong disclosure pressure.",
    "New York": "New York S4278 requires studies on board diversity with annual disclosure. Encourages but does not mandate specific gender quotas.",
    "Maryland": "Maryland requires annual disclosure of board diversity statistics for publicly traded companies headquartered in the state.",
    "New Jersey": "New Jersey S3469 requires public companies to report board diversity annually, with recommendations for minimum representation targets.",
    # US states without specific mandates
    "Michigan": "Michigan does not currently have state-level board gender diversity mandate legislation.",
    "Texas": "Texas does not have state-level board gender diversity mandate legislation.",
    "Nebraska": "Nebraska does not have state-level board gender diversity mandate legislation.",
    "Massachusetts": "Massachusetts does not have a state-level board gender diversity mandate, though it has general anti-discrimination statutes.",
    "Georgia": "Georgia does not have state-level board gender diversity mandate legislation.",
    "Pennsylvania": "Pennsylvania does not have state-level board gender diversity mandate legislation.",
    "Connecticut": "Connecticut does not have state-level board gender diversity mandate legislation.",
    "Virginia": "Virginia does not have state-level board gender diversity mandate legislation.",
    "Nevada": "Nevada does not have state-level board gender diversity mandate legislation.",
    "Ohio": "Ohio does not have state-level board gender diversity mandate legislation.",
    "Oklahoma": "Oklahoma does not have state-level board gender diversity mandate legislation.",
    "Indiana": "Indiana does not have state-level board gender diversity mandate legislation.",
    "Wyoming": "Wyoming does not have state-level board gender diversity mandate legislation.",
    "Oregon": "Oregon does not have state-level board gender diversity mandate legislation.",
    "Kansas": "Kansas does not have state-level board gender diversity mandate legislation.",
    "Florida": "Florida does not have state-level board gender diversity mandate legislation.",
    "Idaho": "Idaho does not have state-level board gender diversity mandate legislation.",
    "Delaware": "Delaware does not have a state-level board gender diversity mandate, though most US public companies are incorporated here.",
    # International jurisdictions
    "Ireland": "Ireland is subject to the EU Women on Boards Directive (2022/2381), requiring listed companies to achieve 40% of non-executive director seats held by the under-represented gender by 30 June 2026, or 33% of all director seats.",
    "British Columbia": "British Columbia (Canada) introduced disclosure-based requirements under the BC Business Corporations Act. Companies must disclose board diversity policies and the number of female directors annually. There is no mandatory quota.",
}

POWER_ROLE_NAMES = [
    "Board Chair",
    "Lead Independent Director",
    "Audit Committee Chair",
    "Compensation Committee Chair",
    "Governance/Nominating Committee Chair",
]


def _ucfirst(s: str) -> str:
    """Uppercase only the first character, preserving the rest."""
    if not s:
        return s
    return s[0].upper() + s[1:]


def _capitalise_sentences(text: str) -> str:
    """Capitalise the first letter of every sentence in the text."""
    if not text:
        return text
    parts = text.split(". ")
    return ". ".join(_ucfirst(p) for p in parts)


def _is_mandate(val) -> bool:
    """Safely check if in_mandate_jurisdiction is truthy (handles string 'Yes'/'No')."""
    if isinstance(val, str):
        return val.strip().lower() in ("yes", "true", "1")
    return bool(val)


def _rag_badge_html(colour: str, label: str) -> str:
    """Return HTML for a RAG status pill badge."""
    bg = RAG_COLOURS.get(colour, "#ADB5BD")
    return (
        f'<span style="background:{bg}; color:#FFFFFF; padding:4px 12px; '
        f'border-radius:12px; font-weight:600; font-size:0.85em;">'
        f'Female Representation: {label}</span>'
    )


def _signal_badge_html(label: str) -> str:
    """Return HTML for FGAG trading signal badge."""
    bg = FGAG_COLOURS.get(label, "#ADB5BD")
    return (
        f'<span style="background:{bg}; color:#FFFFFF; padding:4px 12px; '
        f'border-radius:12px; font-weight:600; font-size:0.85em;">{label}</span>'
    )


def _eps_consistency(vals: list) -> str:
    """Assess year-on-year EPS consistency."""
    if len(vals) < 3:
        return ""
    increases = sum(1 for i in range(1, len(vals)) if vals[i] > vals[i - 1])
    decreases = sum(1 for i in range(1, len(vals)) if vals[i] < vals[i - 1])
    periods = len(vals) - 1
    if increases == periods:
        return "EPS grew consistently in every year of the period"
    if decreases == periods:
        return "EPS declined in every year, a persistent downward trend"
    if increases >= periods - 1:
        return "EPS was largely consistent with only one year of decline"
    return f"EPS was inconsistent, rising in {increases} years and falling in {decreases}"


def _rev_consistency(vals: list) -> str:
    """Assess year-on-year Revenue consistency."""
    if len(vals) < 3:
        return ""
    increases = sum(1 for i in range(1, len(vals)) if vals[i] > vals[i - 1])
    decreases = sum(1 for i in range(1, len(vals)) if vals[i] < vals[i - 1])
    periods = len(vals) - 1
    if increases == periods:
        return "Revenue grew every year, demonstrating consistent top-line momentum"
    if decreases == periods:
        return "Revenue declined every year, a sustained contraction"
    if increases >= periods - 1:
        return "Revenue growth was largely consistent with only one year of contraction"
    return f"Revenue growth was mixed, expanding in {increases} years and contracting in {decreases}"


def _generate_financial_summary(ticker: str, fin_table, tsr_3yr) -> str:
    """Generate a data-driven financial performance summary."""
    if fin_table is None or fin_table.empty:
        return "Insufficient financial data for analysis."

    parts = []

    # EPS analysis
    eps_col = "EPS ($)"
    if eps_col in fin_table.columns:
        eps_vals = fin_table[eps_col].dropna().tolist()
        if len(eps_vals) >= 2:
            first, last = eps_vals[0], eps_vals[-1]
            if first and last and abs(first) > 0.01:
                eps_change = ((last - first) / abs(first)) * 100
                if eps_change > 10:
                    parts.append(f"EPS grew {eps_change:.0f}% over the 5-year period ({first:.2f} to {last:.2f}), indicating strengthening profitability")
                elif eps_change < -10:
                    parts.append(f"EPS declined {abs(eps_change):.0f}% over the 5-year period ({first:.2f} to {last:.2f}), signalling weakening earnings")
                else:
                    parts.append(f"EPS was broadly flat over the 5-year period ({first:.2f} to {last:.2f})")
            # Consistency
            consistency = _eps_consistency(eps_vals)
            if consistency:
                parts.append(consistency)

    # Revenue analysis
    rev_col = "Revenue ($B)"
    if rev_col in fin_table.columns:
        rev_vals = fin_table[rev_col].dropna().tolist()
        if len(rev_vals) >= 2:
            first, last = rev_vals[0], rev_vals[-1]
            if first and last and first > 0:
                rev_change = ((last - first) / first) * 100
                if rev_change > 10:
                    parts.append(f"Revenue grew {rev_change:.0f}% ({first:.1f}B to {last:.1f}B), showing top-line expansion")
                elif rev_change < -10:
                    parts.append(f"Revenue declined {abs(rev_change):.0f}% ({first:.1f}B to {last:.1f}B), a contraction concern")
                else:
                    parts.append(f"Revenue was relatively stable ({first:.1f}B to {last:.1f}B)")
            consistency = _rev_consistency(rev_vals)
            if consistency:
                parts.append(consistency)

    # Share price / TSR link
    if pd.notna(tsr_3yr):
        if tsr_3yr > 30:
            parts.append(f"the 3-year TSR of {tsr_3yr:.1f}% suggests the market has rewarded this financial trajectory")
        elif tsr_3yr > 0:
            parts.append(f"a modest 3-year TSR of {tsr_3yr:.1f}% suggests the market has partially priced in these fundamentals")
        else:
            parts.append(f"a negative 3-year TSR of {tsr_3yr:.1f}% indicates the share price has not reflected the underlying financials")

    return _capitalise_sentences(". ".join(parts)) + "." if parts else "Insufficient data for financial analysis."


def _generate_depth_summary(row, board_row) -> str:
    """Generate a data-driven structural depth summary."""
    parts = []
    ret_rate = row.get("retention_rate")
    fc23 = int(board_row.get("female_count_2023", 0))
    fc25 = int(board_row.get("female_count_2025", 0))
    in_mandate = _is_mandate(board_row.get("in_mandate_jurisdiction", False))
    jurisdiction = str(board_row.get("jurisdiction", "")).strip()

    if pd.notna(ret_rate) and ret_rate > 0:
        if ret_rate >= 80:
            parts.append(f"{ret_rate:.0f}% of female directors from 3 years ago are still serving, indicating strong commitment and stability")
        elif ret_rate >= 50:
            parts.append(f"{ret_rate:.0f}% 3-year retention suggests moderate board stability with some turnover")
        else:
            parts.append(f"Only {ret_rate:.0f}% 3-year retention raises questions about whether female appointments are sustained")

    if fc23 > 0 and fc25 > 0:
        if fc25 > fc23:
            parts.append(f"Female representation grew from {fc23} to {fc25} directors over 3 years, showing an upward trajectory")
        elif fc25 < fc23:
            parts.append(f"Female representation declined from {fc23} to {fc25} directors, a concerning reversal")
        else:
            parts.append(f"Female representation held steady at {fc25} directors over the period")

    if in_mandate and jurisdiction:
        legislation = JURISDICTION_LEGISLATION.get(jurisdiction, "")
        if legislation:
            parts.append(f"The company is headquartered in {jurisdiction}, which has board diversity requirements ({legislation.split('.')[0]})")
        else:
            parts.append(f"The company is headquartered in {jurisdiction}, which has board diversity legislation")
    elif jurisdiction:
        no_mandate_text = JURISDICTION_LEGISLATION.get(jurisdiction, "")
        if no_mandate_text and "does not" in no_mandate_text.lower():
            parts.append(f"The company is headquartered in {jurisdiction}, which does not have a board gender diversity mandate, suggesting female appointments are voluntary")
        else:
            parts.append(f"The company is headquartered in {jurisdiction}, which does not have a mandatory board gender diversity quota, suggesting female appointments are voluntary")

    return _capitalise_sentences(". ".join(parts)) + "." if parts else "Insufficient data for structural depth analysis."


def _generate_trading_summary(row) -> str:
    """Generate a data-driven trading signal summary."""
    fgag = row.get("fgag")
    gov_score = row.get("governance_score", 0)
    tsr_3yr = row.get("tsr_3yr")
    fgag_label = row.get("fgag_label", "N/A")

    if not pd.notna(fgag):
        return "Insufficient data for FGAG analysis."

    parts = []

    if gov_score >= 70:
        parts.append(f"a Female Governance Composite Score of {gov_score:.0f}/100 places this company in the upper tier of the universe")
    elif gov_score >= 40:
        parts.append(f"a Female Governance Composite Score of {gov_score:.0f}/100 represents mid-range governance quality")
    else:
        parts.append(f"a Female Governance Composite Score of {gov_score:.0f}/100 indicates limited governance depth")

    if pd.notna(tsr_3yr):
        if tsr_3yr > 50:
            parts.append(f"strong 3-year shareholder returns of {tsr_3yr:.1f}% contribute positively to the growth component")
        elif tsr_3yr > 0:
            parts.append(f"moderate 3-year returns of {tsr_3yr:.1f}% provide a neutral growth signal")
        else:
            parts.append(f"negative 3-year returns of {tsr_3yr:.1f}% weigh on the growth component")

    parts.append(f"these combine for an FGAG of {fgag:+.2f} ({fgag_label})")

    if fgag > 0.4:
        parts.append("the investment case is strong — governance quality significantly exceeds market pricing, suggesting an undervalued opportunity")
    elif fgag > 0.1:
        parts.append("governance quality is roughly reflected in the current valuation — a core holding if the governance trajectory continues improving")
    elif fgag > -0.1:
        parts.append("the stock appears fairly valued relative to its governance profile — no clear mispricing signal")
    elif fgag > -0.4:
        parts.append("the market is pricing the stock at a premium relative to governance quality — caution warranted")
    else:
        parts.append("high valuation relative to weak governance signals significant risk — a governance trap to avoid")

    return _capitalise_sentences(". ".join(parts)) + "."


def render_company_page() -> None:
    """Render the company deep-dive page."""
    scored = build_scored_dataset()
    board = load_board_data()
    ai_data = load_ai_analysis()
    valuations = load_valuations()

    # Universe averages for comparison (Bug 8)
    universe_female_pct = scored["female_pct"].mean()
    universe_board_size = scored["board_size"].mean()

    # Company selector
    options = scored.apply(
        lambda r: f"{r['ticker']} — {r.get('company', r['ticker'])}", axis=1
    ).tolist()

    if "selected_ticker" in st.session_state:
        target = st.session_state["selected_ticker"]
        for opt in options:
            if opt.startswith(target + " "):
                st.session_state["company_selector"] = opt
                break

    selected = st.selectbox("Select Company", options, key="company_selector")

    ticker = selected.split(" — ")[0].strip()
    row = scored[scored["ticker"] == ticker].iloc[0]
    board_row = board[board["ticker"] == ticker].iloc[0]
    ai = ai_data.get(ticker, {})
    val_row = valuations[valuations["ticker"] == ticker]
    val_data = val_row.iloc[0] if not val_row.empty else {}

    # ===================================================================
    # SECTION 1: Company Overview
    # ===================================================================
    st.markdown("---")
    st.markdown("#### Company Overview")

    gov_score = row["governance_score"]
    p4 = row.get("p4_financial_impact", 0)
    composite = row["composite_score"]
    female_pct_val = row.get("female_pct", 0)
    board_size_val = int(row.get("board_size", 0))
    ret_rate = row.get("retention_rate")
    ret_display = f"{ret_rate:.0f}%" if pd.notna(ret_rate) and ret_rate else "N/A"
    sector_val = row.get("sector", "N/A")

    # Render entire overview as a single aligned HTML block — Bug 4: uniform format
    overview_html = f"""
    <div style="padding:8px 0;">
        <div style="display:flex; justify-content:center; gap:40px; flex-wrap:wrap;">
            <div style="text-align:center; min-width:120px;">
                <div style="font-size:2.2em; font-weight:700; color:{OXFORD_BLUE};">{gov_score:.0f}</div>
                <div style="font-size:0.8em; color:#6C757D;">Female Governance<br>Composite Score</div>
            </div>
            <div style="text-align:center; min-width:120px;">
                <div style="font-size:2.2em; font-weight:700; color:{OXFORD_BLUE};">{p4:.0f}</div>
                <div style="font-size:0.8em; color:#6C757D;">Financial Performance<br>Score</div>
            </div>
            <div style="text-align:center; min-width:120px;">
                <div style="font-size:2.2em; font-weight:700; color:{OXFORD_BLUE};">{composite:.0f}</div>
                <div style="font-size:0.8em; color:#6C757D;">Overall Holistic<br>Composite Score</div>
            </div>
            <div style="text-align:center; min-width:100px;">
                <div style="font-size:2.2em; font-weight:700; color:{OXFORD_BLUE};">{female_pct_val:.0f}%</div>
                <div style="font-size:0.8em; color:#6C757D;">Female %</div>
            </div>
            <div style="text-align:center; min-width:100px;">
                <div style="font-size:2.2em; font-weight:700; color:{OXFORD_BLUE};">{board_size_val}</div>
                <div style="font-size:0.8em; color:#6C757D;">Board Size</div>
            </div>
            <div style="text-align:center; min-width:100px;">
                <div style="font-size:2.2em; font-weight:700; color:{OXFORD_BLUE};">{ret_display}</div>
                <div style="font-size:0.8em; color:#6C757D;">3-yr Retention</div>
            </div>
            <div style="text-align:center; min-width:100px;">
                <div style="font-size:2.2em; font-weight:700; color:{OXFORD_BLUE};">{sector_val}</div>
                <div style="font-size:0.8em; color:#6C757D;">Sector</div>
            </div>
        </div>
    </div>
    """
    st.markdown(overview_html, unsafe_allow_html=True)

    # ===================================================================
    # SECTION 2: Female Governance (merged Board Composition + Structural Depth)
    # ===================================================================
    st.markdown("---")
    st.markdown("### Female Governance")

    # --- Sub-section: Board Composition --- (Bug 3: RAG pill adjacent to heading)
    rag_html = _rag_badge_html(row["rag_status"], row["rag_label"])
    st.markdown(
        "#### Board Composition &nbsp;"
        '<span title="Measures female headcount (Numeric Dominance) and the 5 key '
        "Positional Power roles held by women: Board Chair, Lead Independent Director, "
        "Audit Committee Chair, Compensation Committee Chair, and "
        'Governance/Nominating Committee Chair.">&#9432;</span>'
        f"&nbsp;&nbsp;{rag_html}",
        unsafe_allow_html=True,
    )

    p1_score = row["p1_numeric_dominance"]
    p2_score = row["p2_positional_power"]
    st.markdown(
        f"**Numeric Dominance:** {p1_score:.0f}/100 &nbsp;&nbsp; "
        f"**Positional Power:** {p2_score:.0f}/100"
    )

    bc1, bc2, bc3 = st.columns([3, 2, 2])
    with bc1:
        role_cols = {
            "board_chair_gender": "Board Chair",
            "lead_independent_gender": "Lead Independent Director",
            "audit_chair_gender": "Audit Committee Chair",
            "comp_chair_gender": "Compensation Committee Chair",
            "gov_nom_chair_gender": "Governance/Nominating Committee Chair",
        }
        name_cols = {
            "board_chair_gender": "board_chair_name",
            "lead_independent_gender": "lead_independent_name",
            "audit_chair_gender": "audit_chair_name",
            "comp_chair_gender": "comp_chair_name",
            "gov_nom_chair_gender": "gov_nom_chair_name",
        }

        board_members = []
        female_power_count = 0
        male_power_count = 0
        for col, role_name in role_cols.items():
            gender = board_row.get(col, "Unknown")
            if pd.isna(gender):
                gender = "Unknown"
            name = board_row.get(name_cols[col], "—")
            if pd.isna(name):
                name = "—"
            board_members.append({
                "Role": f"**{role_name}**",
                "Name": str(name),
                "Gender": str(gender),
                "_power": True,
            })
            if str(gender).lower() == "female":
                female_power_count += 1
            elif str(gender).lower() == "male":
                male_power_count += 1

        # Fill remaining seats as Non-Executive Directors
        board_size = int(row.get("board_size", 0))
        female_count = int(row.get("female_count", 0))
        remaining = max(board_size - len(role_cols), 0)
        unique_female_power = min(female_power_count, female_count)
        remaining_female = max(female_count - unique_female_power, 0)
        remaining_male = max(remaining - remaining_female, 0)

        # Read NED names from CSV if available
        ned_names_raw = board_row.get("ned_names", "")
        ned_names_list = []
        if isinstance(ned_names_raw, str) and ned_names_raw.strip():
            ned_names_list = [n.strip() for n in ned_names_raw.split("|") if n.strip()]

        ned_idx = 0
        for _ in range(remaining_female):
            name = ned_names_list[ned_idx] if ned_idx < len(ned_names_list) else "—"
            ned_idx += 1
            board_members.append({"Role": "Non-Executive Director", "Name": name, "Gender": "Female", "_power": False})
        for _ in range(remaining_male):
            name = ned_names_list[ned_idx] if ned_idx < len(ned_names_list) else "—"
            ned_idx += 1
            board_members.append({"Role": "Non-Executive Director", "Name": name, "Gender": "Male", "_power": False})

        # Build HTML table so power roles render in bold
        _html_rows = []
        for m in board_members:
            role_txt = m["Role"]
            is_power = m.get("_power", False)
            if is_power:
                role_txt = role_txt.replace("**", "")  # strip markdown
                role_cell = f"<b>{role_txt}</b>"
            else:
                role_cell = role_txt.replace("**", "")
            _html_rows.append(
                f"<tr><td style='padding:6px 10px;'>{role_cell}</td>"
                f"<td style='padding:6px 10px;'>{m['Name']}</td>"
                f"<td style='padding:6px 10px;'>{m['Gender']}</td></tr>"
            )
        _table_html = (
            "<div style='max-height:500px; overflow-y:auto;'>"
            "<table style='width:100%; border-collapse:collapse; font-size:0.9em;'>"
            "<thead><tr style='background:#052a4e; color:white;'>"
            "<th style='padding:8px 10px; text-align:left;'>Role</th>"
            "<th style='padding:8px 10px; text-align:left;'>Name</th>"
            "<th style='padding:8px 10px; text-align:left;'>Gender</th>"
            "</tr></thead><tbody>"
        )
        for i, r in enumerate(_html_rows):
            bg = "#f8f9fa" if i % 2 == 0 else "white"
            _table_html += r.replace("<tr>", f"<tr style='background:{bg};'>")
        _table_html += "</tbody></table></div>"
        st.markdown(_table_html, unsafe_allow_html=True)

    with bc2:
        female_c = int(row.get("female_count", 0))
        male_c = int(row.get("board_size", 0)) - female_c
        fig = build_board_donut(female_c, max(male_c, 0))
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
        st.caption("Board Composition")

    with bc3:
        fig = build_power_donut(female_power_count, male_power_count)
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
        st.caption("Power Role Split")

    # Board summary — compare to universe (Bug 8)
    female_pct = row.get("female_pct", 0)
    pct_diff = female_pct - universe_female_pct
    pct_comparison = (
        f"above the universe average of {universe_female_pct:.0f}%"
        if pct_diff > 1
        else f"below the universe average of {universe_female_pct:.0f}%"
        if pct_diff < -1
        else f"in line with the universe average of {universe_female_pct:.0f}%"
    )

    # Compute universe average power roles held by women
    power_gender_cols = ["board_chair_gender", "audit_chair_gender", "comp_chair_gender", "gov_nom_chair_gender", "lead_independent_gender"]
    avg_power = board[power_gender_cols].apply(lambda col: (col.str.lower() == "female").sum()).sum() / len(board)

    # Count unique female directors holding power roles (by name)
    power_name_cols = {
        "board_chair_gender": "board_chair_name",
        "lead_independent_gender": "lead_independent_name",
        "audit_chair_gender": "audit_chair_name",
        "comp_chair_gender": "comp_chair_name",
        "gov_nom_chair_gender": "gov_nom_chair_name",
    }
    unique_female_power_names = set()
    for gcol, ncol in power_name_cols.items():
        if str(board_row.get(gcol, "")).lower() == "female":
            name = str(board_row.get(ncol, "")).strip()
            if name and name != "—":
                unique_female_power_names.add(name)
    unique_female_in_power = len(unique_female_power_names)

    board_summary = (
        f"{female_c} of {board_size} directors are female ({female_pct:.0f}%), "
        f"{pct_comparison}. "
        f"Women hold {female_power_count} of 5 key governance roles "
        f"(vs. a universe average of {avg_power:.1f}). "
    )
    if female_power_count > unique_female_in_power and unique_female_in_power > 0:
        board_summary += (
            f"Note: {unique_female_in_power} female director{'s' if unique_female_in_power > 1 else ''} "
            f"hold{'s' if unique_female_in_power == 1 else ''} {female_power_count} roles, "
            f"meaning individual directors chair multiple committees. "
        )

    st.markdown(
        f'<div style="background:#f8f9fa; border-left:4px solid #3B4B8A; padding:10px 16px; '
        f'margin:8px 0; font-size:0.92em;">'
        f'<strong>Summary (AI driven):</strong> <em>{board_summary}</em></div>',
        unsafe_allow_html=True,
    )

    # --- Sub-section: Structural Depth & Retention ---
    st.markdown("")
    st.markdown(
        "#### Structural Depth & Retention &nbsp;"
        '<span title="Evaluates whether female board representation is sustained '
        'and deepening over time. Key inputs: 3-year retention rate (percentage of '
        'female directors from 3 years ago still serving today) and the '
        'year-over-year representation trend.">&#9432;</span>',
        unsafe_allow_html=True,
    )

    p3_score = row["p3_structural_depth"]
    st.markdown(f"**Structural Depth Score:** {p3_score:.0f}/100")

    sd1, sd2 = st.columns([2, 3])
    with sd1:
        # Mandate flag with legislation detail
        jurisdiction = str(board_row.get("jurisdiction", "")).strip()
        has_mandate = _is_mandate(board_row.get("in_mandate_jurisdiction", False))
        legislation_detail = JURISDICTION_LEGISLATION.get(jurisdiction, "")

        if has_mandate and jurisdiction:
            st.markdown(
                f'<div style="background:#FFF3CD; padding:10px 16px; border-radius:8px; '
                f'border-left:4px solid #E6A800; margin:8px 0;">'
                f'<strong>Mandate Jurisdiction: {jurisdiction}</strong><br>'
                f'<span style="font-size:0.85em;">{legislation_detail}</span></div>',
                unsafe_allow_html=True,
            )
        elif jurisdiction:
            no_mandate_text = legislation_detail if legislation_detail else (
                f"{jurisdiction} does not have state-level board gender diversity mandate legislation."
            )
            st.markdown(
                f'<div style="background:#D4EDDA; padding:10px 16px; border-radius:8px; '
                f'border-left:4px solid #1B7A3D; margin:8px 0;">'
                f'<strong>Jurisdiction: {jurisdiction}</strong><br>'
                f'<span style="font-size:0.85em;">{no_mandate_text}</span></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="background:#D4EDDA; padding:10px 16px; border-radius:8px; '
                'border-left:4px solid #1B7A3D; margin:8px 0;">'
                '<strong>No Mandate Jurisdiction</strong><br>'
                '<span style="font-size:0.85em;">This company is not subject to board '
                'diversity mandates. Female appointments are voluntary.</span></div>',
                unsafe_allow_html=True,
            )

    with sd2:
        fc23 = float(board_row.get("female_count_2023", 0))
        fc24 = float(board_row.get("female_count_2024", 0))
        fc25 = float(board_row.get("female_count_2025", 0))
        bs = max(float(board_row.get("board_size", 1)), 1)

        pct23 = (fc23 / bs) * 100
        pct24 = (fc24 / bs) * 100
        pct25 = (fc25 / bs) * 100

        st.markdown("**Female Board % Trend (3-Year)**")
        fig = build_female_pct_sparkline(pct23, pct24, pct25, ticker)
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

        st.markdown(
            f"**Director Count:** {int(fc23)} ({pct23:.0f}%) in 2023 → "
            f"{int(fc24)} ({pct24:.0f}%) in 2024 → "
            f"{int(fc25)} ({pct25:.0f}%) in 2025"
        )

    depth_summary = _generate_depth_summary(row, board_row)
    st.markdown(
        f'<div style="background:#f8f9fa; border-left:4px solid #3B4B8A; padding:10px 16px; '
        f'margin:8px 0; font-size:0.92em;">'
        f'<strong>Summary (AI driven):</strong> <em>{depth_summary}</em></div>',
        unsafe_allow_html=True,
    )

    # ===================================================================
    # SECTION 3: Corporate Financial Performance (merged Financial + Trading Signal)
    # ===================================================================
    st.markdown("---")
    st.markdown("### Corporate Financial Performance")

    # --- Sub-section: Financial Performance ---
    st.markdown(
        "#### Financial Performance (2021-2025) &nbsp;"
        '<span title="Details the Earnings Per Share and Revenue performance over the '
        "most recent 5 years based on the company's official SEC filing."
        '">&#9432;</span>',
        unsafe_allow_html=True,
    )

    p4_score = row["p4_financial_impact"]
    st.markdown(f"**Profit and Sales Performance:** {p4_score:.0f}/100")

    fin_table = get_company_financials(ticker)
    if fin_table is not None:
        st.dataframe(fin_table, use_container_width=True, hide_index=True)

    prices = get_company_share_prices(ticker)
    if prices is not None and not prices.empty:
        fig = build_share_price_chart(prices, ticker)
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    tsr_3yr = row.get("tsr_3yr")
    fin_summary = _generate_financial_summary(ticker, fin_table, tsr_3yr)
    st.markdown(
        f'<div style="background:#f8f9fa; border-left:4px solid #3B4B8A; padding:10px 16px; '
        f'margin:8px 0; font-size:0.92em;">'
        f'<strong>Summary (AI driven):</strong> <em>{fin_summary}</em></div>',
        unsafe_allow_html=True,
    )

    # --- Sub-section: Trading Signal — Female Governance Alpha Gap ---
    st.markdown("")
    st.markdown(
        "#### Trading Signal — Female Governance Alpha Gap &nbsp;"
        '<span title="The FGAG combines three inputs to identify companies where '
        "governance quality, growth, and value converge: (1) Female Governance "
        "Composite Score as a percentage, (2) 3-Year TSR ranked against all other "
        "companies in the universe, and (3) how cheaply the stock trades relative "
        "to its sector based on Forward P/E. A positive score means strong governance "
        'at an attractive price with solid returns.">&#9432;</span>',
        unsafe_allow_html=True,
    )

    ts1, ts2 = st.columns([2, 3])
    with ts1:
        fgag = row.get("fgag")
        fgag_label = row.get("fgag_label", "N/A")

        if fgag is not None and pd.notna(fgag):
            st.markdown(
                _signal_badge_html(fgag_label),
                unsafe_allow_html=True,
            )
            st.markdown("")

            gov_score = row["governance_score"]
            tsr_3yr_val = row.get("tsr_3yr")
            fwd_pe = val_data.get("forward_pe", "N/A") if isinstance(val_data, dict) else getattr(val_data, "forward_pe", "N/A")
            val_pctile_raw = val_data.get("valuation_percentile", "N/A") if isinstance(val_data, dict) else getattr(val_data, "valuation_percentile", "N/A")

            tsr_display = f"{tsr_3yr_val:.1f}%" if pd.notna(tsr_3yr_val) else "N/A"
            val_display = val_pctile_raw if isinstance(val_pctile_raw, str) else f"{val_pctile_raw:.0%}"

            st.markdown(
                f"**Female Governance Composite Score:** {gov_score:.0f}/100 "
                f"*(see Female Governance section above)*  \n"
                f"**3-Year TSR:** {tsr_display}  \n"
                f"**Forward P/E:** {fwd_pe}x  \n"
                f"**Valuation Percentile:** {val_display}"
            )
        else:
            st.markdown("*Insufficient data for Female Governance Alpha Gap calculation.*")

    with ts2:
        if fgag is not None and pd.notna(fgag):
            fig = build_fgag_gauge(float(fgag), fgag_label)
            st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
            # Segment legend below gauge
            st.markdown(
                '<div style="display:flex; justify-content:center; gap:6px; flex-wrap:wrap; '
                'font-size:0.75em; margin-top:-8px;">'
                '<span style="background:#FADBD8; color:#B03A2E; padding:2px 8px; border-radius:4px; font-weight:600;">Governance Trap (&lt;-0.4)</span>'
                '<span style="background:#FCE4B8; color:#B8860B; padding:2px 8px; border-radius:4px; font-weight:600;">Overvalued (-0.4 to -0.1)</span>'
                '<span style="background:#E8E8E8; color:#555; padding:2px 8px; border-radius:4px; font-weight:600;">Fair Value (-0.1 to 0.1)</span>'
                '<span style="background:#D4E6F1; color:#2E6DA4; padding:2px 8px; border-radius:4px; font-weight:600;">Efficient Quality (0.1 to 0.4)</span>'
                '<span style="background:#D5F5E3; color:#1B7A3D; padding:2px 8px; border-radius:4px; font-weight:600;">Undervalued Quality (&gt;0.4)</span>'
                '</div>',
                unsafe_allow_html=True,
            )

    # Catalyst badge
    catalyst = row.get("catalyst")
    if catalyst and pd.notna(catalyst):
        st.markdown(
            f'<div style="background:#D4EDDA; padding:10px 16px; border-radius:8px; '
            f'border-left:4px solid #1B7A3D; margin:8px 0;">'
            f'<strong>Catalyst:</strong> {catalyst}</div>',
            unsafe_allow_html=True,
        )

    if fgag is not None and pd.notna(fgag):
        trading_summary = _generate_trading_summary(row)
        st.markdown(
            f'<div style="background:#f8f9fa; border-left:4px solid #3B4B8A; padding:10px 16px; '
            f'margin:8px 0; font-size:0.92em;">'
            f'<strong>Summary (AI driven):</strong> <em>{trading_summary}</em></div>',
            unsafe_allow_html=True,
        )
