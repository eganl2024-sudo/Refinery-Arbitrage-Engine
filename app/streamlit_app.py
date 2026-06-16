import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
import os

# --- PATH SETUP ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- MODULE IMPORTS ---
try:
    from src.config import VLO_DEFAULTS, MARKET_EVENTS
    from src.signal_generator import calculate_signal_metrics
    from src.valuation_model import calculate_ebitda_impact, calculate_share_price_impact
    from src.correlation_engine import calculate_correlations
    from src.report_generator import generate_executive_summary
    from src.db import read_processed, read_table
    from src.bootstrap import ensure_market_data
except ImportError as e:
    st.error(f"❌ Module Import Failed: {e}. Ensure you are running from the project root.")
    st.stop()

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Refinery Arbitrage Engine", page_icon="🛢️", layout="wide")

# --- CSS STYLING ---
st.markdown("""
<style>
    .metric-card { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
    .stAlert { padding: 10px; }
</style>
""", unsafe_allow_html=True)

# --- DATA LOADING ---
@st.cache_data
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
if df.empty: st.stop()

# --- SIDEBAR CONFIGURATION ---
with st.sidebar:
    st.header("⚙️ Configuration")

    # 1. Date Range
    timeframe = st.selectbox("Lookback Period", ["1 Year", "3 Years", "5 Years", "All Time"], index=2)
    end_date = df.index.max()

    signal_map_defaults = {
        "1 Year": 1,
        "3 Years": 2,
        "5 Years": 3,
        "All Time": 3
    }
    default_signal_index = signal_map_defaults.get(timeframe, 2)

    if timeframe == "1 Year": start_date = end_date - timedelta(days=365)
    elif timeframe == "3 Years": start_date = end_date - timedelta(days=365*3)
    elif timeframe == "5 Years": start_date = end_date - timedelta(days=365*5)
    else: start_date = df.index.min()

    filtered_df = df.loc[start_date:end_date]

    st.divider()

    # 2. Signal Settings
    st.subheader("🎯 Signal Settings")
    signal_window = st.selectbox(
        "Signal Calculation Period",
        ["30 Days", "90 Days", "1 Year", "All Time"],
        index=default_signal_index,
        help="Time period for Z-score and percentile calculations"
    )
    window_map = {"30 Days": 30, "90 Days": 90, "1 Year": 252, "All Time": None}
    signal_days = window_map[signal_window]

    st.divider()

    # 3. Valuation Inputs
    st.header("💰 Valuation Model")
    st.info("Simulate a shock to the 3:2:1 Crack Spread.")

    throughput = st.number_input("Throughput (bpd)", value=VLO_DEFAULTS['throughput_bpd'], step=100_000)
    capture_rate = st.slider("Capture Rate (%)", 70, 100, int(VLO_DEFAULTS['capture_rate']*100)) / 100
    shares = st.number_input("Shares (M)", value=VLO_DEFAULTS['shares_outstanding']/1_000_000, step=5.0) * 1_000_000

    st.markdown("---")

    latest = df.iloc[-1]
    current_spread_val = latest['Crack_Spread']
    default_scenario = float(current_spread_val) + 5.0

    shock_spread = st.slider(
        "Scenario Spread ($/bbl)",
        0.0, 60.0,
        default_scenario,
        help="Adjust to see impact of margin compression/expansion"
    )

    c1, c2, c3 = st.columns(3)
    if c1.button("📉 Bear"): shock_spread = current_spread_val - 10
    if c2.button("📊 Base"): shock_spread = current_spread_val
    if c3.button("📈 Bull"): shock_spread = current_spread_val + 10

# --- MAIN DASHBOARD ---
st.title("🛢️ Refinery Arbitrage Engine")
st.markdown("**Objective:** Quantify the theoretical margins (Gross & Net) of US Gulf Coast refineries.")

# --- TABS SETUP ---
tabs = st.tabs(["📊 Market Dashboard", "📰 Sentiment & Topics"])

