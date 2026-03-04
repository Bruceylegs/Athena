"""
Athena Charts — Plotly chart builders with corporate styling.

No Streamlit dependency. Returns plotly.graph_objects.Figure objects.
Colour palette: Oxford Blue (#002147) primary, Indigo (#3B4B8A) accent.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Corporate Palette
# ---------------------------------------------------------------------------
OXFORD_BLUE = "#002147"
MARINE_BLUE = "#052a4e"
INDIGO = "#3B4B8A"
LIGHT_GREY = "#F0F2F6"
WHITE = "#FFFFFF"
BG_COLOUR = "#FAFBFC"

RAG_COLOURS = {
    "Red": "#DC3545",
    "Amber": "#FFC107",
    "Light Green": "#6BBF59",
    "Dark Green": "#1B7A3D",
}

FGAG_COLOURS = {
    "Undervalued Quality": "#1B7A3D",
    "Efficient Quality": "#3B4B8A",
    "Fair Value": "#6C757D",
    "Overvalued vs. Governance": "#FFC107",
    "Governance Trap": "#DC3545",
    "N/A": "#ADB5BD",
}

PLOTLY_CONFIG = {"displayModeBar": False}

CHART_LAYOUT_DEFAULTS = dict(
    font=dict(family="Segoe UI, sans-serif", color=OXFORD_BLUE),
    paper_bgcolor=WHITE,
    plot_bgcolor=WHITE,
    margin=dict(l=60, r=30, t=50, b=60),
)


# ---------------------------------------------------------------------------
# Quadrant Chart (Screener landing page)
# ---------------------------------------------------------------------------

def build_quadrant_chart(
    df: pd.DataFrame,
    benchmark_y: float,
    mean_governance: float,
    y_col: str = "tsr_3yr",
    y_label: str = "3-Year Total Shareholder Return (%)",
    hline_label: str = "NASDAQ-100 Mean",
    y_format: str = ".1f",
    y_suffix: str = "%",
) -> go.Figure:
    """Governance Score vs Y-metric scatter with coloured quadrant backgrounds.

    Args:
        df: scored DataFrame with columns: ticker, governance_score, y_col, rag_status
        benchmark_y: horizontal dividing line value
        mean_governance: vertical dividing line (mean governance score)
        y_col: column name for Y-axis values
        y_label: display label for Y-axis
        hline_label: label for the horizontal dividing line
        y_format: format string for hover values
        y_suffix: suffix for hover values (e.g., "%" or "/100")
    """
    assert not df.empty, "Cannot build quadrant from empty DataFrame"
    assert "governance_score" in df.columns, "Missing governance_score column"
    assert y_col in df.columns, f"Missing {y_col} column"

    plot_df = df.dropna(subset=["governance_score", y_col]).copy()

    # Calculate axis ranges with padding
    x_min = max(plot_df["governance_score"].min() - 5, 0)
    x_max = min(plot_df["governance_score"].max() + 5, 100)
    y_min = plot_df[y_col].min() - 20
    y_max = plot_df[y_col].max() + 30

    fig = go.Figure()

    # --- Quadrant background rectangles (Bug 9) ---
    # Bottom-left: Neither (light red)
    fig.add_shape(type="rect", x0=x_min, x1=mean_governance, y0=y_min, y1=benchmark_y,
                  fillcolor="rgba(220, 53, 69, 0.06)", line_width=0, layer="below")
    # Top-left: Returns Without Governance (light amber)
    fig.add_shape(type="rect", x0=x_min, x1=mean_governance, y0=benchmark_y, y1=y_max,
                  fillcolor="rgba(255, 193, 7, 0.06)", line_width=0, layer="below")
    # Bottom-right: Governance Without Returns (light blue)
    fig.add_shape(type="rect", x0=mean_governance, x1=x_max, y0=y_min, y1=benchmark_y,
                  fillcolor="rgba(59, 75, 138, 0.06)", line_width=0, layer="below")
    # Top-right: Sweet Spot (light green)
    fig.add_shape(type="rect", x0=mean_governance, x1=x_max, y0=benchmark_y, y1=y_max,
                  fillcolor="rgba(27, 122, 61, 0.08)", line_width=0, layer="below")

    # Quadrant labels (centred in each quadrant, opaque)
    quadrant_labels = [
        dict(x=(x_min + mean_governance) / 2, y=(y_min + benchmark_y) / 2,
             text="Neither", font=dict(size=13, color="rgba(220, 53, 69, 0.25)")),
        dict(x=(x_min + mean_governance) / 2, y=(benchmark_y + y_max) / 2,
             text="Returns Without<br>Governance", font=dict(size=13, color="rgba(255, 170, 0, 0.3)")),
        dict(x=(mean_governance + x_max) / 2, y=(y_min + benchmark_y) / 2,
             text="Governance Without<br>Returns", font=dict(size=13, color="rgba(59, 75, 138, 0.25)")),
        dict(x=(mean_governance + x_max) / 2, y=(benchmark_y + y_max) / 2,
             text="Sweet Spot", font=dict(size=15, color="rgba(27, 122, 61, 0.3)")),
    ]
    for lbl in quadrant_labels:
        fig.add_annotation(
            x=lbl["x"], y=lbl["y"], text=lbl["text"],
            font=lbl["font"], showarrow=False, xanchor="center", yanchor="middle",
        )

    # Add dots grouped by RAG status for legend
    # Bug 9: descriptive legend labels
    legend_labels = {
        "Red": "Nil Female Board Members",
        "Amber": "Minimal (up to 2) Female Board Members",
        "Light Green": "Critical Mass (3+) Female Board Members",
        "Dark Green": "Majority (>50%) Female Board Members",
    }

    for rag_status, colour in RAG_COLOURS.items():
        mask = plot_df["rag_status"] == rag_status
        subset = plot_df[mask]
        if subset.empty:
            continue

        hover_text = [
            f"<b>{row['ticker']}</b><br>"
            f"Governance: {row['governance_score']:.1f}<br>"
            f"{y_label}: {format(row[y_col], y_format)}{y_suffix}<br>"
            f"RAG: {row['rag_label']}"
            for _, row in subset.iterrows()
        ]

        fig.add_trace(go.Scatter(
            x=subset["governance_score"],
            y=subset[y_col],
            mode="markers+text",
            marker=dict(size=12, color=colour, line=dict(width=1, color=OXFORD_BLUE)),
            text=subset["ticker"],
            textposition="top center",
            textfont=dict(size=9, color=OXFORD_BLUE),
            hovertext=hover_text,
            hoverinfo="text",
            name=legend_labels.get(rag_status, rag_status),
            legendgroup=rag_status,
        ))

    # Vertical line: mean governance
    fig.add_vline(
        x=mean_governance, line_dash="dash",
        line_color=INDIGO, opacity=0.5,
        annotation_text=f"Mean Gov. Score ({mean_governance:.0f})",
        annotation_position="top",
        annotation_font=dict(size=10, color=INDIGO),
    )

    # Horizontal line: benchmark (Bug 13 — use "left" to avoid cutoff)
    fig.add_hline(
        y=benchmark_y, line_dash="dash",
        line_color=INDIGO, opacity=0.5,
        annotation_text=f"{hline_label} ({format(benchmark_y, y_format)}{y_suffix})",
        annotation_position="top left",
        annotation_font=dict(size=10, color=INDIGO),
    )

    # Bug 4: main title with date; Bug 11: axis labels; Bug 12: axis title hover
    from datetime import date as dt_date
    today_str = dt_date.today().strftime("%d %b %Y")

    fig.update_layout(
        font=dict(family="Segoe UI, sans-serif", color=OXFORD_BLUE),
        paper_bgcolor=WHITE,
        plot_bgcolor=WHITE,
        title=dict(
            text=f"Company Universe (Updated: {today_str})",
            font=dict(size=17, color=OXFORD_BLUE),
        ),
        xaxis=dict(
            title="Female Governance Composite Score",
            gridcolor=LIGHT_GREY,
            zeroline=False,
            range=[x_min, x_max],
        ),
        yaxis=dict(
            title=y_label,
            gridcolor=LIGHT_GREY,
            zeroline=False,
            range=[y_min, y_max],
        ),
        legend=dict(
            title=dict(text="Key: Number / Proportion of Female Board Members", font=dict(size=11)),
            orientation="h", yanchor="bottom", y=-0.28,
            xanchor="center", x=0.5,
            font=dict(size=11),
        ),
        height=560,
        margin=dict(l=70, r=70, t=60, b=70),
    )

    return fig


# ---------------------------------------------------------------------------
# Board Composition Donut (Company Deep Dive)
# ---------------------------------------------------------------------------

def build_board_donut(female_count: int, male_count: int) -> go.Figure:
    """Donut chart showing female vs. male board split."""
    assert female_count >= 0, "female_count cannot be negative"
    assert male_count >= 0, "male_count cannot be negative"

    fig = go.Figure(data=[go.Pie(
        labels=["Female", "Male"],
        values=[female_count, male_count],
        hole=0.55,
        marker=dict(colors=[MARINE_BLUE, LIGHT_GREY], line=dict(color=WHITE, width=2)),
        textinfo="label+percent",
        textfont=dict(size=13),
        insidetextfont=dict(size=13),
        hovertemplate="<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>",
        sort=False,
    )])
    # Per-slice text colours: white on dark (Female/marine blue), black on light (Male/LIGHT_GREY)
    fig.data[0].textfont.color = [WHITE, OXFORD_BLUE]

    fig.update_layout(
        font=dict(family="Segoe UI, sans-serif", color=OXFORD_BLUE),
        paper_bgcolor=WHITE,
        plot_bgcolor=WHITE,
        showlegend=False,
        height=280,
        margin=dict(l=20, r=20, t=20, b=20),
        annotations=[dict(
            text=f"<b>{female_count + male_count}</b><br>Directors",
            x=0.5, y=0.5, font_size=14, font_color=OXFORD_BLUE,
            showarrow=False,
        )],
    )

    return fig


# ---------------------------------------------------------------------------
# Positional Power Donut (Company Deep Dive)
# ---------------------------------------------------------------------------

def build_power_donut(female_power: int, male_power: int) -> go.Figure:
    """Donut chart showing female vs. male split of key governance roles."""
    assert female_power >= 0, "female_power cannot be negative"
    assert male_power >= 0, "male_power cannot be negative"

    total = female_power + male_power
    fig = go.Figure(data=[go.Pie(
        labels=["Female", "Male"],
        values=[female_power, male_power],
        hole=0.55,
        marker=dict(colors=[MARINE_BLUE, LIGHT_GREY], line=dict(color=WHITE, width=2)),
        textinfo="label+percent",
        textfont=dict(size=13),
        insidetextfont=dict(size=13),
        hovertemplate="<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>",
        sort=False,
    )])
    fig.data[0].textfont.color = [WHITE, OXFORD_BLUE]

    fig.update_layout(
        font=dict(family="Segoe UI, sans-serif", color=OXFORD_BLUE),
        paper_bgcolor=WHITE,
        plot_bgcolor=WHITE,
        showlegend=False,
        height=280,
        margin=dict(l=20, r=20, t=20, b=20),
        annotations=[dict(
            text=f"<b>{total}</b><br>Power Roles",
            x=0.5, y=0.5, font_size=13, font_color=OXFORD_BLUE,
            showarrow=False,
        )],
    )

    return fig


# ---------------------------------------------------------------------------
# Share Price Line Chart (Company Deep Dive)
# ---------------------------------------------------------------------------

def build_share_price_chart(prices_df: pd.DataFrame, ticker: str) -> go.Figure:
    """5-year quarterly share price line chart."""
    assert not prices_df.empty, "Cannot build chart from empty price data"

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=prices_df["Quarter"],
        y=prices_df["Close ($)"],
        mode="lines+markers",
        line=dict(color=INDIGO, width=2),
        marker=dict(size=5, color=INDIGO),
        hovertemplate="<b>%{x}</b><br>$%{y:.2f}<extra></extra>",
        name=ticker,
    ))

    fig.update_layout(
        **CHART_LAYOUT_DEFAULTS,
        title=dict(text=f"{ticker} — 5 Year Share Price Chart (2021-2025)", font=dict(size=14)),
        xaxis=dict(
            title="Quarter",
            gridcolor=LIGHT_GREY,
            tickangle=-45,
            dtick=4,
        ),
        yaxis=dict(
            title="Share Price ($)",
            gridcolor=LIGHT_GREY,
            tickprefix="$",
        ),
        showlegend=False,
        height=350,
    )

    return fig


# ---------------------------------------------------------------------------
# Female % Sparkline (3-Year Trend)
# ---------------------------------------------------------------------------

def build_female_pct_sparkline(
    pct_2023: float,
    pct_2024: float,
    pct_2025: float,
    ticker: str,
) -> go.Figure:
    """Compact 3-year trend of female board representation."""
    years = ["2023", "2024", "2025"]
    values = [pct_2023, pct_2024, pct_2025]

    line_colour = MARINE_BLUE

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=years,
        y=values,
        mode="lines+markers+text",
        line=dict(color=line_colour, width=3),
        marker=dict(size=8, color=line_colour),
        text=[f"{v:.0f}%" for v in values],
        textposition="top center",
        textfont=dict(size=11, color=OXFORD_BLUE),
        hovertemplate="<b>%{x}</b><br>%{y:.1f}%<extra></extra>",
    ))

    fig.update_layout(
        font=dict(family="Segoe UI, sans-serif", color=OXFORD_BLUE),
        paper_bgcolor=WHITE,
        plot_bgcolor=WHITE,
        showlegend=False,
        height=180,
        margin=dict(l=30, r=30, t=10, b=30),
        xaxis=dict(showgrid=False),
        yaxis=dict(
            title="Female %",
            showgrid=False,
            range=[max(0, min(values) - 10), min(100, max(values) + 10)],
            ticksuffix="%",
        ),
    )

    return fig


# ---------------------------------------------------------------------------
# FGAG Gauge (Trading Signal section)
# ---------------------------------------------------------------------------

def build_fgag_gauge(fgag_score: float, label: str) -> go.Figure:
    """Semi-circular gauge showing FGAG score position with segment labels."""
    colour = FGAG_COLOURS.get(label, INDIGO)

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=fgag_score,
        number=dict(
            font=dict(size=36, color=OXFORD_BLUE),
            valueformat="+.2f",
        ),
        title=dict(text=label, font=dict(size=14, color=colour)),
        gauge=dict(
            axis=dict(range=[-1, 1], tickwidth=1, tickcolor=OXFORD_BLUE,
                      tickvals=[-1, -0.4, -0.1, 0.1, 0.4, 1],
                      ticktext=["-1", "-0.4", "-0.1", "0.1", "0.4", "1"]),
            bar=dict(color=colour),
            bgcolor=LIGHT_GREY,
            borderwidth=0,
            steps=[
                dict(range=[-1, -0.4], color="#FADBD8"),
                dict(range=[-0.4, -0.1], color="#FCE4B8"),
                dict(range=[-0.1, 0.1], color="#E8E8E8"),
                dict(range=[0.1, 0.4], color="#D4E6F1"),
                dict(range=[0.4, 1], color="#D5F5E3"),
            ],
        ),
    ))

    fig.update_layout(
        font=dict(family="Segoe UI, sans-serif", color=OXFORD_BLUE),
        paper_bgcolor=WHITE,
        plot_bgcolor=WHITE,
        height=250,
        margin=dict(l=30, r=30, t=50, b=10),
    )

    return fig


# ---------------------------------------------------------------------------
# EPS / Revenue Bar Chart (Company Deep Dive — Financial Performance)
# ---------------------------------------------------------------------------

def build_eps_revenue_bars(fin_table: pd.DataFrame, ticker: str) -> go.Figure:
    """Grouped bar chart showing EPS and Revenue side-by-side over 5 years."""
    assert not fin_table.empty, "Cannot build chart from empty financial data"

    years = fin_table["Year"].tolist()
    eps_vals = fin_table["EPS ($)"].tolist() if "EPS ($)" in fin_table.columns else []
    rev_vals = fin_table["Revenue ($B)"].tolist() if "Revenue ($B)" in fin_table.columns else []

    fig = go.Figure()

    if eps_vals:
        fig.add_trace(go.Bar(
            x=years,
            y=eps_vals,
            name="EPS ($)",
            marker_color=MARINE_BLUE,
            yaxis="y",
            hovertemplate="<b>%{x}</b><br>EPS: $%{y:.2f}<extra></extra>",
        ))

    if rev_vals:
        fig.add_trace(go.Bar(
            x=years,
            y=rev_vals,
            name="Revenue ($B)",
            marker_color=INDIGO,
            yaxis="y2",
            hovertemplate="<b>%{x}</b><br>Revenue: $%{y:.1f}B<extra></extra>",
            opacity=0.7,
        ))

    fig.update_layout(
        **CHART_LAYOUT_DEFAULTS,
        title=dict(text=f"{ticker} — EPS & Revenue (5-Year)", font=dict(size=14)),
        barmode="group",
        xaxis=dict(title="Year", gridcolor=LIGHT_GREY),
        yaxis=dict(
            title="EPS ($)",
            title_font=dict(color=MARINE_BLUE),
            tickfont=dict(color=MARINE_BLUE),
            tickprefix="$",
            gridcolor=LIGHT_GREY,
        ),
        yaxis2=dict(
            title="Revenue ($B)",
            title_font=dict(color=INDIGO),
            tickfont=dict(color=INDIGO),
            tickprefix="$",
            ticksuffix="B",
            anchor="x",
            overlaying="y",
            side="right",
        ),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
        height=350,
    )

    return fig


# ---------------------------------------------------------------------------
# Sector Peer Governance Comparison (Company Deep Dive)
# ---------------------------------------------------------------------------

def build_sector_peer_governance(
    scored_df: pd.DataFrame,
    ticker: str,
    sector: str,
) -> go.Figure:
    """Horizontal bar chart comparing governance scores within the same sector."""
    peers = scored_df[scored_df["sector"] == sector].copy()
    if peers.empty:
        peers = scored_df.head(5).copy()

    peers = peers.sort_values("governance_score", ascending=True)

    colours = [
        MARINE_BLUE if t == ticker else LIGHT_GREY
        for t in peers["ticker"]
    ]
    border_colours = [
        OXFORD_BLUE if t == ticker else "#CCC"
        for t in peers["ticker"]
    ]

    fig = go.Figure(go.Bar(
        y=peers["ticker"],
        x=peers["governance_score"],
        orientation="h",
        marker=dict(color=colours, line=dict(color=border_colours, width=1.5)),
        hovertemplate="<b>%{y}</b><br>Governance Score: %{x:.1f}<extra></extra>",
    ))

    fig.update_layout(
        **CHART_LAYOUT_DEFAULTS,
        title=dict(text=f"Sector Peer Comparison — {sector}", font=dict(size=14)),
        xaxis=dict(title="Female Governance Composite Score", gridcolor=LIGHT_GREY, range=[0, 100]),
        yaxis=dict(title=""),
        showlegend=False,
        height=max(250, len(peers) * 35 + 80),
    )

    return fig
