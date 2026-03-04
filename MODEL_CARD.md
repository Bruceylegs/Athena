# Model Card — Athena

**Athena — Female Governance. Untapped Alpha.**

A tool that scores companies on the quality of their female board representation, checks whether those companies are also performing well financially, and flags cases where the market may not yet be pricing that combination in.

---

## 1. Model Overview

Athena is an interactive web application built as an interview challenge for a Forward-Deployed AI Engineer role. It introduces the **FGAG (Female Governance Alpha Gap)** — a single number between -1 and +1 that combines three things: how good a company's female board governance is, how well the company's share price has performed, and whether the company looks cheap or expensive relative to its peers.

The core idea: companies with genuine (not token) female governance, strong financial results, and reasonable share prices may represent an overlooked opportunity. Athena scores, classifies, and visualises a 50-company universe to let users explore this idea interactively.

---

## 2. System Architecture

```
Athena/
├── app.py                      ← Starting point: sets up the page layout, colours, and tab navigation
├── data_loader.py              ← Central hub: loads all data files, combines them, runs scoring, caches results
├── scoring.py                  ← Scoring engine: all formulas and classification rules (standalone, no web dependency)
├── charts.py                   ← Chart builders: creates all interactive charts (standalone, no web dependency)
├── generate_ai_analysis.py     ← Offline script: run once to produce the pre-written narrative text file
├── requirements.txt            ← Lists the 4 software packages the app needs to run
├── .streamlit/
│   └── config.toml             ← Colour and font settings
├── assets/
│   ├── athena_logo.png
│   └── favicon.png
├── pages/
│   ├── screener.py             ← Overview of all companies: scatter chart, quick filters, rankings table
│   └── company.py              ← Detailed view of one company across 3 sections
└── data/
    ├── board_data.csv           (board composition, roles, tenure, jurisdiction)
    ├── financials.csv           (5-year EPS, revenue, ROE, margin)
    ├── share_prices.csv         (20 quarterly close prices, wide format)
    ├── valuations.csv           (forward P/E, sector median, percentile)
    ├── esg_context.csv          (ESG scores, diversity disclosures — loaded but not displayed)
    ├── benchmark.csv            (single row: NASDAQ-100 3-year TSR)
    └── ai_analysis.json         (pre-computed narratives per company)
```

### The role of Streamlit — and how the Python scripts become a website

Athena's Python scripts do not produce a website on their own. On their own, they are just text files containing Python code. **Streamlit** is the software that reads those scripts and turns them into an interactive web page that anyone can use in a browser. Think of it like this:

- The Python scripts are the **content and logic** (what to show, how to score, what charts to draw).
- Streamlit is the **engine** that takes that content and renders it as a live, clickable web page.

#### Where the scripts are stored and how they reach the user

The scripts are **not uploaded manually** to Streamlit's platform. Instead, the deployment works through a chain of three locations. The files exist as **copies in all three places simultaneously**:

1. **The developer's computer** — all the `.py` files, `.csv` data files, and configuration files live in the `Athena/` folder on the developer's machine. This is where editing happens.
2. **GitHub** — the folder is connected to a GitHub repository (`Bruceylegs/Athena`). When the developer pushes changes (i.e. uploads the latest versions of the files), GitHub stores a copy of every file publicly.
3. **Streamlit Community Cloud** — this is a free hosting service run by Streamlit. It is connected to the GitHub repository. When the code on GitHub changes, Streamlit Community Cloud **copies the entire repository onto its own servers** — every `.py` script, every `.csv` data file, the `.streamlit/config.toml`, everything. It then installs the four packages listed in `requirements.txt` (Pandas, NumPy, Plotly, and Streamlit itself) **on that same server**, and runs `app.py` **on that same server**.

So yes — the Python scripts, the data files, and the installed packages all end up stored and running on Streamlit's servers. The web page that users see in their browser is being generated and served from Streamlit's infrastructure, not from GitHub or the developer's machine. GitHub is just the intermediary that gets the files there — the developer pushes to GitHub, and Streamlit's servers pull from GitHub automatically.

#### What Streamlit provides inside the code

Throughout the scripts, you will see calls that start with `st.` — these are Streamlit commands. They are how the Python code tells Streamlit what to display:

- **Layout and widgets.** `st.columns()` creates side-by-side columns. `st.tabs()` creates the Screener and Company Deep Dive tabs. `st.selectbox()` creates dropdown menus. `st.dataframe()` displays a table. These are called in `app.py`, `screener.py`, and `company.py`.
- **Caching.** `data_loader.py` uses `@st.cache_data` — a Streamlit feature that tells it: "load and process these CSV files once, then remember the result. Don't redo the work every time the user clicks something."
- **Session state.** The cross-page navigation (described in point 5 below) relies on `st.session_state` — a shared notepad that all parts of the application can read and write to, lasting for the duration of the user's browser session.
- **Configuration.** The `.streamlit/config.toml` file tells Streamlit what colour scheme and font to use. Streamlit reads this file automatically on startup.

#### Why two files deliberately avoid Streamlit

`scoring.py` and `charts.py` are written with **no Streamlit commands at all**. They use only plain Python, Pandas, and Plotly. This is a deliberate design choice: because they do not depend on Streamlit, they can be tested and reused independently — for example, a developer could run the scoring engine in a terminal or a test suite without needing to start the web application.

### How components connect

1. **`app.py`** is where the application starts. Streamlit reads this file first. It sets up the page title, applies the colour scheme (Oxford Blue and Indigo), renders the logo banner and navigation menu, and presents two tabs: **Screener** and **Company Deep Dive**. A small piece of JavaScript keeps the banner pinned to the top of the page as the user scrolls.

2. **`data_loader.py`** is the central hub. It loads all 6 CSV files, joins them together using the ticker symbol as the common key, calculates how each company compares to its sector (e.g. is its revenue growth above or below the sector average?), sends the combined data to the scoring engine, and then works out the FGAG values across the full set of companies (because FGAG needs to know how each company ranks relative to everyone else). Results are cached so the data is only loaded once per user session.

3. **`scoring.py`** contains all the scoring formulas, classification rules, and the FGAG calculation. It has no dependency on the web framework — it is plain Python — which means it can be tested on its own without running the application.

4. **`charts.py`** builds all the interactive charts: the quadrant scatter plot, two donut charts (board composition and power roles), a share price line chart, a female percentage sparkline, the FGAG gauge, an earnings and revenue bar chart, and a sector peer comparison. Like the scoring engine, it has no dependency on the web framework.

5. **Cross-page navigation** is handled by a built-in Streamlit feature called "session state" — there is no separate script for it. It works like a shared notepad that all parts of the application can read and write to. Here is the step-by-step flow:

   - **Step 1 (Screener writes):** In `pages/screener.py`, when the user clicks a row in the rankings table, the code reads the ticker from that row (e.g. "AAPL") and saves it to the shared notepad under the key `"selected_ticker"`.
   - **Step 2 (Company Deep Dive reads):** In `pages/company.py`, when the page loads, it checks whether `"selected_ticker"` exists on the shared notepad. If it does, the page automatically sets the company dropdown to that ticker, so the user sees that company's full analysis without having to search for it manually.
   - **Step 3 (Home button clears):** In `app.py`, when the user clicks the "Home" button, the code deletes `"selected_ticker"` from the shared notepad, resetting the navigation so no company is pre-selected.

   All three files participate, but there is no routing script or URL-based navigation. The shared notepad (`st.session_state`) persists for the duration of the user's browser session and is the only mechanism linking the two tabs together.

---

## 3. Data Description

The data layer consists of 6 CSV files and 1 JSON file in the `data/` folder. The universe contains **15 real companies** and **~35 synthetic companies**, clearly labelled via the `data_source` column (`"real"` or `"synthetic"`).

### How the data files feed into the architecture

All 7 data files sit in the `data/` folder and are loaded by `data_loader.py` — the central hub described in Section 2. Here is how each file flows through the system:

1. **`board_data.csv`** is the foundation. `data_loader.py` loads it first, then merges every other CSV onto it using the ticker symbol as the joining key. The board fields feed directly into Pillars 1, 2, and 3 of the scoring engine (`scoring.py`).

2. **`financials.csv`** is merged onto the board data by ticker. `data_loader.py` uses the revenue columns to calculate year-on-year revenue growth, compares it against the sector median, and passes the result into Pillar 4 (Financial Impact) in `scoring.py`. The 5-year financial history is also displayed as a table and bar chart on the Company Deep Dive page, built by `charts.py`.

3. **`share_prices.csv`** is merged by ticker. `data_loader.py` pulls the Q1 2023 and Q4 2025 prices to calculate 3-year total shareholder return — one of the three inputs to the FGAG formula. The full 20-quarter series is passed to `charts.py` to draw the share price line chart on the Company Deep Dive page.

