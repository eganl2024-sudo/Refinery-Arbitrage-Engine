import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta
import sys
import os

# --- PATH SETUP ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- MODULE IMPORTS ---
try:
    from src.config import REFINER_CONFIGS, CRACK_FORMULAS, MARKET_EVENTS
    from src.signal_generator import calculate_signal_metrics
    from src.valuation_model import calculate_ebitda_impact, calculate_share_price_impact
    from src.correlation_engine import calculate_correlations
    from src.spread_calculator import compute_correlation_returns
    from src.report_generator import generate_executive_summary
    from src.db import read_processed, read_table
    from src.bootstrap import ensure_market_data
except ImportError as e:
    st.error(f"❌ Module Import Failed: {e}. Ensure you are running from the project root.")
    st.stop()

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Refinery Arbitrage Engine", page_icon="🛢️", layout="wide")

st.markdown("""
<style>
    .metric-card { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
    .stAlert { padding: 10px; }
</style>
""", unsafe_allow_html=True)

# --- DATA LOADING ---
@st.cache_data(ttl=300)
def load_data():
    df = read_processed()
    if df.empty:
        with st.spinner("⏳ First-run detected — fetching market data (this takes ~30 seconds)..."):
            df = ensure_market_data()
    if df.empty:
        st.error("❌ Could not load market data. Check yfinance connectivity and try refreshing.")
        return pd.DataFrame()
    return df

df = load_data()
if df.empty:
    st.stop()

# --- CRACK SPREAD COMPUTATION ---
def compute_spread(frame, formula_key):
    """Return spread series for the selected formula using pre-stored or on-the-fly columns."""
    f = CRACK_FORMULAS[formula_key]
    if f['col'] == 'Crack_Spread':
        return frame['Crack_Spread']
    g_ratio, h_ratio, c_ratio = f['ratios']
    return (g_ratio * frame['Gasoline_bbl'] + h_ratio * frame['Heating_Oil_bbl'] - c_ratio * frame['Crude_Oil']) / c_ratio

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuration")

    # 0. Refiner selector
    refiner_name = st.selectbox(
        "Refiner",
        options=list(REFINER_CONFIGS.keys()),
        index=0,
        help="Switch between VLO and PSX — affects correlation and valuation sections",
    )
    refiner = REFINER_CONFIGS[refiner_name]
    equity_col = refiner['ticker_col']

    st.divider()

    # 1. Crack formula selector
    formula_key = st.radio(
        "Crack Spread Formula",
        options=list(CRACK_FORMULAS.keys()),
        index=0,
        help="3:2:1 is the US Gulf Coast benchmark. Others suit different feedstock/output mixes.",
    )
    st.caption(CRACK_FORMULAS[formula_key]['description'])
    formula_label = CRACK_FORMULAS[formula_key]['label']

    st.divider()

    # 2. Date range
    timeframe = st.selectbox("Lookback Period", ["1 Year", "3 Years", "5 Years", "All Time"], index=2)
    end_date = df.index.max()

    signal_map_defaults = {"1 Year": 1, "3 Years": 2, "5 Years": 3, "All Time": 3}
    default_signal_index = signal_map_defaults.get(timeframe, 2)

    if timeframe == "1 Year":
        start_date = end_date - timedelta(days=365)
    elif timeframe == "3 Years":
        start_date = end_date - timedelta(days=365 * 3)
    elif timeframe == "5 Years":
        start_date = end_date - timedelta(days=365 * 5)
    else:
        start_date = df.index.min()

    st.divider()

    # 3. Signal settings
    st.subheader("🎯 Signal Settings")
    signal_window = st.selectbox(
        "Signal Calculation Period",
        ["30 Days", "90 Days", "1 Year", "All Time"],
        index=default_signal_index,
        help="Time period for Z-score and percentile calculations",
    )
    window_map = {"30 Days": 30, "90 Days": 90, "1 Year": 252, "All Time": None}
    signal_days = window_map[signal_window]

    st.divider()

    # 4. Valuation inputs (refiner-specific)
    short_name = refiner_name.split(' ')[0]
    st.header(f"💰 Valuation — {short_name}")
    st.info("Simulate a shock to the crack spread.")

    throughput = st.number_input("Throughput (bpd)", value=refiner['throughput_bpd'], step=100_000)
    capture_rate = st.slider("Capture Rate (%)", 70, 100, int(refiner['capture_rate'] * 100)) / 100
    shares = st.number_input("Shares (M)", value=refiner['shares_outstanding'] / 1_000_000, step=5.0) * 1_000_000

    st.markdown("---")

    # Compute active spread on full df for current values
    df['Active_Spread'] = compute_spread(df, formula_key)
    current_spread_val = float(df['Active_Spread'].iloc[-1])

    # Preset buttons — must come BEFORE slider so session_state is set before slider renders
    if 'shock_target' not in st.session_state:
        st.session_state['shock_target'] = current_spread_val + 5.0

    b1, b2, b3 = st.columns(3)
    if b1.button("📉 Bear"):
        st.session_state['shock_target'] = float(np.clip(current_spread_val - 10.0, 0.0, 60.0))
    if b2.button("📊 Base"):
        st.session_state['shock_target'] = float(current_spread_val)
    if b3.button("📈 Bull"):
        st.session_state['shock_target'] = float(np.clip(current_spread_val + 10.0, 0.0, 60.0))

    shock_spread = st.slider(
        "Scenario Spread ($/bbl)",
        0.0,
        60.0,
        value=float(np.clip(st.session_state['shock_target'], 0.0, 60.0)),
        key='shock_slider',
        help="Adjust scenario; presets above snap to Bear/Base/Bull anchors",
    )
    # Sync slider back so manual drag persists on next rerun
    st.session_state['shock_target'] = shock_spread

