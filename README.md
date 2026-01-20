# 🛢️ Refinery Arbitrage Engine
**Real-Time Commodity Margin & Equity Valuation Monitor**

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)]([https://your-app-url-here.streamlit.app]([https://refinery-arbitrage-engine-uturqbhqngbykahhfonr6k.streamlit.app/](https://refinery-arbitrage-engine-uturqbhqngbykahhfonr6k.streamlit.app/)))
*(Click the badge above to launch the live dashboard)*

### 📊 Business Context
Refineries profit from the **"Crack Spread"**—the economic differential between crude oil input costs and refined product output prices (Gasoline & Diesel). This platform models the industry-standard **3:2:1 Crack Spread** to quantify the "Physical Reality" of the energy market and correlates it to downstream equity valuations.

**The "So What?" for Investors:**
When physical margins compress, refinery valuations contract. This engine answers: *If the crack spread drops by $5/bbl today, what is the implied EBITDA impact for Valero (VLO)?*

---

### 🚀 Key Intelligence Modules

#### 1. The Physical Arbitrage Monitor (Engineering Layer)
* **Logic:** Implements the **3:2:1 Mass Balance** formula: `(2 * Gasoline + 1 * Distillate - 3 * Crude) / 3`.
* **Unit Operations:** Automatically handles unit conversion (Gallons $\to$ Barrels) and aligns Futures contract expirations.
* **Alpha:** Identifies "margin expansion" events in real-time before they appear in quarterly earnings reports.

#### 2. Valuation Sensitivity Model (Banking Layer)
* **Goal:** Quantify **Operational Leverage**.
* **Methodology:** A "DCF-Lite" engine that simulates EBITDA shocks based on spread volatility.
* **Scenario:** *User Input:* "What if margins crash to $15/bbl?" $\to$ *Output:* "VLO Share Price implied impact: -$12.45".

#### 3. Statistical Correlation Engine (Quant Layer)
* **Hypothesis:** Downstream equities are mathematically coupled to physical margins.
* **Proof:** Calculates **90-Day Rolling Correlations** to visualize "Regime Changes" (e.g., the 2020 COVID decoupling).
* **Metrics:** Real-time **R-Squared ($R^2$)**, **Z-Score**, and **Percentile Rank**.

---

### 🛠️ Technical Stack
* **Core Logic:** Python (Pandas, NumPy, SciPy)
* **Visualization:** Streamlit, Plotly Interactive (Dual-Axis Charts)
* **Statistics:** Statsmodels (OLS Regression), Rolling Window Analysis
* **Data Pipeline:** `yfinance` API (Real-time Futures: CL=F, RB=F, HO=F)

---

### 💻 Local Installation
To run this engine on your local machine:

```bash
# 1. Clone the repository
git clone https://github.com/your-username/Refinery-Arbitrage-Engine.git

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch the dashboard
streamlit run app/streamlit_app.py
```

### ⚖️ Disclaimer
This project is for educational and portfolio purposes only. It uses free-tier data (Yahoo Finance) which may have delays. Not financial advice.

Built by Liam Egan | [LinkedIn](https://linkedin.com/in/liam-egan) | [Portfolio](https://liamegan.com)