4. **`valuations.csv`** is merged by ticker. The `valuation_percentile` column becomes the second input to the FGAG formula (how expensive or cheap a company is relative to its sector). The forward price-to-earnings ratio is displayed on the Company Deep Dive page.

5. **`esg_context.csv`** is loaded by `data_loader.py` but is **not currently used** in any scoring or display. It exists as a placeholder for future development.

6. **`benchmark.csv`** contains a single row — the NASDAQ-100 3-year return of 47.2%. `data_loader.py` loads this value and passes it to `pages/screener.py`, which draws it as the horizontal reference line on the quadrant chart. Companies above this line have beaten the market; companies below have not.

7. **`ai_analysis.json`** takes a different path. It is loaded directly by the Company Deep Dive page (`pages/company.py`), bypassing the scoring pipeline entirely. It provides the pre-written narrative text blocks that appear alongside the charts and scores. If a company's narrative is missing from this file, the page falls back to simpler rule-based sentences generated on the fly.

### board_data.csv
Who sits on each company's board, what roles they hold, and how long they have been there. Key columns:
- `ticker`, `company`, `sector`, `jurisdiction`
- `board_size`, `female_count`, `female_pct`
- `female_count_2023`, `female_count_2024`, `female_count_2025` — 3-year headcount history
- `female_retained` — number of female directors retained from 3 years ago
- `female_ceo` — whether the CEO is female
- `board_chair_gender`, `lead_independent_gender`, `audit_chair_gender`, `comp_chair_gender`, `gov_nom_chair_gender` — gender of each power role holder
- `board_chair_name`, `lead_independent_name`, `audit_chair_name`, `comp_chair_name`, `gov_nom_chair_name`, `ned_names` — the names of each role holder and non-executive directors (non-exec names are separated by `|` characters)
- `avg_female_tenure` — how many years, on average, the female directors have served on the board
- `in_mandate_jurisdiction` — whether the company is based somewhere that legally requires female board representation
- `data_source` — `"real"` or `"synthetic"`

