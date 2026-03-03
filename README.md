# Athena — Female Governance Alpha Generator

A governance-adjusted value screener that identifies companies where meaningful female board representation coincides with financial outperformance or market mispricing.

**Live demo**: [athena-gov.streamlit.app](https://athena-gov.streamlit.app/)

```bash
pip install -r requirements.txt && streamlit run app.py
```

---

## How I Interpreted the Use Case

The brief asks what "meaningful" female board representation looks like. My answer: it's two things at once — **positional power** and **financial coincidence**.

Percentage alone is insufficient. A board that is 40% female but where every woman is a recently appointed non-executive director is not "meaningfully" represented. Critical-mass research (Konrad et al., 2008; Torchia et al., 2011) shows that below three female directors, minority voices self-censor and are absorbed by the dominant group. At three or more, group dynamics shift and governance outcomes measurably improve. But even beyond three, *which* seats matter: a female Board Chair or committee chair wields structural influence that additional non-executive appointments do not. The scoring model therefore weights Positional Power (35%) above Numeric Dominance (20%).

Good governance alone isn't investable — it has to be underpriced. The dashboard's centrepiece metric, the **Female Governance Alpha Gap (FGAG)**, combines a company's governance quality score with its relative total shareholder return and forward valuation. A company with exemplary governance that the market has already priced in generates no alpha; one where strong governance coexists with a cheap forward P/E does. The FGAG turns a qualitative ESG narrative into a quantitative signal that identifies where the market may be mispricing governance quality.

This is framed as **correlation, not causation** — governance is one analytical lens among many.

---

## Definitions, Assumptions & Trade-Offs

**Composite Score — 4 Pillars**

| Pillar | Weight | Measures |
|---|:---:|---|
| Numeric Dominance | 20% | Female headcount and percentage (critical mass at 3+) |
| Positional Power | 35% | Board Chair, committee chairs, CEO, CFO, Lead Independent |
| Structural Depth | 25% | 3-year retention rate, average tenure, mandate-jurisdiction compliance |
| Financial Impact | 20% | Revenue growth, ROE vs. sector, relative TSR |

**RAG Status** (headcount-based):
- **Red** — zero female directors
- **Amber** — 1–2 female directors (below critical mass)
- **Light Green** — 3+ female directors, ≤50% of board
- **Dark Green** — 3+ female directors, >50% of board

**FGAG** — three normalised inputs (governance quality from Pillars 1–3, 3-year TSR percentile rank, inverted forward-P/E percentile) averaged and scaled to **−1 to +1**. Five signal bands:

| FGAG | Signal |
|---|---|
| > +0.4 | Undervalued Quality — market hasn't priced in governance strength |
| > +0.1 | Efficient Quality — core hold |
| > −0.1 | Fair Value — neutral |
| > −0.4 | Overvalued vs. Governance — caution |
| ≤ −0.4 | Governance Trap — risk warning |

**Key trade-offs**
- **Power > percentage** — could underweight genuinely majority-female boards where women hold non-executive roles.
- **3-year retention** penalises companies that made recent, genuine improvements.
- **Forward P/E as single valuation proxy** — production would blend EV/EBITDA, PEG, and FCF yield.
- **50 companies (15 real + 35 synthetic)** — sufficient for a working demo, not for factor analysis or statistical significance.
- **Pre-computed AI narratives** — zero runtime API dependencies, but analysis cannot adapt to live filings.

---

## What I Would Build Next

- **Live SEC EDGAR parser** — extract board composition directly from DEF 14A proxy statements.
- **Full NASDAQ-100 universe** with daily automated refresh.
- **Factor regression** — isolate the governance alpha signal from Fama-French size, value, and momentum factors.
- **Real-time valuations** via market-data API (forward P/E, EV/EBITDA).
- **Backtest engine** — simulate FGAG-sorted portfolios against the index over rolling windows.
- **Export** — downloadable PDF tear-sheets and CSV screening results.

---

## Data Disclosure

15 companies use real board and financial data hand-curated from 2025 SEC proxy statements, public annual reports, and Yahoo Finance. The remaining ~35 are synthetic and clearly labelled (`data_source` column). All data is bundled as static CSV/JSON — no external API calls at runtime.
