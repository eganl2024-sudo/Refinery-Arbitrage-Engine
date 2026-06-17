"""
src/bootstrap.py

Ensures market data is available before the Streamlit app renders.
Called automatically on cold starts (fresh Streamlit Cloud container,
redeployment, or any state where the DuckDB file has no processed data).

The NLP/sentiment layer is intentionally excluded here — it requires
separate pipeline runs and is treated as optional in the app UI.
"""

import sys
import os

# Ensure project root is on the path when called from app/
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db import read_processed


def ensure_market_data():
    """
    Check whether processed spread data exists in DuckDB.
    If not, run the market data pipeline and spread calculator to generate it.
    Returns the resulting DataFrame (may still be empty if the fetch fails).
    """
    df = read_processed()
    if not df.empty:
        return df

    print("[bootstrap] No processed data found — running market pipeline...")

    try:
        from src.data_pipeline import fetch_market_data
        result = fetch_market_data(period="5y")
        if result is None:
            print("[bootstrap] ❌ fetch_market_data() returned None — check yfinance connectivity.")
            return read_processed()  # return whatever is there (likely empty)
    except Exception as e:
        print(f"[bootstrap] ❌ data_pipeline failed: {e}")
        return read_processed()

    try:
        from src.spread_calculator import calculate_spread
        calculate_spread()
    except Exception as e:
        print(f"[bootstrap] ❌ spread_calculator failed: {e}")
        return read_processed()

    df = read_processed()
    if df.empty:
        print("[bootstrap] ⚠️  Pipeline ran but processed table is still empty.")
    else:
        print(f"[bootstrap] ✅ Market data ready — {len(df)} rows loaded.")

    return df
