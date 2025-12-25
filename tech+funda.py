import streamlit as st
import pandas as pd
from tradingview_screener import Query, Column as col
from typing import Optional
import io
import requests

# ==================================================
# PAGE CONFIG
# ==================================================
st.set_page_config(
    page_title="📈 Indian Technical Stock Screener",
    page_icon="📊",
    layout="wide"
)

st.title("📈 Indian Stock Technical Screener")
st.caption("RSI • EMA • Bollinger • Stochastic • ADX | NSE + BSE")

# ==================================================
# SIDEBAR – PRESETS
# ==================================================
PRESETS = {
    "None": None,
    "Top Gainers": "gainers",
    "Biggest Losers": "losers",
    "Most Active": "most_active",
    "Unusual Volume": "unusual_volume",
}

st.sidebar.header("📌 Preset Filters")
preset_label = st.sidebar.selectbox("Select Preset", PRESETS.keys())
preset_value = PRESETS[preset_label]

# ==================================================
# TECHNICAL FILTERS
# ==================================================
st.sidebar.header("📉 Momentum Filters")

min_rsi = st.sidebar.slider("RSI Min", 0, 100, 40)
max_rsi = st.sidebar.slider("RSI Max", 0, 100, 75)

st.sidebar.header("📊 Trend Filters")

adx_min = st.sidebar.slider("ADX Min (Trend Strength)", 0, 60, 20)

trend_direction = st.sidebar.selectbox(
    "Trend Direction",
    ["Any", "Bullish (+DI > -DI)", "Bearish (-DI > +DI)"]
)

st.sidebar.header("📐 EMA Filters")

ema20 = st.sidebar.checkbox("Price > EMA 20", True)
ema50 = st.sidebar.checkbox("Price > EMA 50", True)
ema200 = st.sidebar.checkbox("Price > EMA 200", False)

st.sidebar.header("📦 Bollinger Band Filters")

bb_condition = st.sidebar.selectbox(
    "Bollinger Condition",
    ["Any", "Near Lower Band", "Above Upper Band"]
)

st.sidebar.header("🎯 Stochastic Filters")

stoch_mode = st.sidebar.selectbox(
    "Stochastic Mode",
    ["Any", "Oversold (<20)", "Overbought (>80)", "Bullish (%K > %D)", "Bearish (%K < %D)"]
)

st.sidebar.header("🔊 Liquidity")

min_volume = st.sidebar.number_input("Min Volume", value=100000)

limit = st.sidebar.slider("Number of Stocks", 10, 200, 50)

run_scan = st.sidebar.button("🚀 Run Screener")

# ==================================================
# TECHNICAL SCAN FUNCTION
# ==================================================
def run_technical_scan(preset: Optional[str]) -> pd.DataFrame:
    try:
        q = (
            Query()
            .set_markets("india")
            .select(
                "name",
                "sector",
                "close",
                "change",
                "volume",
                "RSI",
                "EMA20",
                "EMA50",
                "EMA200",
                "BB.upper",
                "BB.lower",
                "Stoch.K",
                "Stoch.D",
                "ADX",
                "ADX+DI",
                "ADX-DI",
            )
            .where(
                col("type") == "stock",
                col("typespecs").has("common"),
                col("is_primary") == True,
                col("RSI") >= min_rsi,
                col("RSI") <= max_rsi,
                col("volume") >= min_volume,
                col("ADX") >= adx_min,
            )
            .limit(limit)
        )

        # EMA CONDITIONS
        if ema20:
            q = q.where(col("close") > col("EMA20"))
        if ema50:
            q = q.where(col("close") > col("EMA50"))
        if ema200:
            q = q.where(col("close") > col("EMA200"))

        # ADX DIRECTION
        if trend_direction == "Bullish (+DI > -DI)":
            q = q.where(col("ADX+DI") > col("ADX-DI"))
        elif trend_direction == "Bearish (-DI > +DI)":
            q = q.where(col("ADX-DI") > col("ADX+DI"))

        # BOLLINGER
        if bb_condition == "Near Lower Band":
            q = q.where(col("close") <= col("BB.lower") * 1.02)
        elif bb_condition == "Above Upper Band":
            q = q.where(col("close") > col("BB.upper"))

        # STOCHASTIC
        if stoch_mode == "Oversold (<20)":
            q = q.where(col("Stoch.K") < 20)
        elif stoch_mode == "Overbought (>80)":
            q = q.where(col("Stoch.K") > 80)
        elif stoch_mode == "Bullish (%K > %D)":
            q = q.where(col("Stoch.K") > col("Stoch.D"))
        elif stoch_mode == "Bearish (%K < %D)":
            q = q.where(col("Stoch.K") < col("Stoch.D"))

        if preset:
            q = q.set_property("preset", preset)

        _, df = q.get_scanner_data(timeout=30)
        return df

    except requests.exceptions.HTTPError:
        st.error("TradingView rejected the request. Reduce filters.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        return pd.DataFrame()

# ==================================================
# OUTPUT
# ==================================================
if run_scan:
    with st.spinner("Scanning Indian Markets..."):
        df = run_technical_scan(preset_value)

    if df.empty:
        st.warning("No stocks matched the criteria.")
    else:
        st.subheader(f"📋 Results ({len(df)} stocks)")

        st.dataframe(
            df.sort_values("ADX", ascending=False),
            use_container_width=True
        )

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Technical")

        st.download_button(
            "⬇️ Download Excel",
            output.getvalue(),
            "india_technical_screener.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# ==================================================
# FOOTER
# ==================================================
st.markdown("---")
st.markdown(
    """
**Designed by Gaurav**  
Price Action • Momentum • Trend Intelligence  
Built with ❤️ using TradingView
"""
)
