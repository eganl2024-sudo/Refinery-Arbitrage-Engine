import duckdb
import pandas as pd
import os

# --- Absolute path resolution: safe in any launch context ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "market_data.duckdb")

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return duckdb.connect(DB_PATH)

def init_db():
    con = get_connection()
    con.execute("""
        CREATE TABLE IF NOT EXISTS raw_market_data (
            Date TIMESTAMP PRIMARY KEY,
            Crude_Oil DOUBLE,
            Gasoline DOUBLE,
            Heating_Oil DOUBLE,
            Natural_Gas DOUBLE,
            Valero DOUBLE,
            Phillips66 DOUBLE
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS processed_spread_data (
            Date TIMESTAMP PRIMARY KEY,
            Crude_Oil DOUBLE,
            Gasoline DOUBLE,
            Heating_Oil DOUBLE,
            Natural_Gas DOUBLE,
            Valero DOUBLE,
            Phillips66 DOUBLE,
            Gasoline_bbl DOUBLE,
            Heating_Oil_bbl DOUBLE,
            Crack_Spread DOUBLE,
            Variable_OpEx DOUBLE,
            Total_OpEx DOUBLE,
            Net_Refining_Margin DOUBLE,
            Spread_30D_MA DOUBLE,
            Net_Margin_30D_MA DOUBLE
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS eia_reports (
            report_date TIMESTAMP PRIMARY KEY,
            url VARCHAR,
            raw_text VARCHAR,
            word_count INTEGER
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS eia_sentiment (
            report_date TIMESTAMP PRIMARY KEY,
            compound DOUBLE,
            positive DOUBLE,
            negative DOUBLE,
            neutral DOUBLE,
            net_keyword_score DOUBLE,
            dominant_topic INTEGER,
            topic_prob DOUBLE
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS sentiment_spread_merged (
            report_date TIMESTAMP PRIMARY KEY,
            compound DOUBLE,
            positive DOUBLE,
            negative DOUBLE,
            neutral DOUBLE,
            net_keyword_score DOUBLE,
            dominant_topic INTEGER,
            topic_prob DOUBLE,
            Date TIMESTAMP,
            Crack_Spread DOUBLE,
            Spread_30D_MA DOUBLE,
            Net_Refining_Margin DOUBLE
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS sentiment_spread_rolling_corr (
            date TIMESTAMP PRIMARY KEY,
            rolling_corr DOUBLE
        )
    """)
    con.close()

def get_existing_eia_dates():
    con = get_connection()
    try:
        df = con.execute("SELECT report_date FROM eia_reports").df()
        dates = pd.to_datetime(df['report_date']).dt.date.tolist() if not df.empty else []
    except duckdb.CatalogException:
        dates = []
    con.close()
    return dates

def get_existing_sentiment_dates():
    con = get_connection()
    try:
        df = con.execute("SELECT report_date FROM eia_sentiment").df()
        dates = pd.to_datetime(df['report_date']).dt.date.tolist() if not df.empty else []
    except duckdb.CatalogException:
        dates = []
    con.close()
    return dates

def read_eia_reports():
    con = get_connection()
    try:
        df = con.execute("SELECT * FROM eia_reports ORDER BY report_date").df()
        if not df.empty:
            df.set_index('report_date', inplace=True)
    except duckdb.CatalogException:
        df = pd.DataFrame()
    con.close()
    return df

def write_raw(df):
    con = get_connection()
    df_temp = df.copy()
    if df_temp.index.name != 'Date':
        df_temp.index.name = 'Date'
    df_temp = df_temp.reset_index()
    df_temp['Date'] = pd.to_datetime(df_temp['Date'])

    con.register('temp_df', df_temp)
    con.execute("DELETE FROM raw_market_data WHERE Date IN (SELECT Date FROM temp_df)")
    cols = ", ".join(df_temp.columns)
    con.execute(f"INSERT INTO raw_market_data ({cols}) SELECT {cols} FROM temp_df")
    con.close()

def write_processed(df):
    con = get_connection()
    df_temp = df.copy()
    if df_temp.index.name != 'Date':
        df_temp.index.name = 'Date'
    df_temp = df_temp.reset_index()
    df_temp['Date'] = pd.to_datetime(df_temp['Date'])

    con.register('temp_df', df_temp)
    con.execute("DELETE FROM processed_spread_data WHERE Date IN (SELECT Date FROM temp_df)")
    cols = ", ".join(df_temp.columns)
    con.execute(f"INSERT INTO processed_spread_data ({cols}) SELECT {cols} FROM temp_df")
    con.close()

