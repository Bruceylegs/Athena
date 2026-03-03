"""
Athena Data Loader — CSV/JSON loading, caching, sector median pre-calculation.

All data loading happens here. Pages import from this module, never read CSVs directly.
Uses @st.cache_data for Streamlit caching (ttl=None — static data).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

from scoring import (
    BoardScoringEngine,
    CompanyResult,
    MAX_COMPANIES,
)

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
ASSETS_DIR = Path(__file__).parent / "assets"

# Expected CSV schemas (column subsets for validation)
BOARD_REQUIRED_COLS = [
    "ticker", "company", "sector", "female_count", "female_pct",
    "board_size", "avg_female_tenure", "in_mandate_jurisdiction",
    "female_count_2023", "female_count_2024", "female_count_2025",
    "female_retained", "data_source",
]
FINANCIALS_REQUIRED_COLS = ["ticker", "eps_2025", "rev_2025_B", "roe_2025", "sector"]
VALUATIONS_REQUIRED_COLS = ["ticker", "forward_pe", "sector_median_pe", "valuation_percentile"]
SHARE_PRICES_REQUIRED_COLS = ["ticker", "2023-Q1", "2025-Q4"]


def _validate_columns(df: pd.DataFrame, required: list[str], name: str) -> None:
    """Assert that all required columns exist in a DataFrame."""
    missing = set(required) - set(df.columns)
    assert len(missing) == 0, f"{name} missing columns: {missing}"


@st.cache_data(ttl=None)
def load_board_data() -> pd.DataFrame:
    """Load board composition data."""
    path = DATA_DIR / "board_data.csv"
    df = pd.read_csv(path)
    assert not df.empty, f"No data from {path}"
    _validate_columns(df, BOARD_REQUIRED_COLS, "board_data")
    return df


@st.cache_data(ttl=None)
def load_financials() -> pd.DataFrame:
    """Load 5-year financial performance data."""
    path = DATA_DIR / "financials.csv"
    df = pd.read_csv(path)
    assert not df.empty, f"No data from {path}"
    _validate_columns(df, FINANCIALS_REQUIRED_COLS, "financials")
    return df


@st.cache_data(ttl=None)
def load_share_prices() -> pd.DataFrame:
    """Load quarterly share price data (wide format)."""
    path = DATA_DIR / "share_prices.csv"
    df = pd.read_csv(path)
    assert not df.empty, f"No data from {path}"
    _validate_columns(df, SHARE_PRICES_REQUIRED_COLS, "share_prices")
    return df


@st.cache_data(ttl=None)
def load_valuations() -> pd.DataFrame:
    """Load forward P/E and valuation percentile data."""
    path = DATA_DIR / "valuations.csv"
    df = pd.read_csv(path)
    assert not df.empty, f"No data from {path}"
    _validate_columns(df, VALUATIONS_REQUIRED_COLS, "valuations")
    return df


@st.cache_data(ttl=None)
def load_esg_context() -> pd.DataFrame:
    """Load ESG and legislative context data."""
    path = DATA_DIR / "esg_context.csv"
    df = pd.read_csv(path)
    assert not df.empty, f"No data from {path}"
    return df


@st.cache_data(ttl=None)
def load_benchmark() -> float:
    """Load NASDAQ-100 3-year TSR benchmark. Returns percentage."""
    path = DATA_DIR / "benchmark.csv"
    df = pd.read_csv(path)
    assert not df.empty, f"No data from {path}"
    tsr = float(df.iloc[0]["tsr_3yr_pct"])
    assert pd.notna(tsr), "Benchmark TSR is NaN"
    return tsr


@st.cache_data(ttl=None)
def load_ai_analysis() -> dict[str, Any]:
    """Load pre-computed AI analysis per company."""
    path = DATA_DIR / "ai_analysis.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict), "ai_analysis.json must be a dict"
    return data


@st.cache_data(ttl=None)
def calculate_sector_medians() -> pd.DataFrame:
    """Pre-calculate sector median financial metrics for Pillar 4."""
    fin = load_financials()

    eps_cols = [c for c in fin.columns if c.startswith("eps_")]
    rev_cols = [c for c in fin.columns if c.startswith("rev_") and c.endswith("_B")]

    # Revenue growth: latest year vs prior
    fin = fin.copy()
    fin["rev_growth"] = np.where(
        fin["rev_2024_B"] > 1e-10,
        (fin["rev_2025_B"] - fin["rev_2024_B"]) / fin["rev_2024_B"],
        np.nan,
    )

    medians = fin.groupby("sector").agg(
        rev_growth_median=("rev_growth", "median"),
        roe_median=("roe_2025", "median"),
    ).reset_index()

    return medians


@st.cache_data(ttl=None)
def build_scored_dataset(
    weights: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Master function: merge all data, score every company, return flat DataFrame.

    This is the single entry point for all pages. Returns a DataFrame with
    all board data + pillar scores + composite + FGAG + TSR + classification.
    """
    board = load_board_data()
    fin = load_financials()
    val = load_valuations()
    prices = load_share_prices()
    medians = calculate_sector_medians()

    assert len(board) <= MAX_COMPANIES, f"Too many companies: {len(board)}"

    # Merge financials
    merged = board.merge(fin[["ticker", "roe_2025", "rev_2024_B", "rev_2025_B", "sector"]],
                         on="ticker", how="left", suffixes=("", "_fin"))

    # Calculate rev growth vs sector
    merged["rev_growth"] = np.where(
        merged["rev_2024_B"] > 1e-10,
        (merged["rev_2025_B"] - merged["rev_2024_B"]) / merged["rev_2024_B"],
        np.nan,
    )
    merged = merged.merge(medians, on="sector", how="left", suffixes=("", "_med"))
    merged["rev_growth_vs_sector"] = merged["rev_growth"] - merged["rev_growth_median"]
    merged["roe_vs_sector"] = merged["roe_2025"] - merged["roe_median"]

    # Merge valuations
    merged = merged.merge(val[["ticker", "valuation_percentile", "forward_pe"]],
                          on="ticker", how="left")

    # Get share prices for TSR
    price_start_col = "2023-Q1"
    price_end_col = "2025-Q4"
    if price_start_col in prices.columns and price_end_col in prices.columns:
        price_subset = prices[["ticker", price_start_col, price_end_col]].copy()
        price_subset.columns = ["ticker", "price_start", "price_end"]
        merged = merged.merge(price_subset, on="ticker", how="left")
    else:
        merged["price_start"] = np.nan
        merged["price_end"] = np.nan

    # Build roles dict per company
    role_cols = [
        "board_chair_gender", "lead_independent_gender",
        "audit_chair_gender", "comp_chair_gender", "gov_nom_chair_gender",
    ]
    role_map = {
        "board_chair_gender": "Board Chair",
        "lead_independent_gender": "Lead Independent Director",
        "audit_chair_gender": "Audit Committee Chair",
        "comp_chair_gender": "Compensation Committee Chair",
        "gov_nom_chair_gender": "Governance/Nominating Committee Chair",
    }

    def _build_roles_dict(row: pd.Series) -> dict[str, str]:
        roles = {}
        for col, role_name in role_map.items():
            val_cell = row.get(col, "")
            if pd.notna(val_cell):
                roles[role_name] = str(val_cell)
        return roles

    merged["roles_dict"] = merged.apply(_build_roles_dict, axis=1)

    # Score each company
    engine = BoardScoringEngine(weights=weights)
    results: list[CompanyResult] = []

    for _, row in merged.iterrows():
        company_data = {
            "ticker": row["ticker"],
            "female_pct": float(row["female_pct"]),
            "female_count": int(row["female_count"]),
            "board_size": int(row["board_size"]),
            "roles_dict": row["roles_dict"],
            "retention_rate": float(row.get("female_retained", 0))
                / max(float(row.get("female_count_2023", 1)), 1) * 100
                if row.get("female_count_2023", 0) > 0 else 0.0,
            "avg_female_tenure": float(row.get("avg_female_tenure", 0)),
            "in_mandate_jurisdiction": bool(row.get("in_mandate_jurisdiction", False)),
            "rev_growth_vs_sector": row.get("rev_growth_vs_sector", np.nan),
            "roe_vs_sector": row.get("roe_vs_sector", np.nan),
            "valuation_percentile": row.get("valuation_percentile", np.nan),
            "price_start": row.get("price_start", np.nan),
            "price_end": row.get("price_end", np.nan),
            "female_count_3yr_ago": int(row.get("female_count_2023", 0)),
            "female_retained": int(row.get("female_retained", 0)),
            "prior_classification": "",
        }
        result = engine.score_company(company_data)
        results.append(result)

    # Convert to DataFrame
    scored = engine.results_to_dataframe(results)

    # Merge back company metadata
    meta_cols = ["ticker", "company", "sector", "jurisdiction", "board_size",
                 "female_count", "female_pct", "female_ceo", "forward_pe",
                 "data_source"]
    available_meta = [c for c in meta_cols if c in merged.columns]
    scored = scored.merge(merged[available_meta], on="ticker", how="left")

    # Merge valuation percentile for FGAG calculation
    if "valuation_percentile" not in scored.columns:
        val_pctile = merged[["ticker", "valuation_percentile"]].drop_duplicates("ticker")
        scored = scored.merge(val_pctile, on="ticker", how="left")

    # --- Compute 3-input FGAG at dataset level ---
    # Ensure fgag column is numeric (placeholder strings from scoring engine)
    scored["fgag"] = pd.to_numeric(scored["fgag"], errors="coerce")

    from scoring import calculate_fgag, get_fgag_label

    has_all = (
        scored["governance_score"].notna()
        & scored["tsr_3yr"].notna()
        & scored["valuation_percentile"].notna()
    )
    if has_all.any():
        subset_idx = scored.loc[has_all].index
        tsr_pctile = scored.loc[subset_idx, "tsr_3yr"].rank(pct=True)

        for idx in subset_idx:
            gov_norm = scored.at[idx, "governance_score"] / 100.0
            tsr_p = float(tsr_pctile.at[idx])
            val_p = float(scored.at[idx, "valuation_percentile"])
            fgag = calculate_fgag(gov_norm, tsr_p, val_p)
            label, action = get_fgag_label(fgag)
            scored.at[idx, "fgag"] = fgag
            scored.at[idx, "fgag_label"] = label
            scored.at[idx, "fgag_action"] = action

    return scored