with tabs[0]:
    # --- EXECUTIVE SUMMARY ---
    st.markdown("### 📝 Executive Briefing")
    summary_text = generate_executive_summary(filtered_df)
    st.info(summary_text)

    st.divider()

    # 1. KPI ROW
    latest = df.iloc[-1]
    ma_30 = latest['Spread_30D_MA']
    delta_vs_ma = latest['Crack_Spread'] - ma_30

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.metric("Gross Margin (3:2:1)", f"${latest['Crack_Spread']:.2f}", f"{delta_vs_ma:+.2f} vs 30D MA", help="Current spread relative to 30-day moving average")

    with c2:
        if 'Net_Refining_Margin' in df.columns:
            net_val = latest['Net_Refining_Margin']
            net_ma_30 = latest['Net_Margin_30D_MA']
            net_delta = net_val - net_ma_30
            st.metric("Net Margin (After OpEx)", f"${net_val:.2f}", f"{net_delta:+.2f} vs 30D MA")
        else:
            st.metric("Net Margin", "N/A", "Run Phase 7")

    with c3:
        prev = df.iloc[-2]
        st.metric("WTI Crude", f"${latest['Crude_Oil']:.2f}", f"{latest['Crude_Oil']-prev['Crude_Oil']:.2f}", delta_color="inverse")

    with c4:
        st.metric("Valero (VLO)", f"${latest['Valero']:.2f}", f"{latest['Valero']-prev['Valero']:.2f}")

    with c5:
        metrics = calculate_signal_metrics(df['Crack_Spread'], window=signal_days)
        st.metric("Market Signal", metrics['signal'], f"Z: {metrics['z_score']:.2f}σ | Pctl: {metrics['percentile']:.0f}%", help="Z-score vs. percentile: -1σ ≈ 16th %ile, 0σ = 50th %ile, +1σ ≈ 84th %ile")

    # 2. CHARTS & TRENDS
    st.subheader("📈 Margin Trends (Gross vs Net)")
    fig = go.Figure()

    fig.add_trace(go.Scatter(x=filtered_df.index, y=filtered_df['Crack_Spread'], mode='lines', name='Gross Margin (3:2:1)', line=dict(color='#1f77b4', width=2)))

    if 'Net_Refining_Margin' in filtered_df.columns:
        fig.add_trace(go.Scatter(x=filtered_df.index, y=filtered_df['Net_Refining_Margin'], mode='lines', name='Net Margin (Realized)', line=dict(color='#2ca02c', width=2), fill='tonexty', fillcolor='rgba(44, 160, 44, 0.1)'))

    fig.add_trace(go.Scatter(x=filtered_df.index, y=filtered_df['Spread_30D_MA'], mode='lines', name='30D Avg (Gross)', line=dict(color='#ff7f0e', width=1, dash='dot')))

    events_visible = False
    for date, label in MARKET_EVENTS:
        date_obj = pd.to_datetime(date)
        if start_date <= date_obj <= end_date:
            fig.add_vline(x=date, line_dash="dash", line_color="gray")
            fig.add_annotation(x=date, y=filtered_df['Crack_Spread'].max(), text=label)
            events_visible = True

    fig.update_layout(height=500, hovermode="x unified", legend=dict(orientation="h", y=1.02, x=0.5, xanchor='center'))
    st.plotly_chart(fig, use_container_width=True)

    st.caption("""**OpEx Assumptions:** Variable cost based on Natural Gas (NG=F) × 0.45 MMBtu/bbl. Fixed cost ($6/bbl) represents labor, maintenance, and catalyst expenses. *Industry range: $4-8/bbl.*""")

    if not events_visible:
        st.caption("ℹ️ No major market events in selected timeframe. Try '5 Years' to see historical catalysts.")

    # 3. CORRELATION ENGINE
    st.divider()
    st.subheader("🔗 Market Intelligence")

    @st.cache_data
    def get_correlations(df):
        return calculate_correlations(df, 'Crack_Spread', 'Valero')

    corr, r2, rolling = get_correlations(filtered_df)

    with st.expander("🔬 Correlation Methodology: Levels vs. Returns", expanded=False):
        col_a, col_b = st.columns(2)
        with col_a:
            st.write("**Method 1: Price Levels**")
            st.caption("Correlates $22 spread vs. $183 stock price.")
            st.metric("Correlation (Levels)", f"{corr:.2f}")
        with col_b:
            st.write("**Method 2: % Returns**")
            st.caption("Correlates daily % change in spread vs VLO.")

            @st.cache_data
            def get_corr_returns(df):
                from src.spread_calculator import compute_correlation_returns
                return compute_correlation_returns(df, 'Crack_Spread', 'Valero')

            corr_returns = get_corr_returns(filtered_df)
            st.metric("Correlation (Returns)", f"{corr_returns:.2f}")

        st.info("**Analysis:** Stock prices trend up over time (earnings/buybacks) while spreads are cyclical. If 'Returns' correlation is higher, VLO reacts to daily spread changes, even if the long-term price trend is decoupled.")

    if abs(corr) > 0.7:
        corr_context = "🟢 Strong fundamental link"
    elif abs(corr) > 0.4:
        corr_context = "🟡 Moderate link (mixed drivers)"
    else:
        corr_context = "🔴 Decoupled (sentiment/policy driven)"

    c1, c2, c3 = st.columns(3)
    c1.metric("Correlation (Levels)", f"{corr:.2f}", help="Pearson Coefficient")
    c2.metric("R-Squared", f"{r2:.2f}", help="Explained Variance")
    c3.metric("Link Strength", "Strong" if abs(corr)>0.7 else "Weak", help=corr_context)

    if abs(corr) < 0.3 and abs(corr_returns) < 0.3:
        st.warning(f"⚠️ Weak correlation detected in both Levels ({corr:.2f}) and Returns ({corr_returns:.2f}). VLO is likely trading on macro sentiment, buybacks, or forward earnings expectations rather than current spot margins.")

    t1, t2 = st.tabs(["Regime Analysis", "Fair Value Regression"])
    with t1:
        st.plotly_chart(px.line(rolling, title="Rolling Correlation"), use_container_width=True)
    with t2:
        try:
            st.plotly_chart(px.scatter(filtered_df, x='Crack_Spread', y='Valero', trendline='ols', title="Fair Value Model"), use_container_width=True)
        except:
            st.warning("Install statsmodels for trendlines.")

    # 4. VALUATION SENSITIVITY
    st.divider()
    st.subheader("⚡ Valuation Sensitivity")
    impact = calculate_ebitda_impact(throughput, capture_rate, current_spread_val, shock_spread)
    price_delta, _ = calculate_share_price_impact(VLO_DEFAULTS['current_ebitda'], impact, VLO_DEFAULTS['ev_ebitda_multiple'], shares)

    c1, c2, c3 = st.columns(3)
    c1.metric("Scenario Spread", f"${shock_spread:.2f}", f"{shock_spread-current_spread_val:.2f} Delta", delta_color="off")
    c2.metric("EBITDA Impact", f"${impact/1e6:,.0f} M", "Annualized", delta_color="inverse" if impact > 0 else "normal")
    c3.metric("Share Price Impact", f"${price_delta:+.2f}", f"at {VLO_DEFAULTS['ev_ebitda_multiple']}x EV/EBITDA", delta_color="inverse" if impact > 0 else "normal")