### financials.csv
Five years of financial results for each company. Key columns:
- `ticker`, `sector`, `data_source`
- `eps_2021` through `eps_2025` — earnings per share (how much profit the company made per share of stock, each year)
- `rev_2021_B` through `rev_2025_B` — annual revenue in billions of US dollars
- `roe_2025` — return on equity for the latest year (a measure of how efficiently the company uses shareholders' money to generate profit)
- `net_margin_2025` — net profit margin for the latest year (what percentage of revenue is left as profit after all costs)

### share_prices.csv
Share prices at the end of each quarter, laid out with one column per quarter:
- `ticker`, `data_source`
- `2021-Q1` through `2025-Q4` — 20 quarterly closing prices in US dollars

The 3-year total shareholder return is calculated by comparing the Q1 2023 price to the Q4 2025 price.

### valuations.csv
How expensive or cheap each company's shares are relative to its sector:
- `ticker`, `sector`, `data_source`
- `forward_pe` — forward price-to-earnings ratio (share price divided by next year's expected earnings — a common way to measure whether a stock is cheap or expensive)
- `sector_median_pe` — the typical forward P/E for companies in the same sector
- `valuation_percentile` — where the company sits on a scale from 0.0 (cheapest in its sector) to 1.0 (most expensive)

### esg_context.csv
Environmental, social, and governance (ESG) data and diversity disclosure information. Columns include `esg_governance_score`, `workforce_diversity_disclosure`, `diversity_mandate_jurisdiction`, `mandate_name`, `cdp_score`. This file is loaded by the application but is **not currently used** in any scoring or shown on any page — it exists as a placeholder for potential future use.

### benchmark.csv
A single row containing the market reference point used to judge whether a company has beaten "the market":
- `benchmark`: "NASDAQ-100" (a well-known index of the 100 largest non-financial companies on the NASDAQ stock exchange)
- `tsr_3yr_pct`: **47.2%** — this means the NASDAQ-100 grew by 47.2% over the 3-year period from Q1 2023 to Q4 2025. Any company with a higher return has outperformed the market.

### ai_analysis.json
Pre-written plain-English summaries for each company, stored by ticker symbol. Each company entry contains:
- `classification` — which of the 7 governance categories the company falls into
- `confidence` — `"High"` for real companies, `"Medium"` for synthetic ones
- `so_what_headline` — a one-line summary of the company's governance story
- `so_what_board` — a paragraph about the company's board composition
- `so_what_financial` — a paragraph about the company's financial performance
- `so_what_depth` — a paragraph about how deep and durable the female representation is
- `so_what_trading` — a paragraph about the FGAG trading signal

There is also a `"_dataset_summary"` entry that provides overall statistics across all companies.

---

## 4. Scoring Methodology

All formulas are defined in `scoring.py`. The scoring system has four pillars (each measuring a different aspect of governance or performance), two overall scores that combine those pillars, and the FGAG signal.

### Pillar 1 — Numeric Dominance (P1)

Measures the proportion of female directors on the board. The score jumps at key thresholds rather than rising smoothly, based on research into "critical mass" theory (Konrad 2008) — the idea that women need a certain minimum share of the board before they can meaningfully influence decisions:

| Female % | Score |
|---|---|
| >= 60% | 100 |
| >= 50% | 90 |
| >= 40% | 75 |
| >= 30% | 50 |
| < 30% | Scales up gradually: `(female_pct / 30) * 40` |

Below 30%, the score rises gradually from 0 to 40. At 30% it jumps to 50, reflecting the research finding that women need roughly a third of the board before they can influence decisions as a group rather than as isolated individuals.

**Range:** 0 to 100.

### Pillar 2 — Positional Power (P2)

Measures whether women hold influential board roles, not just seats. Having four women on the board means less if none of them chair anything. Five key roles are scored by how much influence they carry:

| Role | Points |
|---|---|
| Board Chair | 40 |
| Lead Independent Director | 20 |
| Audit Committee Chair | 15 |
| Compensation Committee Chair | 15 |
| Governance/Nominating Committee Chair | 10 |

The score is the sum of points for roles held by women, capped at 100.

**Range:** 0 to 100.

### Pillar 3 — Structural Depth (P3)

Measures whether the female representation is built to last or is just for show. Three components:

- **Retention score** (up to 50 points): What proportion of the women who were on the board 3 years ago are still there today? Calculated as `retention_rate * 0.5`, where retention rate = `(female_retained / female_count_3yr_ago) * 100`.
- **Tenure score** (up to 40 points): How long have the female directors been serving, on average? Calculated as `min((avg_female_tenure / 5) * 40, 40)`. The score maxes out at 5 years — beyond that, additional tenure does not add more points.
- **Organic bonus** (0 or 10 points): 10 points if the company is **not** in a jurisdiction that legally requires female directors, 0 if it is. The reasoning: companies that appoint women to the board voluntarily, without a legal push, may be signalling stronger internal commitment.

**Formula:** `score = retention_score + tenure_score + organic_bonus`, with the result kept within [0, 100].

**Retention labels:**
- >= 80%: "Strong Retention"
- >= 50%: "Moderate Turnover"
- < 50%: "High Turnover"

### Pillar 4 — Financial Impact (P4)

Measures whether the company is doing better or worse than its sector financially. It starts at a neutral baseline and adjusts up or down:

- **Baseline:** 50 (neutral — average for the sector)
- **Revenue growing faster than the sector average?** +25 points
- **Return on equity above the sector average?** +25 points (return on equity measures how efficiently the company turns shareholders' money into profit)
- **Revenue growth more than 10% below the sector average?** -20 points (a penalty for falling far behind)
- If either input is missing, the score stays at the neutral 50.

Revenue growth is calculated in `data_loader.py` as the percentage change from 2024 to 2025 revenue, then compared against the middle value for the sector.

**Range:** 0 to 100 (in practice, 30 to 100).

### Composite Score

A weighted average of all four pillars. Each pillar contributes a different share of the total, reflecting how important it is to the overall thesis:

```
composite = (P1 * 0.20) + (P2 * 0.35) + (P3 * 0.25) + (P4 * 0.20)
```

In plain terms: Positional Power counts for the most (35%), because having women in positions of real authority matters more than headcount alone. Structural Depth is next (25%), followed by Numeric Dominance and Financial Impact (20% each). The result is kept within [0, 100] and rounded to 1 decimal place.

### Governance Score

Measures governance quality only — Pillars 1 to 3, excluding Financial Impact. Because one pillar has been removed, the remaining three weights are scaled up so they still add to 100%:

```
governance = (P1 * 0.25) + (P2 * 0.4375) + (P3 * 0.3125)
```

These weights come from taking the original P1/P2/P3 weights (0.20, 0.35, 0.25) and dividing each by their combined total (0.80). The result is kept within [0, 100] and rounded to 1 decimal place.

### FGAG — Female Governance Alpha Gap

The headline signal. It answers one question: "Does this company have good governance, good returns, AND a reasonable price?" It combines three inputs, each scaled to a 0-to-1 range:

1. **Governance quality** = `governance_score / 100` — how the governance pillars scored (0 = worst, 1 = best)
2. **Share price performance ranking** = where the company's 3-year return sits relative to all other companies in the universe (0 = lowest return, 1 = highest return)
3. **Value score** = `1 - valuation_percentile` — how cheap the company is relative to its sector (0 = most expensive, 1 = cheapest)

**Formula:**
```
average_of_three = (governance_quality + performance_ranking + value_score) / 3
fgag = average_of_three * 2 - 1
```

The first line averages the three inputs (giving a number between 0 and 1). The second line rescales it to a range of **-1.0 to +1.0**, where +1.0 means top governance, top returns, and cheapest valuation, while -1.0 means the opposite across all three.

FGAG must be calculated across the full set of companies (not one at a time) because the performance ranking depends on how every company compares to every other company.

### FGAG Signal Bands

| FGAG threshold | Label | Action |
|---|---|---|
| > 0.4 | Undervalued Quality | High conviction buy signal |
| > 0.1 | Efficient Quality | Core hold |
| > -0.1 | Fair Value | Neutral |
| > -0.4 | Overvalued vs. Governance | Caution |
| <= -0.4 | Governance Trap | Risk warning |

### Traffic-Light Classification (RAG)

A simple red/amber/green system based on how many women are on the board:

| Female count | Female % | Colour | Label |
|---|---|---|---|
| 0 | any | Red | Nil |
| 1–2 | any | Amber | Minimal |
| 3+ | <= 50% | Light Green | Critical Mass |
| 3+ | > 50% | Dark Green | Majority |

### AI Classification

Seven categories, evaluated in order (first match wins):

1. **No Female Representation** — female % is zero
2. **Genuine Structural Depth** — composite >= 80 AND positional power > 70
3. **Emerging Governance Leader** — composite >= 60 AND positional power >= 40
4. **Compliance-Driven / Recent Shift** — numeric dominance > 50 AND structural depth < 40
5. **Cosmetic / Token Risk** — numeric dominance > 30 AND positional power < 20
6. **Developing Governance** — composite >= 40
7. **Early Stage** — everything else

### 3-Year Total Shareholder Return

How much a shareholder's investment grew (or shrank) over 3 years, expressed as a percentage:

```
return = (ending_price - starting_price) / starting_price * 100
```

Calculated using the Q1 2023 and Q4 2025 share prices. If either price is missing, no return is calculated.

### Retention Rate

```
rate = (female_retained / female_count_3yr_ago) * 100
```

Returns "N/A — No Prior Baseline" if there were no female directors 3 years ago.

### Catalyst Detection

Checks whether a company's governance classification has improved over time (e.g. moving from "Cosmetic / Token Risk" to "Genuine Structural Depth"). If the current classification is ranked higher than the previous one, the company is flagged with a "Governance Upgrade" label — highlighting that something has changed for the better.

---

## 5. AI Narrative Generation

Despite the name "AI analysis", this is **not** a large language model or any form of machine learning. The `generate_ai_analysis.py` script is a **rule-based template system** — it uses if/then logic and pre-written sentence fragments to assemble narratives. It is run once, offline, to produce the `data/ai_analysis.json` file.

For each company, it generates:
- A one-line headline summary
- A paragraph about board composition
- A paragraph about financial performance
- A paragraph about how deep and durable the female representation is
- A paragraph about the FGAG trading signal
- A classification label and a confidence level

**Confidence:** `"High"` for real companies (based on actual data), `"Medium"` for synthetic companies (based on fabricated data).

**What happens when the app runs:** The Company Deep Dive page first looks for the company's entry in `ai_analysis.json`. If the entry exists, it displays those pre-written paragraphs. If the entry is missing (e.g. a new company was added to the data but the script was not re-run), the page falls back to simpler rule-based sentences generated on the spot — for example, "EPS grew by more than 10%" or "retention is strong at 85%".

---

## 6. Technology Stack

| Component | Version | What it does |
|---|---|---|
| Python | 3.x | The programming language the entire application is written in. It runs all the scoring logic, data processing, and page rendering. |
| Streamlit | >= 1.31.0 | A framework that turns Python scripts into interactive web applications. It handles the browser interface — buttons, tables, tabs, dropdowns — without needing separate front-end code. Athena runs entirely through Streamlit. |
| Pandas | >= 2.0.0 | A data manipulation library. It loads the CSV files into table-like structures, merges them together by ticker symbol, calculates new columns (like revenue growth), and filters/sorts results. It is the backbone of all data handling in Athena. |
| NumPy | >= 1.24.0 | A numerical computing library. Pandas uses it under the hood for fast arithmetic on large columns of numbers. Athena uses it directly in a few places for handling missing values and basic maths. |
| Plotly | >= 5.18.0 | A charting library that produces interactive, browser-based charts. Every visual in Athena — the quadrant scatter plot, donut charts, share price lines, the FGAG gauge, bar charts, and sparklines — is built with Plotly. Users can hover over data points to see details. |

**Hosting:** Streamlit Community Cloud — a free service that takes the application code and makes it available as a public website. There is no paid server or infrastructure to manage.

**No external services at runtime.** The application does not call any outside APIs, databases, or third-party services while it is running. All the data it needs is bundled as flat files (CSVs and one JSON file) inside the application itself.

**Theme configuration** (`.streamlit/config.toml`): Controls the visual appearance of the application — the accent colour (Indigo), background colour (off-white), text colour (Oxford Blue), and font (sans-serif). This file is read automatically by Streamlit when the application starts.

---

## 7. Limitations and Known Constraints

- **Data does not update automatically.** All data is a snapshot from a single point in time. There is no live feed or automatic refresh — if a company appoints a new director tomorrow, the app will not reflect it until someone manually updates the CSV files.
- **Pillar weights are illustrative.** The weights (20%/35%/25%/20%) were chosen to reflect the thesis, not tested against real-world investment outcomes. Different weights would produce different rankings.
- **Too few companies for statistical proof.** 50 companies (15 real + 35 synthetic) is not enough to draw reliable statistical conclusions about whether the FGAG signal actually predicts returns.
- **Only one measure of "cheapness".** Forward price-to-earnings ratio is the only valuation measure used. A more robust system would combine multiple measures (e.g. price-to-book, enterprise value to earnings, and others).
- **Free hosting with no guarantees.** Streamlit Community Cloud's free tier has no uptime commitment and no access controls — anyone with the link can view the app, and it may occasionally go offline.
- **Narratives cannot adapt to new data.** The written summaries in `ai_analysis.json` are generated once. If the underlying data changes, someone must re-run the generation script to update them.
- **ESG data is loaded but unused.** The `esg_context.csv` file exists in the data folder and is loaded into memory, but it does not feed into any score or appear on any page.
- **Gender treated as binary.** The scoring system recognises only Male and Female. It does not capture non-binary, gender-fluid, or other gender identities.

---

## 8. Intended Use and Out-of-Scope Uses

### Intended use
Athena is a **proof-of-concept** — it demonstrates the idea that female governance quality, financial performance, and relative cheapness can be combined into a single, useful signal. It is designed for:
- Exploring whether there is a relationship between board gender diversity and shareholder returns
- Demonstrating data engineering and visualisation skills as part of an interview challenge
- Presenting a thesis in an interactive, accessible format that anyone can use without technical knowledge

### Out of scope
- **Investment decisions.** Athena is not investment advice and should not be used to buy or sell shares.
- **Regulatory compliance.** The governance classifications are illustrative and should not be treated as official compliance assessments.
- **Drawing statistical conclusions.** The universe is too small and largely synthetic — no reliable statistical claims can be made from this data.
- **Live monitoring.** There is no alerting, portfolio tracking, or real-time data. It is a static analytical tool.

---

## 9. Ethical Considerations

- **Most of the data is made up.** ~70% of the companies are synthetic (fabricated to show how the scoring behaves in different scenarios). These fake companies may not reflect how real-world governance actually works, and any patterns seen across the full universe could be artefacts of how the synthetic data was created.
- **A single number cannot capture the full picture.** Reducing the complexity of corporate governance to a 0–100 score inevitably loses detail. A company labelled "Cosmetic / Token Risk" by the scoring rules may in reality have strong governance practices that the available data simply does not capture.
- **Gender is treated as binary.** The data only records Male or Female. This does not account for non-binary, gender-fluid, or other gender identities. Any future extension of this work should use a more inclusive framework.
- **Companies in progressive jurisdictions may be unfairly penalised.** Pillar 3 gives a 10-point bonus to companies that are *not* legally required to have women on the board. The reasoning is that voluntary action signals stronger commitment — but the flip side is that companies in jurisdictions that pioneered gender quotas (like California or the EU) get no credit for being in places that led the way.
- **Sectors are not evenly represented.** Some sectors have many more companies than others in the universe. Any conclusions about sector-level patterns should be treated with caution.