def get_company_financials(ticker: str) -> pd.DataFrame | None:
    """Get 5-year financial table for a single company (for deep dive page)."""
    fin = load_financials()
    row = fin[fin.ticker == ticker]
    if row.empty:
        return None

    row = row.iloc[0]
    years = [2021, 2022, 2023, 2024, 2025]
    data = []
    for yr in years:
        eps = row.get(f"eps_{yr}", np.nan)
        rev = row.get(f"rev_{yr}_B", np.nan)

        prev_eps = row.get(f"eps_{yr-1}", np.nan) if yr > 2021 else np.nan
        prev_rev = row.get(f"rev_{yr-1}_B", np.nan) if yr > 2021 else np.nan

        eps_growth = ((eps - prev_eps) / abs(prev_eps) * 100
                      if pd.notna(eps) and pd.notna(prev_eps) and abs(prev_eps) > 1e-10
                      else np.nan)
        rev_growth = ((rev - prev_rev) / prev_rev * 100
                      if pd.notna(rev) and pd.notna(prev_rev) and prev_rev > 1e-10
                      else np.nan)

        data.append({
            "Year": str(yr),
            "EPS ($)": round(eps, 2) if pd.notna(eps) else None,
            "EPS Growth (%)": round(eps_growth, 1) if pd.notna(eps_growth) else None,
            "Revenue ($B)": round(rev, 1) if pd.notna(rev) else None,
            "Revenue Growth (%)": round(rev_growth, 1) if pd.notna(rev_growth) else None,
        })

    return pd.DataFrame(data)


def get_company_share_prices(ticker: str) -> pd.DataFrame | None:
    """Get quarterly share prices for a single company (for chart)."""
    prices = load_share_prices()
    row = prices[prices.ticker == ticker]
    if row.empty:
        return None

    row = row.iloc[0]
    date_cols = [c for c in prices.columns if c not in ("ticker", "data_source")]
    data = []
    for col in date_cols:
        price = row.get(col, np.nan)
        if pd.notna(price):
            data.append({"Quarter": col, "Close ($)": float(price)})

    return pd.DataFrame(data)
