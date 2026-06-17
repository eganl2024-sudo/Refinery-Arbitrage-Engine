# Refinery Arbitrage Engine

[![Live Dashboard](https://img.shields.io/badge/Live_Dashboard-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit)](https://refinery-arbitrage-engine-uturqbhqngbykahhfonr6k.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python)](https://python.org)

A live financial analytics platform that models US Gulf Coast refinery economics and tests whether institutional energy commentary predicts margin movements.

**Live dashboard:** https://refinery-arbitrage-engine-uturqbhqngbykahhfonr6k.streamlit.app/

---

## Overview

The engine computes real-time 3:2:1 crack spreads — the benchmark measure of refinery profitability — by pricing WTI crude inputs against RBOB gasoline and heating oil outputs. It extends this physical margin into net profitability by modeling variable and fixed operating costs, then translates margin shocks into EBITDA and share price impacts for Valero (VLO) using a cycle-aware valuation framework.

A second research layer scrapes and analyzes 87 institutional reports from the U.S. Energy Information Administration (2022–2026), applying VADER sentiment analysis and LDA topic modeling to test a practical question in commodity finance: does public institutional commentary lead or lag the market it describes?

---

## Research Question

**Does EIA sentiment Granger-cause crack spread movements?**

Bidirectional Granger causality tests at lags of 1–4 weeks found no significant relationship in either direction (all p > 0.05). The result is consistent with semi-strong market efficiency: by the time institutional commentary is published, its signal is already priced. The corpus also spans a structural break — EIA discontinued its long-form *This Week in Petroleum* reports in January 2024, replacing them with shorter *Today in Energy* articles — which introduces a measurable shift in document length and sentiment distribution that itself warrants analysis.

---

## Architecture

| Module | Function |
|---|---|
| `src/data_pipeline.py` | Market data ingestion via yfinance (CL=F, RB=F, HO=F, NG=F, VLO, PSX) |
| `src/db.py` | DuckDB database layer — all I/O, table init, and read/write helpers |
| `src/bootstrap.py` | Cold-start bootstrap — auto-generates market data on first deploy |
| `src/spread_calculator.py` | 3:2:1 crack spread, net margin, and moving average calculations |
| `src/signal_generator.py` | Z-score and percentile market signal metrics |
| `src/correlation_engine.py` | VLO price correlation and rolling OLS regression |
| `src/valuation_model.py` | EBITDA sensitivity, cyclical EV/EBITDA multiples, run-cut logic |
| `src/eia_scraper.py` | Hybrid scraper across TWIP archive and Today in Energy (87 reports) |
| `src/nlp_pipeline.py` | VADER sentiment scoring and sklearn LDA topic modeling (5 topics) |
| `src/causality_analysis.py` | Bidirectional Granger causality, 4-lag window, rolling correlation |
| `app/streamlit_app.py` | Two-tab Streamlit dashboard: Market Dashboard and Sentiment & Topics |

---

## Data

**Market prices:** 5-year daily history for WTI crude, RBOB gasoline, heating oil, natural gas, Valero, and Phillips 66.

**Text corpus:** 87 EIA institutional reports spanning January 2022 through February 2026, drawn from two sources:
- *This Week in Petroleum* weekly reports (2022–2023) — structured long-form analysis, averaging 800–1,400 words
- *EIA Today in Energy* petroleum articles (2024–2026) — shorter-form successors, averaging 400–800 words

---

## Valuation Model

Two structural upgrades replace the naive linear model with cycle-aware logic:

**Cyclical multiples.** The EV/EBITDA multiple applied to margin shocks adjusts inversely with the spread's Z-score — from 8.5x at trough conditions to 4.5x at peak — reflecting the empirical pattern of multiple compression when earnings are at cycle highs and expansion when they are at lows.

**Economic run-cut floor.** When the scenario spread falls below the $7.50/bbl operating breakeven, throughput is reduced programmatically (20% below breakeven, 40% at zero margin) to emulate real-world margin protection behavior. Bear-case scenarios are materially more adverse than a linear model would suggest.

---

## Limitations

- An 87-document corpus is modest for time-series causality work; results should be interpreted directionally rather than conclusively
- The January 2024 TWIP discontinuation introduces a structural break in document format that may reduce sentiment comparability across the full time series
- yfinance is a free-tier data source subject to rate limiting and occasional gaps; institutional-grade feeds would improve pipeline reliability

---

## How to Run

```bash
# 1. Create and activate a Python 3.11 virtual environment
py -3.11 -m venv venv
venv\Scripts\activate

# 2. Install pinned dependencies
pip install -r requirements.txt

# 3. Run the pipeline in sequence
python src/data_pipeline.py
python src/eia_scraper.py
python src/nlp_pipeline.py
python src/causality_analysis.py

# 4. Launch the dashboard
streamlit run app/streamlit_app.py
```

---

## Streamlit Cloud Deployment

| Setting | Value |
|---|---|
| Repository | `eganl2024-sudo/Refinery-Arbitrage-Engine` |
| Branch | `main` |
| App entrypoint | `app/streamlit_app.py` |
| Python version | 3.11 |
| First-boot behavior | Market data fetched automatically via `src/bootstrap.py` (~30s) |
| Sentiment tab | Requires separate NLP pipeline run; degrades gracefully if absent |

---

## Tech Stack

Python 3.11 · DuckDB · Streamlit · yfinance · VADER · scikit-learn · statsmodels · BeautifulSoup4 · Plotly