with tabs[1]:
    st.header("📰 EIA Sentiment Analysis")

    @st.cache_data
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
        st.info(
            "📭 Sentiment data not available. The Market Dashboard above is fully operational.\n\n"
            "To populate this tab, run the NLP pipeline locally:\n"
            "```\npython src/eia_scraper.py\npython src/nlp_pipeline.py\npython src/causality_analysis.py\n```"
        )
    else:
        latest_sent = df_sent.iloc[-1]
        last_4_avg = df_sent['compound'].tail(4).mean()
        total_reports = len(df_sent)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Latest Sentiment Score", f"{latest_sent['compound']:.2f}")
        m2.metric("4-Week Avg Sentiment", f"{last_4_avg:.2f}")
        m3.metric("Total Reports Analyzed", f"{total_reports}")
        m4.metric("Granger Causality", "Not Significant", "p>0.05 all lags", delta_color="off")

        st.divider()
        st.subheader("Sentiment vs. Crack Spread")
        from plotly.subplots import make_subplots
        fig2 = make_subplots(specs=[[{"secondary_y": True}]])
        fig2.add_trace(go.Scatter(x=df_merged.index, y=df_merged['compound'], name="Sentiment (Compound)", line=dict(color='#1f77b4')), secondary_y=False)
        fig2.add_trace(go.Scatter(x=df_merged.index, y=df_merged['Crack_Spread'], name="Crack Spread ($/bbl)", line=dict(color='#ff7f0e')), secondary_y=True)
        fig2.update_layout(title="EIA Sentiment vs. 3:2:1 Crack Spread", hovermode="x unified", legend=dict(orientation="h", y=1.1, x=0.5, xanchor='center'))
        st.plotly_chart(fig2, use_container_width=True)

        if not df_roll.empty:
            st.divider()
            st.subheader("Sentiment Correlation")
            fig3 = px.line(df_roll, x='date', y='rolling_corr', title="Rolling 90-Day Sentiment-Spread Correlation")
            fig3.add_hline(y=0, line_dash="dash", line_color="gray")
            st.plotly_chart(fig3, use_container_width=True)

        if not df_sent.empty and 'dominant_topic' in df_sent.columns:
            st.divider()
            st.subheader("Topic Extractor")
            topic_summary = df_sent.groupby('dominant_topic').agg(
                Avg_Sentiment=('compound', 'mean'),
                Report_Count=('compound', 'count')
            ).reset_index()
            topic_summary.rename(columns={'dominant_topic': 'Topic', 'Avg_Sentiment': 'Avg Sentiment', 'Report_Count': 'Report Count'}, inplace=True)
            st.dataframe(topic_summary, use_container_width=True)
            st.caption("LDA Topic Modeling — 5 topics extracted via sklearn")

        with st.expander("🔬 About This Analysis"):
            st.markdown(f"**Methodology:** {total_reports} EIA reports scraped (2022-2025). "
                        "Reports were scored using VADER for sentiment polarity and processed using scikit-learn's LatentDirichletAllocation (LDA) to extract 5 topics. "
                        "Granger causality was tested on the merged dataset at lags of 1-4 weeks between sentiment and crack spreads, which found no significant predictive relationship (p > 0.05) - "
                        "an outcome consistent with semi-strong market efficiency where public EIA data is instantly priced into front-month futures.")
