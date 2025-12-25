# ============================================================
# INDIAN STOCK SCREENER (CLOUD SAFE)
# TECHNICAL | FUNDAMENTAL | HYBRID
# NO pandas_ta | NO LOCAL INDICATORS
# RSI LOGIC FIXED | NO STOCK LIMITATION
# ============================================================

import streamlit as st
import pandas as pd
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
st.caption("Technical • Fundamental • Hybrid | TradingView (Cloud Safe)")

# ============================================================
# MODE SELECTOR
# ============================================================
st.sidebar.header("🧭 Screener Mode")

MODE = st.sidebar.selectbox(
    "Select Screener Type",
    ["Technical Screener", "Fundamental Screener", "Hybrid Screener"]
)

# TradingView safe upper bound
limit = st.sidebar.slider("Max Stocks (TradingView)", 50, 500, 200)

# ============================================================
# PRESETS (MODIFY DEFAULTS ONLY)
# ============================================================
PRESETS = {
    "Custom": {},
    "Swing": {"RSI": (45, 65), "ADX": 20, "EMA": "EMA50"},
    "Positional": {"ADX": 25, "EMA": "EMA200", "ROCE": 18, "DE": 0.6},
    "Value": {"PE": 20, "DE": 0.6, "ROCE": 15},
    "Quality": {"ROE": 18, "NM": 12},
}

if MODE == "Hybrid Screener":
    preset = st.sidebar.selectbox("Preset", PRESETS.keys())
else:
    preset = "Custom"

# ============================================================
# DEFAULT FILTER VALUES
# ============================================================
rsi_min, rsi_max = 40, 70
adx_min = 20
ema_filter = "None"

pe_max = 30.0
roce_min = 15.0
roe_min = 15.0
de_max = 1.0

# ============================================================
# APPLY PRESET → CHANGE DEFAULTS ONLY
# ============================================================
if MODE == "Hybrid Screener" and preset != "Custom":
    p = PRESETS[preset]
    rsi_min, rsi_max = p.get("RSI", (rsi_min, rsi_max))
    adx_min = p.get("ADX", adx_min)
    ema_filter = p.get("EMA", ema_filter)
    pe_max = p.get("PE", pe_max)
    roce_min = p.get("ROCE", roce_min)
    roe_min = p.get("ROE", roe_min)
    de_max = p.get("DE", de_max)

# ============================================================
# SIDEBAR FILTERS (SINGLE SOURCE OF TRUTH)
# ============================================================

if MODE in ["Technical Screener", "Hybrid Screener"]:
    st.sidebar.subheader("📈 Technical Filters")
    rsi_min, rsi_max = st.sidebar.slider("RSI Range", 0, 100, (rsi_min, rsi_max))
    adx_min = st.sidebar.slider("ADX Min", 0, 60, adx_min)
    ema_filter = st.sidebar.selectbox(
        "Price Above EMA",
        ["None", "EMA20", "EMA50", "EMA200"],
        index=["None", "EMA20", "EMA50", "EMA200"].index(ema_filter)
    )

if MODE in ["Fundamental Screener", "Hybrid Screener"]:
    st.sidebar.subheader("📊 Fundamental Filters")
    pe_max = st.sidebar.number_input("Max PE", 0.0, 200.0, pe_max)
    roce_min = st.sidebar.number_input("Min ROCE (%)", 0.0, 50.0, roce_min)
    roe_min = st.sidebar.number_input("Min ROE (%)", 0.0, 50.0, roe_min)
    de_max = st.sidebar.number_input("Max Debt / Equity", 0.0, 5.0, de_max)

# ============================================================
# TRADINGVIEW SAFE FIELDS (VERIFIED)
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
# TRADINGVIEW QUERY
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

    if MODE in ["Technical Screener", "Hybrid Screener"]:
        q = q.where(
            col("RSI") >= rsi_min,
            col("RSI") <= rsi_max,
            col("ADX") >= adx_min
        )
        if ema_filter != "None":
            q = q.where(col("close") > col(ema_filter))

    if MODE in ["Fundamental Screener", "Hybrid Screener"]:
        q = q.where(
            col("price_earnings_ttm") <= pe_max,
            col("return_on_invested_capital") >= roce_min,
            col("return_on_equity") >= roe_min,
            col("debt_to_equity") <= de_max
        )

    _, df = q.get_scanner_data(timeout=30)
    return df

# ============================================================
# RUN
# ============================================================
if st.button("🚀 Run Screener"):
    with st.spinner("Running TradingView Screener..."):
        df = run_tv_scan()

    if df.empty:
        st.warning("No stocks matched the criteria.")
        st.stop()

    # FINAL DEFENSIVE RSI FILTER (GUARANTEE)
    if MODE in ["Technical Screener", "Hybrid Screener"]:
        df = df[(df["RSI"] >= rsi_min) & (df["RSI"] <= rsi_max)]

    st.subheader(f"📋 Results ({len(df)} stocks)")
    st.dataframe(df, use_container_width=True)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)

    st.download_button(
        "⬇️ Download Excel",
        output.getvalue(),
        "indian_stock_screener.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.markdown(
    """
**Designed by Gaurav**  
Technical • Fundamental • Hybrid Market Intelligence  
Built with ❤️ using TradingView (Cloud Safe)
"""
)