# --- Filtered data + active spread for selected window ---
filtered_df = df.loc[start_date:end_date].copy()
# Active_Spread already set on df above; slice carries it through

# --- MAIN DASHBOARD ---
st.title("🛢️ Refinery Arbitrage Engine")
st.markdown(f"**Formula:** {formula_label} Crack Spread &nbsp;|&nbsp; **Refiner:** {refiner_name}")

tabs = st.tabs(["📊 Market Dashboard", "📰 Sentiment & Topics"])

# ─────────────────────────────────────────────────────────────────────────────
with tabs[0]:

    # Executive summary
    st.markdown("### 📝 Executive Briefing")
    st.info(generate_executive_summary(filtered_df))
    st.divider()

    # KPI Row
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    active_spread_series = df['Active_Spread']
    current_active = float(latest['Active_Spread'])
    ma_30 = active_spread_series.rolling(30).mean().iloc[-1]

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.metric(
            f"Gross Margin ({formula_label})",
            f"${current_active:.2f}",
            f"{current_active - ma_30:+.2f} vs 30D MA",
            help=f"{formula_label} crack spread — theoretical refining margin per barrel before operating costs",
        )
    with c2:
        if 'Net_Refining_Margin' in df.columns:
            net_val = float(latest['Net_Refining_Margin'])
            net_ma = df['Net_Refining_Margin'].rolling(30).mean().iloc[-1]
            st.metric(
                "Net Margin (After OpEx)",
                f"${net_val:.2f}",
                f"{net_val - net_ma:+.2f} vs 30D MA",
                help="Gross margin minus NatGas variable cost (0.45 MMBtu/bbl) and fixed OpEx ($6/bbl)",
            )
        else:
            st.metric("Net Margin", "N/A", "Run pipeline")
    with c3:
        st.metric(
            "WTI Crude",
            f"${latest['Crude_Oil']:.2f}",
            f"{latest['Crude_Oil'] - prev['Crude_Oil']:.2f}",
            delta_color="inverse",
            help="Lower crude = better margins for refiners (inverse color)",
        )
    with c4:
        equity_val = float(latest[equity_col])
        equity_prev = float(prev[equity_col])
        st.metric(
            short_name,
            f"${equity_val:.2f}",
            f"{equity_val - equity_prev:.2f}",
            help=f"{refiner_name} stock price",
        )
    with c5:
        metrics = calculate_signal_metrics(active_spread_series, window=signal_days)
        st.metric(
            "Market Signal",
            metrics['signal'],
            f"Z: {metrics['z_score']:.2f}σ | Pctl: {metrics['percentile']:.0f}%",
            help="Z>+1σ = Bullish margins; Z<-1σ = Bearish. Percentile ranks current vs. selected window.",
        )

    # Margin trend chart
    st.subheader(f"📈 {formula_label} Crack Spread — Gross vs Net Margin")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=filtered_df.index, y=filtered_df['Active_Spread'],
        mode='lines', name=f'Gross Margin ({formula_label})',
        line=dict(color='#1f77b4', width=2),
    ))
    if 'Net_Refining_Margin' in filtered_df.columns:
        fig.add_trace(go.Scatter(
            x=filtered_df.index, y=filtered_df['Net_Refining_Margin'],
            mode='lines', name='Net Margin (Realized)',
            line=dict(color='#2ca02c', width=2),
            fill='tonexty', fillcolor='rgba(44,160,44,0.1)',
        ))
    spread_ma = filtered_df['Active_Spread'].rolling(30).mean()
    fig.add_trace(go.Scatter(
        x=filtered_df.index, y=spread_ma,
        mode='lines', name='30D Avg',
        line=dict(color='#ff7f0e', width=1, dash='dot'),
    ))
    events_visible = False
    for date, label in MARKET_EVENTS:
        date_obj = pd.to_datetime(date)
        if start_date <= date_obj <= end_date:
            fig.add_vline(x=date, line_dash="dash", line_color="gray")
            fig.add_annotation(x=date, y=filtered_df['Active_Spread'].max(), text=label)
            events_visible = True
    fig.update_layout(
        height=500, hovermode="x unified",
        legend=dict(orientation="h", y=1.02, x=0.5, xanchor='center'),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("**OpEx:** Variable = NatGas (NG=F) × 0.45 MMBtu/bbl. Fixed = $6/bbl (labor, maintenance, catalysts).")
    if not events_visible:
        st.caption("ℹ️ No major market events in selected timeframe. Try '5 Years' to see historical catalysts.")

    # Correlation section
    st.divider()
    st.subheader(f"🔗 Spread–Equity Correlation: {formula_label} vs {refiner_name}")

    @st.cache_data(ttl=300)
    def get_correlations_cached(spread_vals, equity_vals):
        s = pd.Series(spread_vals)
        e = pd.Series(equity_vals)
        work = pd.DataFrame({'s': s, 'e': e}).dropna()
        corr = work['s'].corr(work['e'])
        r2 = corr ** 2
        rolling = work['s'].rolling(90).corr(work['e'])
        return float(corr), float(r2), rolling

    @st.cache_data(ttl=300)
    def get_returns_corr_cached(spread_vals, equity_vals):
        s = pd.Series(spread_vals)
        e = pd.Series(equity_vals)
        work = pd.DataFrame({'s': s, 'e': e}).pct_change().dropna()
        return float(work['s'].corr(work['e']))

    spread_arr = filtered_df['Active_Spread'].values
    equity_arr = filtered_df[equity_col].values

    corr, r2, rolling_corr = get_correlations_cached(spread_arr, equity_arr)
    corr_returns = get_returns_corr_cached(spread_arr, equity_arr)

    # Returns correlation is the headline — analytically more meaningful
    ret_strength = "Strong" if abs(corr_returns) > 0.30 else "Moderate" if abs(corr_returns) > 0.15 else "Weak"
    ret_icon = "🟢" if abs(corr_returns) > 0.30 else "🟡" if abs(corr_returns) > 0.15 else "🔴"

    cr1, cr2, cr3 = st.columns(3)
    cr1.metric(
        "Correlation (Daily Returns)",
        f"{corr_returns:.2f}",
        f"{ret_icon} {ret_strength} fundamental link",
        help="Pearson correlation of daily % changes. Removes long-term equity drift — more analytically meaningful than price levels.",
    )
    cr2.metric(
        "Correlation (Price Levels)",
        f"{corr:.2f}",
        "Inflated by equity drift",
        help="Levels correlation overstates the link because stock prices trend up over time independent of crack spreads.",
    )
    cr3.metric(
        "R² (Returns)",
        f"{corr_returns**2:.2f}",
        f"{corr_returns**2 * 100:.0f}% of daily moves explained",
        help="Share of daily equity return variance explained by crack spread daily changes.",
    )

    if abs(corr_returns) < 0.15:
        st.warning(
            f"⚠️ Returns correlation is {corr_returns:.2f} — {refiner_name} is likely trading on macro, buybacks, "
            "or forward guidance rather than current spot margins."
        )

    with st.expander("🔬 Why Returns Correlation, Not Price Levels?", expanded=False):
        st.markdown("""
**Price Levels** correlate raw values: a $22/bbl spread vs. a $183 stock price.
Both trend up over years (equity drift, secular commodity cycles), inflating the Pearson coefficient.

**Daily % Returns** ask: "On days the spread moved +2%, did the stock also move up?"
This isolates the fundamental relationship, removing trend noise.

Rule of thumb: |r| > 0.30 on returns = strong real-time margin pricing, worth trading.
|r| < 0.15 = macro or valuation multiple is the dominant driver.
        """)

    t1, t2 = st.tabs(["Regime Analysis (Rolling Corr)", "Fair Value Regression"])
    with t1:
        rolling_series = rolling_corr
        rolling_series.index = filtered_df.index[:len(rolling_series)]
        fig_roll = px.line(
            rolling_series,
            title=f"Rolling 90-Day Correlation: {formula_label} vs {refiner_name}",
            labels={'value': 'Correlation', 'index': 'Date'},
        )
        fig_roll.add_hline(y=0, line_dash="dash", line_color="gray")
        fig_roll.add_hline(y=0.3, line_dash="dot", line_color="green", annotation_text="Strong-link threshold (0.30)")
        fig_roll.add_hline(y=-0.3, line_dash="dot", line_color="red")
        st.plotly_chart(fig_roll, use_container_width=True)
        st.caption("Regime shifts (correlation dropping or sign-flipping) show periods where macro overrides fundamentals.")
    with t2:
        try:
            st.plotly_chart(
                px.scatter(
                    filtered_df, x='Active_Spread', y=equity_col, trendline='ols',
                    title=f"Fair Value: {formula_label} Crack Spread vs {refiner_name}",
                    labels={'Active_Spread': f'{formula_label} Crack Spread ($/bbl)', equity_col: f'{short_name} Price ($)'},
                ),
                use_container_width=True,
            )
        except Exception:
            st.warning("Install statsmodels for OLS trendline: `pip install statsmodels`")

    # Valuation sensitivity
    st.divider()
    st.subheader(f"⚡ Valuation Sensitivity — {refiner_name}")

    impact = calculate_ebitda_impact(throughput, capture_rate, current_active, shock_spread)
    price_delta, _ = calculate_share_price_impact(
        refiner['current_ebitda'], impact, refiner['ev_ebitda_multiple'], shares
    )

    v1, v2, v3 = st.columns(3)
    v1.metric(
        "Scenario Spread",
        f"${shock_spread:.2f}",
        f"{shock_spread - current_active:.2f} Delta",
        delta_color="off",
        help=f"Hypothetical {formula_label} crack spread vs current ${current_active:.2f}/bbl",
    )
    v2.metric(
        "EBITDA Impact",
        f"${impact / 1e6:,.0f}M",
        "Annualized",
        help=f"Δspread × {throughput / 1e6:.1f}M bpd throughput × 365 days × {capture_rate:.0%} capture rate",
    )
    v3.metric(
        "Share Price Impact",
        f"${price_delta:+.2f}",
        f"at {refiner['ev_ebitda_multiple']}x EV/EBITDA",
        help="ΔEBITDA × EV/EBITDA multiple ÷ shares outstanding. Assumes constant net debt.",
    )

# ─────────────────────────────────────────────────────────────────────────────
with tabs[1]:
    st.header("📰 EIA Sentiment Analysis")

    @st.cache_data(ttl=1800)
    def load_sentiment_data():
        df_merged = read_table('sentiment_spread_merged')
        if not df_merged.empty:
            df_merged['report_date'] = pd.to_datetime(df_merged['report_date'])
            df_merged.set_index('report_date', inplace=True)
        df_roll = read_table('sentiment_spread_rolling_corr')
        if not df_roll.empty:
            df_roll['date'] = pd.to_datetime(df_roll['date'])
        df_sent = read_table('eia_sentiment')
        return df_merged, df_roll, df_sent

    df_merged, df_roll, df_sent = load_sentiment_data()

    if df_sent.empty or df_merged.empty:
        st.warning("No sentiment data available. Please run the NLP pipeline first.")
    else:
        latest_sent = df_sent.iloc[-1]
        last_4_avg = df_sent['compound'].tail(4).mean()
        total_reports = len(df_sent)

        # Live Granger causality from merged DB table
        @st.cache_data(ttl=3600)
        def compute_granger(n_obs):
            """Run Granger causality on sentiment → crack spread. Cache key = row count."""
            try:
                from statsmodels.tsa.stattools import grangercausalitytests
                data = df_merged[['Crack_Spread', 'compound']].dropna()
                if len(data) < 10:
                    return None, None, None
                results = grangercausalitytests(data.values, maxlag=[1, 2, 3, 4], verbose=False)
                p_vals = {lag: results[lag][0]['ssr_ftest'][1] for lag in [1, 2, 3, 4]}
                min_p = min(p_vals.values())
                best_lag = min(p_vals, key=p_vals.get)
                return min_p, best_lag, p_vals
            except Exception:
                return None, None, None

        min_p, best_lag, p_vals = compute_granger(len(df_merged))

        if min_p is None:
            granger_label, granger_delta = "N/A", "Insufficient data"
        elif min_p < 0.05:
            granger_label = "Significant"
            granger_delta = f"p={min_p:.3f} at lag {best_lag}wk"
        else:
            granger_label = "Not Significant"
            granger_delta = f"p={min_p:.3f} min across lags"

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Latest Sentiment Score", f"{latest_sent['compound']:.2f}",
                  help="VADER compound: +1 = maximally positive, -1 = maximally negative")
        m2.metric("4-Week Avg Sentiment", f"{last_4_avg:.2f}")
        m3.metric("Total Reports Analyzed", f"{total_reports}")
        m4.metric(
            "Granger Causality",
            granger_label,
            granger_delta,
            delta_color="off",
            help="Tests whether past EIA sentiment predicts future crack spreads beyond the spread's own history",
        )

        if p_vals:
            with st.expander("📊 Granger Test Detail — All Lags"):
                lag_df = pd.DataFrame([
                    {
                        'Lag (weeks)': lag,
                        'p-value': f"{p:.4f}",
                        'Significant (p<0.05)': '✅' if p < 0.05 else '❌',
                    }
                    for lag, p in p_vals.items()
                ])
                st.dataframe(lag_df, use_container_width=True, hide_index=True)
                st.caption(
                    "Granger causality: does knowing past EIA sentiment improve forecast of future crack spreads "
                    "beyond what the spread's own history already tells you? p<0.05 = yes. "
                    "p>0.05 is consistent with semi-strong market efficiency — public EIA data is rapidly priced into futures."
                )

        st.divider()
        st.subheader("Sentiment vs. Crack Spread")
        from plotly.subplots import make_subplots
        fig2 = make_subplots(specs=[[{"secondary_y": True}]])
        fig2.add_trace(
            go.Scatter(x=df_merged.index, y=df_merged['compound'],
                       name="Sentiment (Compound)", line=dict(color='#1f77b4')),
            secondary_y=False,
        )
        fig2.add_trace(
            go.Scatter(x=df_merged.index, y=df_merged['Crack_Spread'],
                       name="Crack Spread ($/bbl)", line=dict(color='#ff7f0e')),
            secondary_y=True,
        )
        fig2.update_layout(
            title="EIA Sentiment vs. 3:2:1 Crack Spread",
            hovermode="x unified",
            legend=dict(orientation="h", y=1.1, x=0.5, xanchor='center'),
        )
        st.plotly_chart(fig2, use_container_width=True)

        st.divider()
        st.subheader("Sentiment Correlation")
        fig3 = px.line(df_roll, x='date', y='rolling_corr',
                       title="Rolling 90-Day Sentiment–Spread Correlation")
        fig3.add_hline(y=0, line_dash="dash", line_color="gray")
        st.plotly_chart(fig3, use_container_width=True)

        st.divider()
        st.subheader("Topic Extractor")
        topic_summary = (
            df_sent.groupby('dominant_topic')
            .agg(Avg_Sentiment=('compound', 'mean'), Report_Count=('compound', 'count'))
            .reset_index()
            .rename(columns={'dominant_topic': 'Topic', 'Avg_Sentiment': 'Avg Sentiment', 'Report_Count': 'Report Count'})
        )
        st.dataframe(topic_summary, use_container_width=True)
        st.caption("LDA Topic Modeling — 5 topics extracted via sklearn")

        with st.expander("🔬 About This Analysis"):
            st.markdown(
                f"**Methodology:** {total_reports} EIA reports scraped (2022–2025). "
                "Scored using VADER for sentiment polarity; 5 topics via sklearn LDA. "
                f"Granger causality (lags 1–4 weeks): **{granger_label.lower()}** ({granger_delta}). "
                "Consistent with semi-strong market efficiency — public EIA data is rapidly priced into front-month futures."
            )
