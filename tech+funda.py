# ============================================================
# INDIAN STOCK SCREENER – TECHNICAL | FUNDAMENTAL | HYBRID
# SINGLE FILE – PRODUCTION READY
# ============================================================

import streamlit as st
import pandas as pd
import talib
import yfinance as yf
from tradingview_screener import Query, Column as col
import io

# ============================================================
# STREAMLIT CONFIG
# ============================================================
st.set_page_config(
    page_title="Indian Stock Screener",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Indian Stock Screener")
st.caption("Technical • Fundamental • Hybrid | TradingView + Python")

# ============================================================
# MODE SELECTOR (STARTING DROPDOWN)
# ============================================================
st.sidebar.header("🧭 Screener Mode")

MODE = st.sidebar.selectbox(
    "Select Screener Type",
    ["Technical Screener", "Fundamental Screener", "Hybrid Screener"]
)

limit = st.sidebar.slider("Max Stocks", 20, 150, 60)

# ============================================================
# PRESETS (ONLY FOR HYBRID)
# ============================================================
PRESETS = {
    "Custom": {},
    "Swing": {
        "RSI": (45, 65),
        "ADX": 20,
        "ema": "EMA50",
    },
    "Positional": {
        "ADX": 25,
        "ema": "EMA200",
        "ROCE": 18,
        "DE": 0.6,
    },
    "Value": {
        "PE": 20,
        "DE": 0.6,
        "ROCE": 15,
    },
    "Quality": {
        "ROE": 18,
        "NM": 12,
        "FCF": 0,
    },
}

if MODE == "Hybrid Screener":
    preset = st.sidebar.selectbox("Preset", PRESETS.keys())
else:
    preset = "Custom"

# ============================================================
# FILTER SECTIONS (DYNAMIC)
# ============================================================

# ---------- TECHNICAL FILTERS ----------
if MODE in ["Technical Screener", "Hybrid Screener"]:
    st.sidebar.subheader("📈 Technical Filters")

    rsi_min, rsi_max = st.sidebar.slider("RSI Range", 0, 100, (40, 70))
    adx_min = st.sidebar.slider("ADX Min", 0, 60, 20)

    ema_filter = st.sidebar.selectbox(
        "Price Above EMA",
        ["None", "EMA20", "EMA50", "EMA200"]
    )

# ---------- FUNDAMENTAL FILTERS ----------
if MODE in ["Fundamental Screener", "Hybrid Screener"]:
    st.sidebar.subheader("📊 Fundamental Filters")

    pe_max = st.sidebar.number_input("Max PE", 0.0, 100.0, 30.0)
    roce_min = st.sidebar.number_input("Min ROCE (%)", 0.0, 50.0, 15.0)
    roe_min = st.sidebar.number_input("Min ROE (%)", 0.0, 50.0, 15.0)
    de_max = st.sidebar.number_input("Max Debt/Equity", 0.0, 5.0, 1.0)

# ============================================================
# TRADINGVIEW FIELD SET
# ============================================================
TV_FIELDS = [
    "name","sector","industry","close","volume",
    "market_cap_basic","price_earnings_ttm",
    "return_on_equity","return_on_invested_capital",
    "net_margin","free_cash_flow_ttm",
    "debt_to_equity",
    "EMA20","EMA50","EMA200",
    "RSI","ADX","BB.upper","BB.lower"
]

# ============================================================
# TRADINGVIEW QUERY ENGINE
# ============================================================
@st.cache_data(show_spinner=False)
def run_tv_scan():
    q = (
        Query()
        .set_markets("india")
        .select(*TV_FIELDS)
        .where(col("type") == "stock")
        .limit(limit)
    )

    # ---- TECHNICAL CONDITIONS ----
    if MODE in ["Technical Screener", "Hybrid Screener"]:
        q = q.where(
            col("RSI").between(rsi_min, rsi_max),
            col("ADX") >= adx_min,
        )
        if ema_filter != "None":
            q = q.where(col("close") > col(ema_filter))

    # ---- FUNDAMENTAL CONDITIONS ----
    if MODE in ["Fundamental Screener", "Hybrid Screener"]:
        q = q.where(
            col("price_earnings_ttm") <= pe_max,
            col("return_on_invested_capital") >= roce_min,
            col("return_on_equity") >= roe_min,
            col("debt_to_equity") <= de_max,
        )

    # ---- PRESET OVERRIDE (HYBRID) ----
    if MODE == "Hybrid Screener" and preset != "Custom":
        p = PRESETS[preset]
        if "RSI" in p:
            q = q.where(col("RSI").between(*p["RSI"]))
        if "ADX" in p:
            q = q.where(col("ADX") > p["ADX"])
        if "ema" in p:
            q = q.where(col("close") > col(p["ema"]))
        if "ROCE" in p:
            q = q.where(col("return_on_invested_capital") > p["ROCE"])
        if "DE" in p:
            q = q.where(col("debt_to_equity") < p["DE"])
        if "PE" in p:
            q = q.where(col("price_earnings_ttm") < p["PE"])
        if "ROE" in p:
            q = q.where(col("return_on_equity") > p["ROE"])
        if "NM" in p:
            q = q.where(col("net_margin") > p["NM"])
        if "FCF" in p:
            q = q.where(col("free_cash_flow_ttm") > p["FCF"])

    _, df = q.get_scanner_data(timeout=30)
    return df

# ============================================================
# LOCAL ENRICHMENT (ONLY FOR TECH / HYBRID)
# ============================================================
def enrich_local(df):
    rows = []
    for sym in df["name"].head(25):
        try:
            data = yf.download(sym + ".NS", period="6mo", progress=False)
            if data.empty:
                continue

            rsi = talib.RSI(data["Close"], 14).iloc[-1]
            atr = talib.ATR(data["High"], data["Low"], data["Close"], 14).iloc[-1]

            rows.append({
                "name": sym,
                "RSI_local": rsi,
                "ATR_local": atr,
            })
        except:
            pass

    if rows:
        df = df.merge(pd.DataFrame(rows), on="name", how="left")
    return df

# ============================================================
# RUN BUTTON
# ============================================================
if st.button("🚀 Run Screener"):
    with st.spinner("Running Screener..."):
        df = run_tv_scan()

    if df.empty:
        st.warning("No stocks matched the criteria.")
        st.stop()

    if MODE in ["Technical Screener", "Hybrid Screener"]:
        df = enrich_local(df)

    st.subheader(f"📋 Results ({len(df)} stocks)")
    st.dataframe(df, use_container_width=True)

    # EXPORT
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)

    st.download_button(
        "⬇️ Download Excel",
        output.getvalue(),
        "stock_screener.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.markdown(
    """
**Designed by Gaurav**  
Technical • Fundamental • Hybrid Intelligence  
Built with ❤️ using TradingView + Python
"""
)
