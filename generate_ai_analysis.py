"""One-time script to generate ai_analysis.json from the data files."""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from scoring import (
    BoardScoringEngine,
    get_rag_status_full,
    calculate_fgag,
    get_fgag_label,
)

DATA_DIR = Path(__file__).parent / "data"


def main() -> None:
    board = pd.read_csv(DATA_DIR / "board_data.csv")
    fin = pd.read_csv(DATA_DIR / "financials.csv")
    val = pd.read_csv(DATA_DIR / "valuations.csv")
    prices = pd.read_csv(DATA_DIR / "share_prices.csv")

    # Merge
    m = board.merge(fin, on="ticker", how="left", suffixes=("", "_fin"))
    m = m.merge(
        val[["ticker", "forward_pe", "valuation_percentile"]],
        on="ticker", how="left",
    )

    # TSR
    if "2023-Q1" in prices.columns and "2025-Q4" in prices.columns:
        pr = prices[["ticker", "2023-Q1", "2025-Q4"]].copy()
        pr.columns = ["ticker", "ps", "pe"]
        m = m.merge(pr, on="ticker", how="left")
        m["tsr"] = np.where(m["ps"] > 0, ((m["pe"] - m["ps"]) / m["ps"]) * 100, np.nan)

    # Sector medians
    m["rev_g"] = np.where(
        m["rev_2024_B"] > 0,
        (m["rev_2025_B"] - m["rev_2024_B"]) / m["rev_2024_B"],
        np.nan,
    )
    sec_med = m.groupby("sector").agg(
        rev_g_med=("rev_g", "median"),
        roe_med=("roe_2025", "median"),
    ).reset_index()
    m = m.merge(sec_med, on="sector", how="left", suffixes=("", "_sm"))

    # EPS CAGR
    m["eps_cagr"] = np.where(
        (m["eps_2021"] > 0) & (m["eps_2025"] > 0),
        ((m["eps_2025"] / m["eps_2021"]) ** (1 / 4) - 1) * 100,
        np.nan,
    )

    role_map = {
        "board_chair_gender": "Board Chair",
        "lead_independent_gender": "Lead Independent Director",
        "audit_chair_gender": "Audit Committee Chair",
        "comp_chair_gender": "Compensation Committee Chair",
        "gov_nom_chair_gender": "Governance/Nominating Committee Chair",
    }

    engine = BoardScoringEngine()
    analysis: dict = {}

    for _, r in m.iterrows():
        tk = r["ticker"]
        fp = float(r["female_pct"])
        fc = int(r["female_count"])
        bs = int(r["board_size"])

        roles = {}
        for col, rn in role_map.items():
            v = r.get(col, "")
            if pd.notna(v):
                roles[rn] = str(v)

        fc23 = int(r.get("female_count_2023", 0))
        fr = int(r.get("female_retained", 0))
        ret_rate = (fr / fc23 * 100) if fc23 > 0 else 0

        rev_g = r.get("rev_g", np.nan)
        rev_g_med = r.get("rev_g_med", 0)
        roe_25 = r.get("roe_2025", np.nan)
        roe_med = r.get("roe_med", 0)

        data = {
            "ticker": tk,
            "female_pct": fp,
            "female_count": fc,
            "board_size": bs,
            "roles_dict": roles,
            "retention_rate": ret_rate,
            "avg_female_tenure": float(r.get("avg_female_tenure", 0)),
            "in_mandate_jurisdiction": bool(r.get("in_mandate_jurisdiction", False)),
            "rev_growth_vs_sector": (rev_g - rev_g_med) if pd.notna(rev_g) else np.nan,
            "roe_vs_sector": (roe_25 - roe_med) if pd.notna(roe_25) else np.nan,
            "valuation_percentile": r.get("valuation_percentile", np.nan),
            "price_start": r.get("ps", np.nan),
            "price_end": r.get("pe", np.nan),
            "female_count_3yr_ago": fc23,
            "female_retained": fr,
            "prior_classification": "",
        }

        res = engine.score_company(data)
        vp = r.get("valuation_percentile", np.nan)
        fgag = calculate_fgag(res.governance_score, float(vp)) if pd.notna(vp) else None
        fgag_l, _ = get_fgag_label(fgag) if fgag is not None else ("N/A", "")

        tsr = r.get("tsr", np.nan)
        eps_cagr = r.get("eps_cagr", np.nan)
        co = r.get("company", tk)

        fem_roles = sum(1 for rn, g in roles.items() if g == "Female" and rn != "Lead Independent Director")
        fem_chair = roles.get("Board Chair") == "Female"

        # --- Headline ---
        if res.classification == "Genuine Structural Depth":
            headline = (
                f"{co} demonstrates genuine structural depth in female governance, "
                f"with a composite score of {res.composite_score:.0f} and positional "
                f"power score of {res.pillar_scores.positional_power:.0f} -- "
                f"this is real influence, not headcount padding."
            )
        elif res.classification == "No Female Representation":
            headline = (
                f"{co} has zero female board representation -- a significant governance "
                f"gap in an era where board diversity correlates with operational discipline."
            )
        elif res.classification == "Cosmetic / Token Risk":
            headline = (
                f"{co} shows signs of cosmetic diversity -- female representation exists "
                f"({fp:.0f}%) but without meaningful positional power "
                f"(score: {res.pillar_scores.positional_power:.0f})."
            )
        elif res.classification == "Compliance-Driven / Recent Shift":
            headline = (
                f"{co} appears to be in a compliance-driven shift -- numeric representation "
                f"has grown ({fp:.0f}%) but structural depth lags, suggesting recent "
                f"rather than organic appointments."
            )
        else:
            headline = (
                f"{co} shows moderate female governance presence "
                f"({fp:.0f}% female, composite {res.composite_score:.0f}) -- "
                f"further positional power development could unlock governance quality premium."
            )

        # --- Board ---
        if fem_chair:
            board_txt = (
                f"Female Board Chair is the single most powerful governance signal. "
                f"With {fc} of {bs} directors female ({fp:.0f}%), {co} combines numeric "
                f"presence with real decision-making authority."
            )
        elif fem_roles >= 3:
            board_txt = (
                f"Women hold {fem_roles} key committee roles -- this is positional power, "
                f"not headcount padding. {fc} of {bs} directors are female ({fp:.0f}%)."
            )
        elif fem_roles >= 1:
            board_txt = (
                f"{fc} of {bs} directors are female ({fp:.0f}%), with women holding "
                f"{fem_roles} committee chair role(s). Scope to deepen positional influence remains."
            )
        elif fc > 0:
            board_txt = (
                f"{fc} of {bs} directors are female ({fp:.0f}%), but none hold key "
                f"committee chair positions -- governance influence is limited to board-level voting."
            )
        else:
            board_txt = f"All {bs} board directors are male. Zero female representation in governance roles."

        # --- Financial ---
        if pd.notna(eps_cagr) and pd.notna(tsr):
            rev_21 = r.get("rev_2021_B", 0)
            rev_25 = r.get("rev_2025_B", 0)
            rev_growth_total = ((rev_25 - rev_21) / rev_21 * 100) if rev_21 > 0 else 0
            if eps_cagr > 10 and tsr > 30:
                fin_txt = (
                    f"EPS has compounded at {eps_cagr:.0f}% CAGR over 4 years with revenue "
                    f"growing {rev_growth_total:.0f}% -- strong financial trajectory that "
                    f"coincides with the board's governance profile."
                )
            elif eps_cagr > 0:
                fin_txt = (
                    f"EPS CAGR of {eps_cagr:.0f}% and {tsr:.0f}% total shareholder return "
                    f"over 3 years -- moderate financial performance alongside current governance structure."
                )
            elif eps_cagr < 0:
                fin_txt = (
                    f"EPS has declined at {eps_cagr:.0f}% CAGR despite governance composition "
                    f"-- financial underperformance warrants investigation of operational factors "
                    f"beyond board structure."
                )
            else:
                fin_txt = (
                    f"3-year TSR of {tsr:.0f}% -- financial trajectory is flat, limiting "
                    f"the governance-to-performance correlation thesis."
                )
        else:
            fin_txt = (
                "Insufficient financial history to assess correlation between governance "
                "composition and financial outcomes."
            )

        # --- Depth ---
        mandate = bool(r.get("in_mandate_jurisdiction", False))
        tenure = r.get("avg_female_tenure", 0)
        if ret_rate >= 80 and not mandate:
            depth_txt = (
                f"{ret_rate:.0f}% female director retention over 3 years with average tenure "
                f"of {tenure:.1f} years -- organic commitment, not mandate-driven compliance."
            )
        elif ret_rate >= 80:
            depth_txt = (
                f"Strong {ret_rate:.0f}% retention rate, though the company operates in a "
                f"mandate jurisdiction -- distinguish organic commitment from regulatory compliance."
            )
        elif ret_rate >= 50:
            depth_txt = (
                f"Moderate {ret_rate:.0f}% retention rate suggests some directorial churn "
                f"-- investigate whether departures were natural rotation or governance instability."
            )
        elif fc23 > 0:
            depth_txt = (
                f"Low {ret_rate:.0f}% retention rate raises questions about appointment "
                f"sustainability -- high turnover often signals cosmetic rather than structural commitment."
            )
        else:
            depth_txt = (
                "No female baseline 3 years ago -- current representation is entirely new, "
                "making long-term commitment impossible to assess."
            )

        # --- Trading ---
        if fgag is not None:
            if fgag > 0.4:
                trade_txt = (
                    f"FGAG of {fgag:+.2f} -- governance quality in the "
                    f"{res.governance_score:.0f}th percentile at a {vp:.0%} valuation. "
                    f"Classic governance arbitrage: market has not priced in the board's "
                    f"structural strength."
                )
            elif fgag > 0.1:
                trade_txt = (
                    f"FGAG of {fgag:+.2f} -- governance strength is roughly reflected in "
                    f"valuation. Core hold thesis if governance trajectory continues upward."
                )
            elif fgag > -0.1:
                trade_txt = (
                    f"FGAG of {fgag:+.2f} -- fair value. Governance quality and market "
                    f"pricing are roughly aligned. No significant arbitrage opportunity."
                )
            elif fgag > -0.4:
                trade_txt = (
                    f"FGAG of {fgag:+.2f} -- caution. Trading at a premium "
                    f"({vp:.0%} valuation percentile) without proportionate governance "
                    f"backing ({res.governance_score:.0f}/100)."
                )
            else:
                trade_txt = (
                    f"FGAG of {fgag:+.2f} -- governance trap warning. "
                    f"High valuation ({vp:.0%} percentile) with weak governance score "
                    f"({res.governance_score:.0f}/100). Risk of multiple compression "
                    f"if governance quality becomes a factor."
                )
        else:
            trade_txt = "Insufficient valuation data to calculate FGAG trading signal."

        analysis[tk] = {
            "classification": res.classification,
            "confidence": "High" if r.get("data_source") == "real" else "Medium",
            "so_what_headline": headline,
            "so_what_board": board_txt,
            "so_what_financial": fin_txt,
            "so_what_depth": depth_txt,
            "so_what_trading": trade_txt,
            "catalyst": None,
        }

    # Dataset summary
    genuine = sum(1 for a in analysis.values() if isinstance(a, dict) and a.get("classification") == "Genuine Structural Depth")
    total = len([a for a in analysis.values() if isinstance(a, dict)])
    analysis["_dataset_summary"] = (
        f"{genuine} of {total} companies achieve 'Genuine Structural Depth' classification "
        f"-- strong female governance with real positional power. "
        f"Screen by FGAG to find where this governance quality coincides with market mispricing."
    )

    out_path = DATA_DIR / "ai_analysis.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)

    print(f"Generated AI analysis for {total} companies")
    print(f"Genuine Structural Depth: {genuine}")

    sample = analysis.get("AAPL", {})
    if sample:
        print(f"\nSample (AAPL):")
        print(f"  Classification: {sample.get('classification')}")
        print(f"  Headline: {sample.get('so_what_headline', '')[:100]}...")


if __name__ == "__main__":
    main()