def read_raw():
    con = get_connection()
    try:
        df = con.execute("SELECT * FROM raw_market_data ORDER BY Date").df()
        if not df.empty:
            df.set_index('Date', inplace=True)
    except duckdb.CatalogException:
        df = pd.DataFrame()
    con.close()
    return df

def read_processed():
    con = get_connection()
    try:
        df = con.execute("SELECT * FROM processed_spread_data ORDER BY Date").df()
        if not df.empty:
            df.set_index('Date', inplace=True)
    except duckdb.CatalogException:
        df = pd.DataFrame()
    con.close()
    return df

def write_eia_reports(df):
    if df.empty: return
    con = get_connection()
    df_temp = df.copy()
    if df_temp.index.name != 'report_date' and 'report_date' not in df_temp.columns:
        df_temp.index.name = 'report_date'
        df_temp = df_temp.reset_index()
    df_temp['report_date'] = pd.to_datetime(df_temp['report_date'])

    con.register('temp_df', df_temp)
    con.execute("DELETE FROM eia_reports WHERE report_date IN (SELECT report_date FROM temp_df)")
    cols = ", ".join(df_temp.columns)
    con.execute(f"INSERT INTO eia_reports ({cols}) SELECT {cols} FROM temp_df")
    con.close()

def write_eia_sentiment(df):
    if df.empty: return
    con = get_connection()
    df_temp = df.copy()
    if df_temp.index.name != 'report_date' and 'report_date' not in df_temp.columns:
        df_temp.index.name = 'report_date'
        df_temp = df_temp.reset_index()
    df_temp['report_date'] = pd.to_datetime(df_temp['report_date'])
    df_temp = df_temp.fillna(0.0)

    con.register('temp_df', df_temp)
    con.execute("DELETE FROM eia_sentiment WHERE report_date IN (SELECT report_date FROM temp_df)")
    cols = ", ".join(df_temp.columns)
    con.execute(f"INSERT INTO eia_sentiment ({cols}) SELECT {cols} FROM temp_df")
    con.close()

def write_sentiment_spread_merged(df):
    if df.empty: return
    con = get_connection()
    df_temp = df.copy()
    if df_temp.index.name != 'report_date' and 'report_date' not in df_temp.columns:
        df_temp.index.name = 'report_date'
        df_temp = df_temp.reset_index()
    df_temp['report_date'] = pd.to_datetime(df_temp['report_date'])

    con.register('temp_df', df_temp)
    con.execute("DELETE FROM sentiment_spread_merged WHERE report_date IN (SELECT report_date FROM temp_df)")
    cols = ", ".join(df_temp.columns)
    con.execute(f"INSERT INTO sentiment_spread_merged ({cols}) SELECT {cols} FROM temp_df")
    con.close()

def write_sentiment_spread_rolling_corr(df):
    if df.empty: return
    con = get_connection()
    df_temp = df.copy()
    if df_temp.index.name != 'date' and 'date' not in df_temp.columns:
        df_temp.index.name = 'date'
        df_temp = df_temp.reset_index()
    df_temp['date'] = pd.to_datetime(df_temp['date'])

    con.register('temp_df', df_temp)
    con.execute("DELETE FROM sentiment_spread_rolling_corr WHERE date IN (SELECT date FROM temp_df)")
    cols = ", ".join(df_temp.columns)
    con.execute(f"INSERT INTO sentiment_spread_rolling_corr ({cols}) SELECT {cols} FROM temp_df")
    con.close()

def get_eia_sentiment():
    con = get_connection()
    try:
        df = con.execute("SELECT * FROM eia_sentiment ORDER BY report_date").df()
        if not df.empty:
            df.set_index('report_date', inplace=True)
    except duckdb.CatalogException:
        df = pd.DataFrame()
    con.close()
    return df

def read_table(table_name):
    con = get_connection()
    try:
        df = con.execute(f"SELECT * FROM {table_name}").df()
    except duckdb.CatalogException:
        df = pd.DataFrame()
    con.close()
    return df

def migrate_from_csv():
    raw_path = os.path.join(PROJECT_ROOT, "data", "raw", "market_data.csv")
    processed_path = os.path.join(PROJECT_ROOT, "data", "processed", "spread_data.csv")

    if os.path.exists(raw_path):
        print(f"Migrating {raw_path} to DuckDB...")
        df = pd.read_csv(raw_path, index_col=0, parse_dates=True)
        write_raw(df)
        os.rename(raw_path, raw_path + ".bak")

    if os.path.exists(processed_path):
        print(f"Migrating {processed_path} to DuckDB...")
        df = pd.read_csv(processed_path, index_col=0, parse_dates=True)
        write_processed(df)
        os.rename(processed_path, processed_path + ".bak")

# Ensure tables are created when imported
init_db()
