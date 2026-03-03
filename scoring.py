"""
Athena Scoring Engine — 4-Pillar Board Governance Scorer + FGAG Signal.

Pure Python. Zero Streamlit dependency. Importable and testable independently.
This is the intellectual core of Athena.

Pillars:
    1. Numeric Dominance (0.20) — female headcount thresholds
    2. Positional Power (0.35) — female directors in power roles
    3. Structural Depth (0.25) — retention, tenure, organic vs. compliance
    4. Financial Impact (0.20) — revenue/ROE vs. sector median

Composite = weighted sum of P1-P4 (0-100).
Governance Score = P1-P3 renormalized (excludes financial pillar).
FGAG = governance_norm - valuation_percentile (mispricing signal).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_COMPANIES = 200
MAX_YEARS = 10

PILLAR_WEIGHTS_DEFAULT = {
    "numeric_dominance": 0.20,
    "positional_power": 0.35,
    "structural_depth": 0.25,
    "financial_impact": 0.20,
}

GOVERNANCE_WEIGHTS = {
    "numeric_dominance": 0.25,
    "positional_power": 0.4375,
    "structural_depth": 0.3125,
}

POWER_ROLE_POINTS: dict[str, int] = {
    "Board Chair": 40,
    "Lead Independent Director": 20,
    "Audit Committee Chair": 15,
    "Compensation Committee Chair": 15,
    "Governance/Nominating Committee Chair": 10,
}

FGAG_BANDS: list[tuple[float, str, str]] = [
    (0.4, "Undervalued Quality", "High conviction buy signal"),
    (0.1, "Efficient Quality", "Core hold"),
    (-0.1, "Fair Value", "Neutral"),
    (-0.4, "Overvalued vs. Governance", "Caution"),
    (float("-inf"), "Governance Trap", "Risk warning"),
]


@dataclass(frozen=True)
class PillarScores:
    """Immutable container for the four pillar scores."""

    numeric_dominance: float
    positional_power: float
    structural_depth: float
    financial_impact: float


@dataclass(frozen=True)
class CompanyResult:
    """Immutable result of scoring a single company."""

    ticker: str
    composite_score: float
    governance_score: float
    pillar_scores: PillarScores
    classification: str
    rag_status: str
    rag_label: str
    fgag: Optional[float]
    fgag_label: str
    fgag_action: str
    tsr_3yr: Optional[float]
    catalyst: Optional[str]
    retention_rate: Optional[float]
    retention_label: str


# ---------------------------------------------------------------------------
# Pillar Calculators (pure functions)
# ---------------------------------------------------------------------------

def calculate_numeric_dominance(female_pct: float) -> float:
    """Pillar 1: stepped scoring based on female board percentage.

    Thresholds aligned to academic critical-mass research (Konrad 2008).
    """
    assert pd.notna(female_pct), "female_pct must not be NaN"
    assert 0 <= female_pct <= 100, f"female_pct {female_pct} out of [0, 100]"

    if female_pct >= 60:
        return 100.0
    if female_pct >= 50:
        return 90.0
    if female_pct >= 40:
        return 75.0
    if female_pct >= 30:
        return 50.0
    score = (female_pct / 30) * 40
    assert 0 <= score <= 100, f"P1 score {score} out of range"
    return round(score, 1)


def calculate_positional_power(roles: dict[str, str]) -> float:
    """Pillar 2: power-role weighting (Chair, committees).

    Args:
        roles: mapping of role name -> gender string ("Female" or "Male").
    """
    assert isinstance(roles, dict), "roles must be a dict"

    score = 0.0
    for role, points in POWER_ROLE_POINTS.items():
        if roles.get(role) == "Female":
            score += points

    score = min(score, 100.0)
    assert 0 <= score <= 100, f"P2 score {score} out of range"
    return score


def calculate_structural_depth(
    retention_rate: float,
    avg_tenure: float,
    in_mandate_jurisdiction: bool,
) -> float:
    """Pillar 3: organic growth vs. compliance-driven optics.

    Retention (0-50 pts) + Tenure (0-40 pts) + Organic bonus (0-10 pts).
    """
    assert pd.notna(retention_rate), "retention_rate must not be NaN"
    assert pd.notna(avg_tenure), "avg_tenure must not be NaN"

    retention_score = retention_rate * 0.5
    tenure_score = min((avg_tenure / 5) * 40, 40.0)
    organic_bonus = 0.0 if in_mandate_jurisdiction else 10.0

    score = retention_score + tenure_score + organic_bonus
    score = max(0.0, min(score, 100.0))
    assert 0 <= score <= 100, f"P3 score {score} out of range"
    return round(score, 1)


def calculate_financial_impact(
    rev_growth_vs_sector: float,
    roe_vs_sector: float,
) -> float:
    """Pillar 4: alpha-correlation quality filter.

    Baseline 50 pts. +25 if rev growth beats sector. +25 if ROE beats sector.
    -20 penalty if rev growth significantly lags (>10% below sector).
    """
    if not pd.notna(rev_growth_vs_sector) or not pd.notna(roe_vs_sector):
        return 50.0  # neutral when data missing

    score = 50.0
    if rev_growth_vs_sector > 0:
        score += 25.0
    if roe_vs_sector > 0:
        score += 25.0
    if rev_growth_vs_sector < -0.10:
        score -= 20.0

    score = max(0.0, min(score, 100.0))
    assert 0 <= score <= 100, f"P4 score {score} out of range"
    return score


# ---------------------------------------------------------------------------
# Composite & Governance Scores
# ---------------------------------------------------------------------------

def calculate_composite(pillars: PillarScores, weights: dict[str, float] | None = None) -> float:
    """Weighted sum of all 4 pillars. Returns 0-100."""
    w = weights or PILLAR_WEIGHTS_DEFAULT
    score = (
        pillars.numeric_dominance * w["numeric_dominance"]
        + pillars.positional_power * w["positional_power"]
        + pillars.structural_depth * w["structural_depth"]
        + pillars.financial_impact * w["financial_impact"]
    )
    score = max(0.0, min(score, 100.0))
    assert 0 <= score <= 100, f"Composite {score} out of range"
    return round(score, 1)


def calculate_governance_score(pillars: PillarScores) -> float:
    """Pillars 1-3 renormalized (excludes financial pillar).

    Formula: (P1 x 0.25) + (P2 x 0.4375) + (P3 x 0.3125)
    """
    score = (
        pillars.numeric_dominance * GOVERNANCE_WEIGHTS["numeric_dominance"]
        + pillars.positional_power * GOVERNANCE_WEIGHTS["positional_power"]
        + pillars.structural_depth * GOVERNANCE_WEIGHTS["structural_depth"]
    )
    score = max(0.0, min(score, 100.0))
    assert 0 <= score <= 100, f"Governance score {score} out of range"
    return round(score, 1)


# ---------------------------------------------------------------------------
# Classification & RAG Status
# ---------------------------------------------------------------------------

def get_classification(
    composite_score: float,
    pillars: PillarScores,
    female_pct: float,
) -> str:
    """AI classification category based on score profile."""
    if female_pct < 1e-10:
        return "No Female Representation"
    if composite_score >= 80 and pillars.positional_power > 70:
        return "Genuine Structural Depth"
    if composite_score >= 60 and pillars.positional_power >= 40:
        return "Emerging Governance Leader"
    if pillars.numeric_dominance > 50 and pillars.structural_depth < 40:
        return "Compliance-Driven / Recent Shift"
    if pillars.numeric_dominance > 30 and pillars.positional_power < 20:
        return "Cosmetic / Token Risk"
    if composite_score >= 40:
        return "Developing Governance"
    return "Early Stage"


def get_rag_status(female_count: int) -> tuple[str, str]:
    """RAG classification: (colour, label).

    Red = 0, Amber = 1-2, Light Green = 3+ (<=50%), Dark Green = >50%.
    Note: Dark Green requires female_pct check done by caller.
    """
    assert isinstance(female_count, (int, np.integer)), f"Expected int, got {type(female_count)}"

    if female_count == 0:
        return ("Red", "Nil")
    if female_count <= 2:
        return ("Amber", "Minimal")
    return ("Light Green", "Critical Mass")


def get_rag_status_full(female_count: int, female_pct: float) -> tuple[str, str]:
    """RAG with majority detection. Returns (colour, label)."""
    if female_count == 0:
        return ("Red", "Nil")
    if female_count <= 2:
        return ("Amber", "Minimal")
    if female_pct > 50:
        return ("Dark Green", "Majority")
    return ("Light Green", "Critical Mass")


# ---------------------------------------------------------------------------
# FGAG — Female Governance Alpha Gap
# ---------------------------------------------------------------------------

def calculate_fgag(
    governance_norm: float,
    tsr_percentile: float,
    valuation_percentile: float,
) -> float:
    """Female Governance Alpha Gap: 3-input composite signal.

    Combines three dimensions to find companies where strong female governance
    coincides with growth AND attractive valuation:

    1. Governance quality (high = strong female governance)
    2. Growth (high TSR percentile = outperforming peers)
    3. Value (low valuation percentile = cheaper within sector)

    Formula: (governance_norm + tsr_percentile + (1 - valuation_percentile)) / 3 * 2 - 1

    Returns -1.0 to +1.0:
        +1.0 = top governance + top growth + cheapest valuation (ideal)
        -1.0 = weak governance + worst growth + most expensive (avoid)

    Args:
        governance_norm: 0.0-1.0 (governance_score / 100).
        tsr_percentile: 0.0-1.0 (rank of 3yr TSR within universe).
        valuation_percentile: 0.0-1.0 (0 = cheapest in sector, 1 = most expensive).
    """
    assert 0 <= governance_norm <= 1.0, f"Gov norm {governance_norm} out of range"
    assert 0 <= tsr_percentile <= 1.0, f"TSR pctile {tsr_percentile} out of range"
    assert 0 <= valuation_percentile <= 1.0, f"Val pctile {valuation_percentile} out of range"

    value_score = 1.0 - valuation_percentile
    composite = (governance_norm + tsr_percentile + value_score) / 3.0
    gap = composite * 2.0 - 1.0

    assert -1.0 <= gap <= 1.0, f"FGAG {gap} out of expected range"
    return round(gap, 2)


def get_fgag_label(fgag: float) -> tuple[str, str]:
    """Trading signal label and action for a given FGAG score."""
    for threshold, label, action in FGAG_BANDS:
        if fgag > threshold:
            return (label, action)
    return ("Governance Trap", "Risk warning")


# ---------------------------------------------------------------------------
# 3-Year TSR
# ---------------------------------------------------------------------------

def calculate_tsr_3yr(price_start: float, price_end: float) -> Optional[float]:
    """3-Year Total Shareholder Return (price-only).

    Formula: (price_end - price_start) / price_start * 100
    """
    if not pd.notna(price_start) or not pd.notna(price_end):
        return None
    if price_start < 1e-10:
        return None

    tsr = ((price_end - price_start) / price_start) * 100
    return round(tsr, 1)


# ---------------------------------------------------------------------------
# Retention Rate
# ---------------------------------------------------------------------------

def calculate_retention_rate(
    female_count_3yr_ago: int,
    female_retained: int,
) -> tuple[Optional[float], str]:
    """3-year female board member retention. Returns (rate, label)."""
    if female_count_3yr_ago == 0:
        return (None, "N/A — No Prior Baseline")

    assert female_retained >= 0, "female_retained cannot be negative"
    assert female_retained <= female_count_3yr_ago, (
        f"Retained ({female_retained}) > baseline ({female_count_3yr_ago})"
    )

    rate = (female_retained / female_count_3yr_ago) * 100
    assert 0 <= rate <= 100, f"Retention rate {rate} out of range"

    if rate >= 80:
        label = "Strong Retention"
    elif rate >= 50:
        label = "Moderate Turnover"
    else:
        label = "High Turnover"

    return (round(rate, 1), label)


# ---------------------------------------------------------------------------
# Catalyst Detection
# ---------------------------------------------------------------------------

def detect_catalyst(
    current_classification: str,
    prior_classification: str,
) -> Optional[str]:
    """Detect governance upgrade between periods.

    Returns a catalyst string if classification improved, else None.
    """
    rank = {
        "No Female Representation": 0,
        "Cosmetic / Token Risk": 1,
        "Compliance-Driven / Recent Shift": 2,
        "Insufficient Data / Neutral": 2,
        "Genuine Structural Depth": 3,
    }
    current_rank = rank.get(current_classification, -1)
    prior_rank = rank.get(prior_classification, -1)

    if current_rank > prior_rank and prior_rank >= 0:
        return f"Governance Upgrade: {prior_classification} -> {current_classification}"
    return None


# ---------------------------------------------------------------------------
# Main Scoring Engine
# ---------------------------------------------------------------------------

class BoardScoringEngine:
    """Orchestrates scoring for one or many companies.

    Stateless aside from pillar weights (configurable via sidebar).
    """

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = weights or PILLAR_WEIGHTS_DEFAULT.copy()
        total = sum(self.weights.values())
        assert abs(total - 1.0) < 1e-10, f"Weights must sum to 1.0, got {total}"

    def score_company(self, row: dict) -> CompanyResult:
        """Score a single company from a flat dict of fields.

        Expected keys: ticker, female_pct, female_count, board_size,
        roles_dict, retention_rate, avg_female_tenure,
        in_mandate_jurisdiction, rev_growth_vs_sector, roe_vs_sector,
        valuation_percentile, price_start, price_end,
        female_count_3yr_ago, female_retained,
        prior_classification (optional).
        """
        ticker = row["ticker"]
        female_pct = float(row["female_pct"])
        female_count = int(row["female_count"])

        # Pillar scores
        p1 = calculate_numeric_dominance(female_pct)
        p2 = calculate_positional_power(row["roles_dict"])
        p3 = calculate_structural_depth(
            float(row["retention_rate"]),
            float(row["avg_female_tenure"]),
            str(row["in_mandate_jurisdiction"]).strip().lower() in ("yes", "true", "1"),
        )
        p4 = calculate_financial_impact(
            row.get("rev_growth_vs_sector", np.nan),
            row.get("roe_vs_sector", np.nan),
        )

        pillars = PillarScores(
            numeric_dominance=p1,
            positional_power=p2,
            structural_depth=p3,
            financial_impact=p4,
        )

        composite = calculate_composite(pillars, self.weights)
        governance = calculate_governance_score(pillars)
        classification = get_classification(composite, pillars, female_pct)
        rag_colour, rag_label = get_rag_status_full(female_count, female_pct)

        # FGAG — computed at dataset level (requires universe TSR percentiles)
        # Placeholder; overridden by build_scored_dataset() in data_loader.py
        fgag, fgag_label, fgag_action = None, "N/A", "Pending"

        # TSR
        tsr = calculate_tsr_3yr(
            row.get("price_start", np.nan),
            row.get("price_end", np.nan),
        )

        # Retention
        retention, retention_label = calculate_retention_rate(
            int(row.get("female_count_3yr_ago", 0)),
            int(row.get("female_retained", 0)),
        )

        # Catalyst
        prior_class = row.get("prior_classification", "")
        catalyst = detect_catalyst(classification, prior_class) if prior_class else None

        return CompanyResult(
            ticker=ticker,
            composite_score=composite,
            governance_score=governance,
            pillar_scores=pillars,
            classification=classification,
            rag_status=rag_colour,
            rag_label=rag_label,
            fgag=fgag,
            fgag_label=fgag_label,
            fgag_action=fgag_action,
            tsr_3yr=tsr,
            catalyst=catalyst,
            retention_rate=retention,
            retention_label=retention_label,
        )

    def score_dataframe(self, df: pd.DataFrame) -> list[CompanyResult]:
        """Score all companies in a DataFrame. Returns list of CompanyResult."""
        assert not df.empty, "Cannot score empty DataFrame"
        assert len(df) <= MAX_COMPANIES, f"DataFrame has {len(df)} rows, max {MAX_COMPANIES}"

        results = []
        for idx, row in df.iterrows():
            result = self.score_company(row.to_dict())
            results.append(result)

        assert len(results) == len(df), "Result count mismatch"
        return results

    def results_to_dataframe(self, results: list[CompanyResult]) -> pd.DataFrame:
        """Convert list of CompanyResult to a flat DataFrame for display."""
        assert len(results) > 0, "Cannot convert empty results"

        records = []
        for r in results:
            records.append({
                "ticker": r.ticker,
                "composite_score": r.composite_score,
                "governance_score": r.governance_score,
                "p1_numeric_dominance": r.pillar_scores.numeric_dominance,
                "p2_positional_power": r.pillar_scores.positional_power,
                "p3_structural_depth": r.pillar_scores.structural_depth,
                "p4_financial_impact": r.pillar_scores.financial_impact,
                "classification": r.classification,
                "rag_status": r.rag_status,
                "rag_label": r.rag_label,
                "fgag": r.fgag,
                "fgag_label": r.fgag_label,
                "fgag_action": r.fgag_action,
                "tsr_3yr": r.tsr_3yr,
                "catalyst": r.catalyst,
                "retention_rate": r.retention_rate,
                "retention_label": r.retention_label,
            })

        return pd.DataFrame(records)
