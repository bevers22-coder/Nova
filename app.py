
from html import escape
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf

# -----------------------------------------
# NOVA — MARKET INTELLIGENCE
# -----------------------------------------

st.set_page_config(
    page_title="Nova | Market Intelligence",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded"
)

voice_component = components.declare_component(
    "nova_voice",
    path=str(Path(__file__).parent / "voice_component")
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=Rajdhani:wght@500;600;700&display=swap');
:root {
    --nova-cyan: #08f5ef;
    --nova-blue: #12a9c5;
    --nova-muted: #75aeb8;
    --nova-line: rgba(8, 245, 239, .27);
    --nova-panel: rgba(3, 18, 27, .88);
}
.stApp {
    position: relative;
    isolation: isolate;
    background:
        radial-gradient(ellipse at 50% 38%, rgba(0, 164, 186, .14), transparent 46%),
        radial-gradient(ellipse at 90% 0%, rgba(0, 238, 231, .10), transparent 32%),
        linear-gradient(rgba(8, 245, 239, .035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(8, 245, 239, .035) 1px, transparent 1px),
        #02090e;
    background-size: auto, auto, 32px 32px, 32px 32px, auto;
    color: #c9faff;
    font-family: 'IBM Plex Mono', monospace;
}
.stApp [data-testid="stAppViewContainer"], .stApp > header {
    position: relative;
    z-index: 1;
}
.stApp::before, .stApp::after {
    position: fixed;
    inset: 0;
    z-index: 0;
    pointer-events: none;
    content: "";
}
.stApp::before {
    opacity: .36;
    background:
        radial-gradient(circle at 13% 24%, #08f5ef 0 1px, transparent 2px),
        radial-gradient(circle at 77% 63%, #08f5ef 0 1px, transparent 2px),
        radial-gradient(circle at 44% 82%, #12a9c5 0 1px, transparent 2px),
        linear-gradient(115deg, transparent 47%, rgba(8,245,239,.06) 48%, transparent 49%);
    background-size: 173px 151px, 211px 187px, 139px 197px, 100% 100%;
    animation: nova-drift 32s linear infinite;
}
.stApp::after {
    opacity: .28;
    background: repeating-linear-gradient(
        0deg, transparent 0 5px, rgba(8,245,239,.025) 6px, transparent 7px
    );
    animation: nova-scan 12s linear infinite;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #04141d, #02090e 78%);
    border-right: 1px solid var(--nova-line);
}
h1, h2, h3, h4 {
    color: #d8fdff !important;
    letter-spacing: .07em;
    font-family: 'Rajdhani', sans-serif !important;
    text-transform: uppercase;
    text-shadow: 0 0 18px rgba(8, 245, 239, .14);
}
[data-testid="stCaptionContainer"] {
    color: var(--nova-muted);
}
div[data-testid="stMetric"] {
    background: linear-gradient(145deg, rgba(5, 28, 38, .96), rgba(3, 14, 21, .96));
    border: 1px solid var(--nova-line);
    border-radius: 2px;
    padding: 14px 16px;
    box-shadow: inset 0 1px 0 rgba(150, 233, 245, .05), 0 0 16px rgba(8, 245, 239, .035);
}
[data-testid="stMetricLabel"] {
    color: #69aab7;
    text-transform: uppercase;
    letter-spacing: .13em;
    font-size: .68rem;
}
[data-testid="stMetricValue"] {
    color: var(--nova-cyan);
    font-family: 'Rajdhani', sans-serif;
}
.stButton button {
    background: linear-gradient(110deg, #063340, #092531);
    color: #e7fbff;
    border: 1px solid #0daeb7;
    border-radius: 1px;
    letter-spacing: .10em;
    font-family: 'IBM Plex Mono', monospace;
    box-shadow: inset 0 0 14px rgba(8, 245, 239, .04);
}
.stButton button:hover {
    background: #0a4b59;
    border-color: var(--nova-cyan);
    color: white;
    box-shadow: 0 0 18px rgba(8, 245, 239, .2);
}
[data-testid="stDataFrame"] {
    border: 1px solid var(--nova-line);
}
div[data-testid="stAlert"] {
    border-radius: 1px;
}
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input {
    background: #06141c;
    border-color: var(--nova-line);
    color: #dcfeff;
}
[data-testid="stSelectbox"] [data-baseweb="select"] > div {
    background: #06141c;
    border-color: var(--nova-line);
}
[data-testid="stTabs"] button {
    color: var(--nova-muted);
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: var(--nova-cyan);
    border-bottom-color: var(--nova-cyan);
}
[data-testid="stExpander"] {
    border-color: var(--nova-line);
    border-radius: 1px;
}
hr {
    border-color: rgba(8, 245, 239, .16);
}
.nova-eyebrow {
    color: var(--nova-cyan);
    font-size: .76rem;
    letter-spacing: .18em;
    text-transform: uppercase;
}
.nova-panel {
    border: 1px solid var(--nova-line);
    border-left: 3px solid var(--nova-cyan);
    padding: 18px 20px;
    background: linear-gradient(110deg, rgba(4, 33, 43, .92), rgba(3, 15, 23, .86));
    margin: 8px 0 22px;
    box-shadow: inset 0 0 32px rgba(8, 245, 239, .025);
}
.nova-hud-strip {
    color: var(--nova-cyan);
    font: 600 .72rem 'IBM Plex Mono', monospace;
    letter-spacing: .11em;
    padding: 7px 10px;
    border-top: 1px solid var(--nova-line);
    border-bottom: 1px solid var(--nova-line);
    background: rgba(4, 28, 38, .55);
}
.nova-time {
    color: var(--nova-cyan);
    font: 700 2.2rem 'Rajdhani', sans-serif;
    line-height: 1.05;
}
.nova-weather-temp {
    color: #e1feff;
    font: 700 2rem 'Rajdhani', sans-serif;
}
.nova-orbit-wrap {
    display: grid;
    place-items: center;
    min-height: 250px;
    overflow: hidden;
    border: 1px solid var(--nova-line);
    background: radial-gradient(circle, rgba(8, 245, 239, .10), rgba(3, 14, 21, .5) 52%, transparent 72%);
}
.nova-reactor {
    position: relative;
    display: grid;
    place-items: center;
    width: 220px;
    height: 220px;
    border: 1px solid rgba(8,245,239,.55);
    border-radius: 50%;
    background: repeating-conic-gradient(from 4deg, rgba(8,245,239,.72) 0 1deg, transparent 1deg 12deg);
    box-shadow: 0 0 30px rgba(8,245,239,.18), inset 0 0 25px rgba(8,245,239,.1);
    animation: nova-spin 36s linear infinite;
}
.nova-reactor::before, .nova-reactor::after {
    position: absolute;
    content: "";
    border: 1px solid rgba(8,245,239,.55);
    border-radius: 50%;
}
.nova-reactor::before {
    inset: 15px;
    border-style: dashed;
    animation: nova-spin 22s linear infinite reverse;
}
.nova-reactor::after {
    inset: 38px;
    border-width: 3px;
    box-shadow: 0 0 24px rgba(8,245,239,.28), inset 0 0 20px rgba(8,245,239,.16);
}
.nova-reactor-core {
    z-index: 1;
    display: grid;
    place-items: center;
    width: 92px;
    height: 92px;
    border: 1px solid var(--nova-cyan);
    border-radius: 50%;
    color: #d8fdff;
    background: radial-gradient(circle, rgba(8,245,239,.5), rgba(3,17,26,.95) 72%);
    font: 700 1rem 'Rajdhani', sans-serif;
    letter-spacing: .14em;
    text-shadow: 0 0 14px var(--nova-cyan);
    animation: nova-pulse 3s ease-in-out infinite;
}
.nova-reactor-label {
    position: absolute;
    color: var(--nova-cyan);
    font: 600 .58rem 'IBM Plex Mono', monospace;
    letter-spacing: .12em;
    animation: nova-counter-spin 36s linear infinite;
}
.nova-reactor-label.top { top: 8px; }
.nova-reactor-label.bottom { bottom: 8px; }
.nova-node {
    min-height: 120px;
    padding: 16px;
    border-left: 2px solid var(--nova-cyan);
    background: linear-gradient(90deg, rgba(4, 33, 43, .8), transparent);
    color: #b6e5e9;
    font-size: .78rem;
    line-height: 1.8;
}
.nova-node strong {
    color: var(--nova-cyan);
    font-size: .68rem;
    letter-spacing: .12em;
}
.nova-terminal-bar {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    padding: 8px 12px;
    border: 1px solid var(--nova-line);
    border-bottom: 0;
    color: var(--nova-muted);
    background: rgba(3, 18, 27, .72);
    font-size: .68rem;
    letter-spacing: .12em;
    text-transform: uppercase;
}
.nova-terminal-bar strong {
    color: var(--nova-cyan);
    font-weight: 600;
}
.nova-console-panel {
    min-height: 250px;
    padding: 16px;
    border: 1px solid var(--nova-line);
    background: linear-gradient(150deg, rgba(4, 25, 34, .94), rgba(2, 11, 17, .92));
    box-shadow: inset 0 0 24px rgba(8, 245, 239, .025);
}
.nova-console-title {
    margin-bottom: 14px;
    color: var(--nova-cyan);
    font-size: .7rem;
    letter-spacing: .14em;
    text-transform: uppercase;
}
.nova-console-row {
    display: flex;
    justify-content: space-between;
    gap: 10px;
    padding: 9px 0;
    border-top: 1px solid rgba(8, 245, 239, .12);
    color: #a7d8de;
    font-size: .72rem;
}
.nova-console-row strong {
    color: #d8fdff;
    font-weight: 500;
    text-align: right;
}
.nova-console-note {
    margin-top: 12px;
    color: var(--nova-muted);
    font-size: .66rem;
    line-height: 1.7;
}
.nova-watchlist {
    min-height: 54px;
    padding: 10px 0;
    border-top: 1px solid rgba(8, 245, 239, .12);
    color: #d8fdff;
    font-size: .72rem;
    line-height: 1.8;
    overflow-wrap: anywhere;
}
.nova-orbit-wrap {
    min-height: 250px;
}
@media (max-width: 760px) {
    .nova-console-panel {
        min-height: 0;
    }
    .nova-terminal-bar {
        flex-wrap: wrap;
    }
    .nova-reactor {
        width: 190px;
        height: 190px;
    }
}
@keyframes nova-spin {
    to { transform: rotate(360deg); }
}
@keyframes nova-counter-spin {
    to { transform: rotate(-360deg); }
}
@keyframes nova-drift {
    to { background-position: 173px 151px, -211px -187px, 139px -197px, 0 0; }
}
@keyframes nova-scan {
    to { background-position-y: 100vh; }
}
@keyframes nova-pulse {
    50% { box-shadow: 0 0 30px rgba(8,245,239,.58), inset 0 0 22px rgba(8,245,239,.28); }
}
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: .01ms !important;
        animation-iteration-count: 1 !important;
    }
}
.nova-small {
    color: var(--nova-muted);
    font-size: .72rem;
    letter-spacing: .06em;
    text-transform: uppercase;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------
# DATA FUNCTIONS
# -----------------------------------------

@st.cache_data(ttl=300)
def get_stock_data(ticker, period="5y"):
    data = yf.download(
        ticker,
        period=period,
        auto_adjust=True,
        progress=False
    )

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    if data.empty or "Close" not in data.columns:
        return pd.DataFrame()

    data["Returns"] = data["Close"].pct_change()
    data["SMA20"] = data["Close"].rolling(20).mean()
    data["SMA50"] = data["Close"].rolling(50).mean()
    data["SMA200"] = data["Close"].rolling(200).mean()
    data["EMA20"] = data["Close"].ewm(span=20, adjust=False).mean()
    data["EMA50"] = data["Close"].ewm(span=50, adjust=False).mean()
    data["BB_Middle"] = data["Close"].rolling(20).mean()
    data["BB_Std"] = data["Close"].rolling(20).std()
    data["BB_Upper"] = data["BB_Middle"] + 2 * data["BB_Std"]
    data["BB_Lower"] = data["BB_Middle"] - 2 * data["BB_Std"]
    data["MACD"] = data["Close"].ewm(span=12, adjust=False).mean() - data["Close"].ewm(span=26, adjust=False).mean()
    data["MACD_Signal"] = data["MACD"].ewm(span=9, adjust=False).mean()
    data["MACD_Histogram"] = data["MACD"] - data["MACD_Signal"]
    data["Volatility"] = data["Returns"].rolling(20).std() * np.sqrt(252)
    delta = data["Close"].diff()
    average_gain = delta.clip(lower=0).rolling(14).mean()
    average_loss = -delta.clip(upper=0).rolling(14).mean()
    relative_strength = average_gain / average_loss.replace(0, np.nan)
    data["RSI14"] = 100 - (100 / (1 + relative_strength))
    data.loc[(average_loss == 0) & (average_gain > 0), "RSI14"] = 100
    data.loc[(average_loss == 0) & (average_gain == 0), "RSI14"] = 50
    data["AverageVolume20"] = data["Volume"].rolling(20).mean()

    return data.dropna(subset=["Close"])


def discover_stock(query):
    try:
        results = yf.Search(query, max_results=8).quotes or []
        equities = [
            x for x in results
            if x.get("quoteType") in ["EQUITY", "ETF"]
            and x.get("symbol")
        ]

        if not equities:
            return None

        exact = [
            x for x in equities
            if x.get("symbol", "").upper() == query.upper()
        ]

        return exact[0] if exact else equities[0]

    except Exception:
        return None


def calculate_metrics(data):
    prices = data["Close"].dropna()
    returns = prices.pct_change().dropna()

    if len(prices) < 2:
        return {}

    years = len(returns) / 252
    total_return = (prices.iloc[-1] / prices.iloc[0] - 1) * 100

    cagr = (
        ((prices.iloc[-1] / prices.iloc[0]) ** (1 / years) - 1) * 100
        if years > 0 else 0
    )

    volatility = returns.std() * np.sqrt(252) * 100
    sharpe = (
        returns.mean() / returns.std() * np.sqrt(252)
        if returns.std() else 0
    )
    downside_deviation = np.sqrt(np.square(returns.clip(upper=0)).mean())
    sortino = (
        returns.mean() / downside_deviation * np.sqrt(252)
        if downside_deviation else 0
    )

    drawdown = (
        (prices / prices.cummax() - 1).min() * 100
    )

    one_month_return = (
        (prices.iloc[-1] / prices.iloc[-22] - 1) * 100
        if len(prices) >= 22 else np.nan
    )
    year_prices = prices.tail(252)
    year_high = float(year_prices.max())
    year_low = float(year_prices.min())
    latest = float(prices.iloc[-1])

    return {
        "Latest Price": latest,
        "Daily Change": float(returns.iloc[-1] * 100) if len(returns) else 0,
        "1M Return": float(one_month_return),
        "RSI (14)": float(data["RSI14"].iloc[-1]),
        "52W High": year_high,
        "52W Low": year_low,
        "From 52W High": float((latest / year_high - 1) * 100),
        "Average Volume (20D)": float(data["AverageVolume20"].iloc[-1]),
        "Total Return": float(total_return),
        "CAGR": float(cagr),
        "Volatility": float(volatility),
        "Sharpe": float(sharpe),
        "Sortino": float(sortino),
        "Max Drawdown": float(drawdown)
    }


def price_chart(data, ticker):
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=data.index,
        y=data["BB_Upper"],
        name="Bollinger upper",
        line=dict(color="rgba(8,245,239,.28)", width=1, dash="dot"),
        hovertemplate="%{x|%b %d, %Y}<br>Upper band: $%{y:,.2f}<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data["BB_Lower"],
        name="Bollinger lower",
        line=dict(color="rgba(8,245,239,.28)", width=1, dash="dot"),
        fill="tonexty",
        fillcolor="rgba(8,245,239,.035)",
        hovertemplate="%{x|%b %d, %Y}<br>Lower band: $%{y:,.2f}<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data["Close"],
        name="Price",
        line=dict(color="#08f5ef", width=2),
        hovertemplate="%{x|%b %d, %Y}<br>Close: $%{y:,.2f}<extra></extra>"
    ))

    for column, color in [
        ("EMA20", "#f4bb55"),
        ("SMA50", "#58a7ff"),
        ("SMA200", "#ff6489")
    ]:
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data[column],
            name=column,
            line=dict(color=color, width=1.2),
            hovertemplate=f"%{{x|%b %d, %Y}}<br>{column}: $%{{y:,.2f}}<extra></extra>"
        ))

    fig.update_layout(
        title=f"{ticker} // PRICE, TREND & VOLATILITY BANDS",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#04121a",
        height=480,
        hovermode="x unified",
        margin=dict(l=55, r=25, t=70, b=45),
        legend=dict(orientation="h", y=1.12, font=dict(size=10)),
        font=dict(family="IBM Plex Mono, monospace", color="#a6d7dc", size=10),
        xaxis=dict(title="SESSION DATE", showgrid=True, gridcolor="rgba(8,245,239,.09)", tickformat="%b %y"),
        yaxis=dict(title="PRICE (USD)", showgrid=True, gridcolor="rgba(8,245,239,.09)", tickprefix="$", tickformat=",.2f", separatethousands=True)
    )

    return fig


def volume_chart(data, ticker):
    fig = go.Figure(go.Bar(
        x=data.index,
        y=data["Volume"],
        name="Volume",
        marker_color="#0daeb7",
        opacity=0.8
    ))
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data["AverageVolume20"],
        name="20D average",
        line=dict(color="#f4bb55", width=1.5)
    ))
    fig.update_layout(
        title=f"{ticker} // DAILY VOLUME",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#04121a",
        height=300,
        margin=dict(l=60, r=25, t=65, b=45),
        hovermode="x unified",
        font=dict(family="IBM Plex Mono, monospace", color="#a6d7dc", size=10),
        xaxis=dict(title="SESSION DATE", showgrid=True, gridcolor="rgba(8,245,239,.09)", tickformat="%b %y"),
        yaxis=dict(title="SHARES", showgrid=True, gridcolor="rgba(8,245,239,.09)", tickformat=",.3s")
    )
    return fig


def momentum_chart(data, ticker):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data.index, y=data["RSI14"], name="RSI (14)",
        line=dict(color="#08f5ef", width=1.7),
        hovertemplate="%{x|%b %d, %Y}<br>RSI: %{y:.2f}<extra></extra>"
    ))
    fig.add_hline(y=70, line_dash="dot", line_color="#ff6489", annotation_text="70")
    fig.add_hline(y=30, line_dash="dot", line_color="#f4bb55", annotation_text="30")
    fig.add_trace(go.Scatter(
        x=data.index, y=data["MACD"], name="MACD",
        line=dict(color="#58a7ff", width=1.4), yaxis="y2",
        hovertemplate="%{x|%b %d, %Y}<br>MACD: %{y:.4f}<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=data.index, y=data["MACD_Signal"], name="Signal",
        line=dict(color="#f4bb55", width=1.2, dash="dash"), yaxis="y2",
        hovertemplate="%{x|%b %d, %Y}<br>Signal: %{y:.4f}<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        x=data.index, y=data["MACD_Histogram"], name="MACD histogram",
        marker_color="#12889a", opacity=.55, yaxis="y2",
        hovertemplate="%{x|%b %d, %Y}<br>Histogram: %{y:.4f}<extra></extra>"
    ))
    fig.update_layout(
        title=f"{ticker} // MOMENTUM: RSI & MACD",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#04121a",
        height=370,
        margin=dict(l=60, r=60, t=65, b=45),
        hovermode="x unified",
        font=dict(family="IBM Plex Mono, monospace", color="#a6d7dc", size=10),
        legend=dict(orientation="h", y=1.12, font=dict(size=10)),
        xaxis=dict(title="SESSION DATE", showgrid=True, gridcolor="rgba(8,245,239,.09)", tickformat="%b %y"),
        yaxis=dict(title="RSI (0–100)", range=[0, 100], showgrid=True, gridcolor="rgba(8,245,239,.09)", tickformat=".0f"),
        yaxis2=dict(title="MACD", overlaying="y", side="right", showgrid=False, tickformat=".3f")
    )
    return fig


def screen_ticker(ticker, benchmark_returns=None):
    data = get_stock_data(ticker, "1y")
    if data.empty or len(data) < 22:
        return None

    metrics = calculate_metrics(data)
    latest = data.iloc[-1]
    close = data["Close"]
    true_range = pd.concat(
        [
            data["High"] - data["Low"],
            (data["High"] - data["Close"].shift()).abs(),
            (data["Low"] - data["Close"].shift()).abs()
        ],
        axis=1
    ).max(axis=1)
    average_true_range = true_range.rolling(14).mean().iloc[-1]
    paired_returns = None
    if benchmark_returns is not None:
        paired_returns = pd.concat(
            [data["Returns"].rename("asset"), benchmark_returns.rename("benchmark")],
            axis=1
        ).dropna()
    benchmark_variance = (
        paired_returns["benchmark"].var()
        if paired_returns is not None and len(paired_returns) > 1
        else 0
    )
    beta = (
        float(paired_returns["asset"].cov(paired_returns["benchmark"]) / benchmark_variance)
        if benchmark_variance > 0 else np.nan
    )
    return {
        "Ticker": ticker,
        "Price ($)": metrics["Latest Price"],
        "Day (%)": metrics["Daily Change"],
        "1M (%)": metrics["1M Return"],
        "3M (%)": float((close.iloc[-1] / close.iloc[-64] - 1) * 100) if len(close) >= 64 else np.nan,
        "6M (%)": float((close.iloc[-1] / close.iloc[-127] - 1) * 100) if len(close) >= 127 else np.nan,
        "1Y (%)": metrics["Total Return"],
        "RSI (14)": metrics["RSI (14)"],
        "Volatility (%)": metrics["Volatility"],
        "Avg Volume (20D)": metrics["Average Volume (20D)"],
        "Avg $ Volume (20D)": float((data["Close"] * data["Volume"]).rolling(20).mean().iloc[-1]),
        "Rel. Volume": (
            float(latest["Volume"] / latest["AverageVolume20"])
            if latest["AverageVolume20"] > 0 else np.nan
        ),
        "From 52W High (%)": metrics["From 52W High"],
        "From 52W Low (%)": float((metrics["Latest Price"] / float(close.tail(252).min()) - 1) * 100),
        "ATR (14) (%)": float(average_true_range / metrics["Latest Price"] * 100),
        "Max Drawdown (%)": metrics["Max Drawdown"],
        "Beta vs SPY": beta,
        "Price vs SMA20 (%)": float((latest["Close"] / latest["SMA20"] - 1) * 100),
        "Price vs SMA50 (%)": float((latest["Close"] / latest["SMA50"] - 1) * 100),
        "Price vs SMA200 (%)": float((latest["Close"] / latest["SMA200"] - 1) * 100),
        "MACD Bullish": bool(latest["MACD"] > latest["MACD_Signal"]),
        "Above SMA20": bool(latest["Close"] > latest["SMA20"]),
        "Above SMA50": bool(latest["Close"] > latest["SMA50"]),
        "Above SMA200": bool(latest["Close"] > latest["SMA200"])
    }


@st.cache_data(ttl=900, show_spinner=False)
def get_naperville_weather():
    url = (
        "https://api.open-meteo.com/v1/forecast?"
        "latitude=41.7508&longitude=-88.1535"
        "&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
        "precipitation,weather_code,wind_speed_10m"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset"
        "&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch"
        "&timezone=America%2FChicago&forecast_days=5"
    )
    with urlopen(url, timeout=3) as response:
        return json.loads(response.read().decode("utf-8"))


def describe_weather_code(code):
    descriptions = {
        0: "Clear sky", 1: "Mostly clear", 2: "Partly cloudy",
        3: "Overcast", 45: "Fog", 48: "Rime fog",
        51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
        56: "Freezing drizzle", 57: "Freezing drizzle",
        61: "Light rain", 63: "Rain", 65: "Heavy rain",
        66: "Freezing rain", 67: "Freezing rain",
        71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains",
        80: "Rain showers", 81: "Rain showers", 82: "Heavy showers",
        85: "Snow showers", 86: "Heavy snow showers",
        95: "Thunderstorm", 96: "Thunderstorm / hail", 99: "Thunderstorm / hail"
    }
    return descriptions.get(int(code), "Conditions unavailable")


@st.cache_data(ttl=900, show_spinner=False)
def get_news(feed_url, limit=8):
    request = Request(feed_url, headers={"User-Agent": "NovaMarketIntelligence/1.0"})
    with urlopen(request, timeout=3) as response:
        root = ET.fromstring(response.read())

    stories = []
    for item in root.findall(".//item")[:limit]:
        title = item.findtext("title", default="").strip()
        link = item.findtext("link", default="").strip()
        if title and link.startswith(("https://", "http://")):
            stories.append({
                "Headline": title,
                "Publisher": item.findtext("source", default="News feed").strip(),
                "Published": item.findtext("pubDate", default="").strip(),
                "Link": link
            })
    return stories


def render_news_feed(title, feed_url):
    st.markdown(f'<div class="nova-small">{title}</div>', unsafe_allow_html=True)
    try:
        with st.spinner("CONNECTING TO NEWS FEED..."):
            stories = get_news(feed_url)
    except (OSError, TimeoutError, ValueError, ET.ParseError) as error:
        st.warning(f"{title} is temporarily unavailable ({error}).")
        return

    if not stories:
        st.info("No headlines are available from this feed right now.")
        return

    st.dataframe(
        pd.DataFrame(stories),
        use_container_width=True,
        hide_index=True,
        height=min(360, 42 + len(stories) * 38),
        column_config={
            "Link": st.column_config.LinkColumn("Article", display_text="Open")
        }
    )


def render_market_news():
    market_feed = (
        "https://news.google.com/rss/search?q="
        f"{quote('stock market stocks earnings finance')}"
        "&hl=en-US&gl=US&ceid=US:en"
    )
    local_feed = (
        "https://news.google.com/rss/search?q="
        f"{quote('Naperville OR Chicago Illinois local business news')}"
        "&hl=en-US&gl=US&ceid=US:en"
    )
    market_col, local_col = st.columns(2)
    with market_col:
        render_news_feed("MARKET & STOCK NEWS", market_feed)
    with local_col:
        render_news_feed("NAPERVILLE / CHICAGO AREA", local_feed)


@st.fragment(run_every="60s")
def render_naperville_context():
    local_now = datetime.now(ZoneInfo("America/Chicago"))
    weather_col, clock_col = st.columns([1.5, 1])
    with clock_col:
        st.markdown(
            '<div class="nova-small">LOCAL SYSTEM TIME // NAPERVILLE, IL</div>'
            f'<div class="nova-time">{local_now.strftime("%I:%M:%S %p")}</div>'
            f'<div class="nova-small">{local_now.strftime("%A • %B %d, %Y")} / {local_now.tzname()}</div>',
            unsafe_allow_html=True
        )
    with weather_col:
        st.markdown(
            '<div class="nova-small">LIVE CONDITIONS // NAPERVILLE, ILLINOIS</div>',
            unsafe_allow_html=True
        )
        if st.button("LOAD LOCAL WEATHER", key="load_naperville_weather"):
            try:
                with st.spinner("CONNECTING TO WEATHER FEED..."):
                    weather = get_naperville_weather()
                current = weather["current"]
                st.markdown(
                    f'<span class="nova-weather-temp">{current["temperature_2m"]:.0f}°F</span>'
                    f' &nbsp; {describe_weather_code(current["weather_code"])}',
                    unsafe_allow_html=True
                )
                metrics = st.columns(4)
                metrics[0].markdown(
                    f'<div class="nova-small">FEELS LIKE</div>{current["apparent_temperature"]:.0f}°F',
                    unsafe_allow_html=True
                )
                metrics[1].markdown(
                    f'<div class="nova-small">HUMIDITY</div>{current["relative_humidity_2m"]:.0f}%',
                    unsafe_allow_html=True
                )
                metrics[2].markdown(
                    f'<div class="nova-small">WIND</div>{current["wind_speed_10m"]:.0f} mph',
                    unsafe_allow_html=True
                )
                forecast = weather["daily"]
                forecast_text = "  //  ".join(
                    f'{datetime.fromisoformat(day).strftime("%a")} '
                    f'{forecast["temperature_2m_min"][index]:.0f}°/'
                    f'{forecast["temperature_2m_max"][index]:.0f}° '
                    f'{describe_weather_code(forecast["weather_code"][index])}'
                    for index, day in enumerate(forecast["time"])
                )
                metrics[3].markdown(
                    f'<div class="nova-small">PRECIP.</div>{current["precipitation"]:.2f} in',
                    unsafe_allow_html=True
                )
                st.markdown(
                    f'<div class="nova-small">5-DAY OUTLOOK &nbsp; {forecast_text}</div>',
                    unsafe_allow_html=True
                )
            except (OSError, TimeoutError, ValueError, KeyError) as error:
                st.warning(
                    f"Naperville weather is temporarily unavailable ({error}). "
                    "The local clock remains active."
                )
        else:
            st.caption("Weather loads on request; the local clock is active.")


# -----------------------------------------
# PORTFOLIO CONFIGURATION
# -----------------------------------------

if "portfolio" not in st.session_state:
    st.session_state.portfolio = {
        "NVDA": 1,
        "ORCL": 5,
        "PLTR": 1,
        "MRVL": 2,
        "FTNT": 1,
        "ABBV": 1,
        "MP": 1,
        "PG": 12
    }

if "radar" not in st.session_state:
    st.session_state.radar = []

if "asset_command" not in st.session_state:
    st.session_state.asset_command = ""

with st.sidebar:
    st.markdown("## ✦ NOVA")
    st.caption("MARKET INTELLIGENCE SYSTEM")
    st.markdown("**VOICE CONTROL**")
    voice_result = voice_component(
        key="nova_voice_control",
        default={"status": "idle", "transcript": ""}
    )
    st.caption("Tap the mic to speak a ticker or navigate by page name.")
if not isinstance(voice_result, dict):
    voice_result = {"status": "idle", "transcript": ""}
transcript = voice_result.get("transcript", "")
voice_notice = ""
if transcript and transcript != st.session_state.get("last_voice_transcript"):
    st.session_state.last_voice_transcript = transcript
    command = " ".join(transcript.strip().lower().split())
    destinations = {
        "command center": "Command Center",
        "home": "Command Center",
        "go home": "Command Center",
        "dashboard": "Command Center",
        "stock intelligence": "Stock Intelligence",
        "stock analysis": "Stock Intelligence",
        "market screener": "Market Screener",
        "screener": "Market Screener",
        "galaxy radar": "Galaxy Radar",
        "radar": "Galaxy Radar",
        "portfolio": "Portfolio Analytics",
        "portfolio analytics": "Portfolio Analytics",
        "strategy research": "Strategy Research",
        "strategy lab": "Strategy Research",
        "system information": "System Information"
    }
    destination = next(
        (
            page_name
            for phrase, page_name in destinations.items()
            if command in {
                phrase,
                f"open {phrase}",
                f"go to {phrase}",
                f"show {phrase}",
                f"navigate to {phrase}"
            }
        ),
        None
    )
    if destination:
        st.session_state.active_page = destination
        voice_notice = f"Voice command opened {destination}."
    else:
        st.session_state.active_page = "Command Center"
        st.session_state.asset_command = transcript
        voice_notice = f"Voice input captured: “{transcript}”"

# -----------------------------------------
# SIDEBAR NAVIGATION
# -----------------------------------------

if voice_result.get("status") == "error":
    st.sidebar.warning(
        "Voice recognition could not start. Check microphone permission and "
        f"browser support. ({voice_result.get('message', 'unknown error')})"
    )
elif voice_notice:
    st.sidebar.caption(voice_notice)
st.sidebar.divider()

page = st.sidebar.radio(
    "SYSTEMS",
    [
        "Command Center",
        "Stock Intelligence",
        "Market Screener",
        "Galaxy Radar",
        "Portfolio Analytics",
        "Strategy Research",
        "System Information"
    ],
    key="active_page"
)

st.sidebar.divider()
st.sidebar.caption("DATA CONNECTION")
st.sidebar.success("Market data provider available")
st.sidebar.caption("Historical data may be delayed.")
st.sidebar.caption("Research simulation only.")

# -----------------------------------------
# COMMAND CENTER
# -----------------------------------------

if page == "Command Center":

    st.markdown('<p class="nova-eyebrow">NOVA // MARKET INTELLIGENCE SYSTEM</p>', unsafe_allow_html=True)
    st.title("NOVA / Command Center")
    local_now = datetime.now(ZoneInfo("America/Chicago"))
    st.markdown(
        '<div class="nova-terminal-bar">'
        '<span>TERMINAL / MARKET RESEARCH</span>'
        f'<span><strong>{local_now.strftime("%A / %b %d, %Y")}</strong>'
        f' &nbsp; // &nbsp; {local_now.strftime("%I:%M %p %Z")}</span>'
        '</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="nova-hud-strip">SYSTEM ONLINE &nbsp; / &nbsp; '
        'MARKET DATA LINK &nbsp; / &nbsp; RESEARCH MODE &nbsp; / &nbsp; '
        'NO TRADE EXECUTION</div>',
        unsafe_allow_html=True
    )
    st.markdown('<div class="nova-panel"><strong>MARKET RESEARCH CONSOLE</strong><br>'
                'Discover an asset, inspect its signals, or scan a custom universe.</div>',
                unsafe_allow_html=True)

    render_naperville_context()

    st.markdown("### SYSTEM STATUS")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Research Modules", "7")
    col2.metric("Portfolio Assets", len(st.session_state.portfolio))
    col3.metric("Radar Assets", len(st.session_state.radar))
    col4.metric("System Mode", "Research")

    portfolio_symbols = ", ".join(
        escape(symbol) for symbol in st.session_state.portfolio
    ) or "No holdings configured"
    radar_symbols = ", ".join(
        escape(symbol) for symbol in st.session_state.radar
    ) or "Radar is waiting for assets"
    left_panel, reactor_panel, right_panel = st.columns([1, 1.2, 1])
    with left_panel:
        st.markdown(
            '<div class="nova-console-panel">'
            '<div class="nova-console-title">Signal channels / 01</div>'
            '<div class="nova-console-row"><span>PRICE HISTORY</span><strong>ON DEMAND</strong></div>'
            '<div class="nova-console-row"><span>MARKET SCREENER</span><strong>READY</strong></div>'
            '<div class="nova-console-row"><span>HEADLINE FEEDS</span><strong>RSS</strong></div>'
            '<div class="nova-console-row"><span>VOICE LINK</span><strong>CLICK TO START</strong></div>'
            '<div class="nova-console-note">Research tools only. Data availability '
            'depends on the external providers.</div>'
            '</div>',
            unsafe_allow_html=True
        )
    with reactor_panel:
        st.markdown(
            '<div class="nova-orbit-wrap"><div class="nova-reactor">'
            '<div class="nova-reactor-label top">NOVA / COMMAND DECK</div>'
            '<div class="nova-reactor-core">NOVA</div>'
            '<div class="nova-reactor-label bottom">MARKET // RESEARCH</div>'
            '</div></div>',
            unsafe_allow_html=True
        )
    with right_panel:
        st.markdown(
            '<div class="nova-console-panel">'
            '<div class="nova-console-title">Active watch / 02</div>'
            f'<div class="nova-console-row"><span>PORTFOLIO</span>'
            f'<strong>{len(st.session_state.portfolio):02d} ASSETS</strong></div>'
            f'<div class="nova-watchlist">{portfolio_symbols}</div>'
            f'<div class="nova-console-row"><span>GALAXY RADAR</span>'
            f'<strong>{len(st.session_state.radar):02d} SIGNALS</strong></div>'
            f'<div class="nova-watchlist">{radar_symbols}</div>'
            '</div>',
            unsafe_allow_html=True
        )

    st.divider()

    st.subheader("Voice / Asset Discovery")
    st.caption(
        "Use the voice control in the sidebar for ticker lookup or say a page "
        "name such as “market screener” to navigate. Microphone starts only "
        "after your click and requires browser permission."
    )
    if voice_notice:
        st.info(voice_notice)
    command = st.text_input(
        "Enter a company name or ticker",
        placeholder="Example: NVIDIA, AAPL, Microsoft...",
        key="asset_command"
    )

    if st.button("RESOLVE ASSET", use_container_width=True):
        if command:
            match = discover_stock(command)

            if match:
                st.session_state.selected_ticker = match["symbol"]
                st.session_state.selected_name = (
                    match.get("longname")
                    or match.get("shortname")
                    or match["symbol"]
                )
                st.success(
                    f"Resolved: {st.session_state.selected_name} "
                    f"({match['symbol']})"
                )
                st.info("Open Stock Intelligence to inspect the asset.")
            else:
                st.error("No matching listed stock or ETF was found.")

    st.divider()

    st.subheader("Portfolio Watchlist")

    portfolio_table = pd.DataFrame([
        {"Ticker": ticker, "Shares": shares}
        for ticker, shares in st.session_state.portfolio.items()
    ])

    st.dataframe(portfolio_table, use_container_width=True, hide_index=True)
    st.divider()
    st.subheader("Live Intelligence Feeds")
    if st.button("LOAD LIVE NEWS", key="load_market_news"):
        render_market_news()
    else:
        st.caption("Live news feeds load when requested.")
    st.markdown(
        '<div class="nova-small">COMMAND DECK &nbsp; • &nbsp; '
        'STOCK INTELLIGENCE &nbsp; • &nbsp; MARKET SCREENER &nbsp; • &nbsp; '
        'GALAXY RADAR &nbsp; • &nbsp; PORTFOLIO &nbsp; • &nbsp; STRATEGY LAB</div>',
        unsafe_allow_html=True
    )

# -----------------------------------------
# STOCK INTELLIGENCE
# -----------------------------------------

elif page == "Stock Intelligence":

    st.markdown('<p class="nova-eyebrow">NOVA // ASSET ANALYSIS</p>', unsafe_allow_html=True)
    st.title("Stock Intelligence")
    st.caption("PRICE ACTION / TREND / MOMENTUM / RISK")

    default_ticker = st.session_state.get("selected_ticker", "NVDA")

    query = st.text_input(
        "Company name or ticker",
        value=default_ticker
    )

    period = st.selectbox(
        "Historical period",
        ["1y", "2y", "5y", "10y"],
        index=2
    )

    if st.button("ANALYZE ASSET", use_container_width=True):

        match = discover_stock(query)

        if match:
            ticker = match["symbol"]
            st.session_state.selected_ticker = ticker

            data = get_stock_data(ticker, period)

            if not data.empty:
                metrics = calculate_metrics(data)

                st.success(
                    f"{match.get('longname') or match.get('shortname')} "
                    f"({ticker})"
                )

                a, b, c = st.columns(3)
                a.metric("Latest Available Price", f"${metrics['Latest Price']:,.2f}")
                b.metric("Selected-Period Return", f"{metrics['Total Return']:.2f}%")
                c.metric("Annualized Return (CAGR)", f"{metrics['CAGR']:.2f}%")

                d, e, f = st.columns(3)
                d.metric("Day Change", f"{metrics['Daily Change']:.2f}%")
                e.metric("1-Month Return", f"{metrics['1M Return']:.2f}%")
                f.metric("RSI (14)", f"{metrics['RSI (14)']:.1f}")

                g, h, i = st.columns(3)
                g.metric("Annualized Volatility", f"{metrics['Volatility']:.2f}%")
                h.metric("Sharpe Ratio", f"{metrics['Sharpe']:.2f}")
                i.metric("Sortino Ratio", f"{metrics['Sortino']:.2f}")

                j, k, l = st.columns(3)
                j.metric("Maximum Drawdown", f"{metrics['Max Drawdown']:.2f}%")
                k.metric("52-Week Range", f"${metrics['52W Low']:,.2f} – ${metrics['52W High']:,.2f}")
                l.metric("From 52-Week High", f"{metrics['From 52W High']:.2f}%")

                indicators = st.columns(4)
                latest = data.iloc[-1]
                indicators[0].metric("EMA (20)", f"${latest['EMA20']:,.2f}")
                indicators[1].metric("SMA (50)", f"${latest['SMA50']:,.2f}")
                indicators[2].metric("SMA (200)", f"${latest['SMA200']:,.2f}")
                indicators[3].metric("MACD", f"{latest['MACD']:.3f}")

                st.plotly_chart(
                    price_chart(data, ticker),
                    use_container_width=True
                )
                st.plotly_chart(
                    momentum_chart(data, ticker),
                    use_container_width=True
                )
                st.plotly_chart(
                    volume_chart(data, ticker),
                    use_container_width=True
                )

                st.caption(
                    f"Average daily volume (20 sessions): "
                    f"{metrics['Average Volume (20D)']:,.0f} shares."
                )

                st.caption(
                    f"Last data point: {data.index[-1].date()}. "
                    "Historical measurements are not predictions."
                )

                if st.button("ADD TO GALAXY RADAR"):
                    if ticker not in st.session_state.radar:
                        st.session_state.radar.append(ticker)
                    st.success(f"{ticker} added to radar.")

            else:
                st.error("No usable historical price data returned.")
        else:
            st.error("Could not identify that stock. Try its ticker symbol.")

# -----------------------------------------
# MARKET SCREENER
# -----------------------------------------

elif page == "Market Screener":

    st.markdown('<p class="nova-eyebrow">NOVA // MARKET SCAN</p>', unsafe_allow_html=True)
    st.title("Market Screener")
    st.caption(
        "Compare momentum, trend strength, liquidity, volatility, drawdown, "
        "and benchmark sensitivity across a custom ticker universe."
    )

    universe = st.text_input(
        "Ticker universe",
        value="NVDA, AAPL, MSFT, AMZN, GOOGL, META, TSLA, AMD, ORCL, PLTR",
        help="Enter comma-separated stock or ETF tickers. Screening is limited to this list."
    )

    with st.expander("Screening criteria", expanded=True):
        first, second, third = st.columns(3)
        min_price = first.number_input(
            "Minimum price ($)", min_value=0.0, value=0.0, step=5.0
        )
        min_avg_volume = second.number_input(
            "Minimum average daily volume",
            min_value=0,
            value=0,
            step=100_000
        )
        min_dollar_volume = third.number_input(
            "Minimum average dollar volume ($)",
            min_value=0,
            value=0,
            step=1_000_000
        )
        fourth, fifth, sixth = st.columns(3)
        rsi_min, rsi_max = fourth.slider(
            "RSI (14) range",
            min_value=0,
            max_value=100,
            value=(0, 100)
        )
        min_one_month_return = fifth.number_input(
            "Minimum 1-month return (%)",
            value=-100.0,
            step=5.0
        )
        min_three_month_return = sixth.number_input(
            "Minimum 3-month return (%)",
            value=-100.0,
            step=5.0
        )
        seventh, eighth, ninth = st.columns(3)
        max_volatility = seventh.number_input(
            "Maximum annualized volatility (%)",
            min_value=0.0,
            value=200.0,
            step=10.0
        )
        min_relative_volume = eighth.number_input(
            "Minimum relative volume",
            min_value=0.0,
            value=0.0,
            step=0.1
        )
        max_atr = ninth.number_input(
            "Maximum ATR (14) / price (%)",
            min_value=0.0,
            value=100.0,
            step=1.0
        )
        tenth, eleventh, twelfth, thirteenth = st.columns(4)
        require_sma20 = tenth.checkbox("Price above 20-day average")
        require_sma50 = eleventh.checkbox("Price above 50-day average")
        require_sma200 = twelfth.checkbox("Price above 200-day average")
        require_macd = thirteenth.checkbox("MACD bullish")
        limit_beta = st.checkbox("Limit beta versus SPY")
        if limit_beta:
            beta_min, beta_max = st.slider(
                "Beta range",
                min_value=-2.0,
                max_value=4.0,
                value=(0.0, 2.0),
                step=0.1
            )
        sort_by = st.selectbox(
            "Rank results by",
            ["3M (%)", "1M (%)", "1Y (%)", "RSI (14)", "Rel. Volume",
             "Avg $ Volume (20D)", "Beta vs SPY", "Max Drawdown (%)"]
        )
        ascending = st.checkbox("Sort low to high")

    if st.button("RUN MARKET SCAN", use_container_width=True):
        tickers = list(dict.fromkeys(
            ticker.strip().upper()
            for ticker in universe.split(",")
            if ticker.strip()
        ))

        if not tickers:
            st.error("Enter at least one ticker to scan.")
        else:
            screen_rows = []
            unavailable = []
            benchmark_data = get_stock_data("SPY", "1y")
            benchmark_returns = (
                benchmark_data["Returns"] if not benchmark_data.empty else None
            )
            progress = st.progress(0, text="Scanning ticker universe...")

            for index, ticker in enumerate(tickers):
                result = screen_ticker(ticker, benchmark_returns)
                if result is None:
                    unavailable.append(ticker)
                else:
                    screen_rows.append(result)
                progress.progress(
                    (index + 1) / len(tickers),
                    text=f"Scanning {ticker} ({index + 1}/{len(tickers)})"
                )

            progress.empty()

            if screen_rows:
                results = pd.DataFrame(screen_rows)
                filtered = results[
                    (results["Price ($)"] >= min_price)
                    & (results["Avg Volume (20D)"] >= min_avg_volume)
                    & (results["Avg $ Volume (20D)"] >= min_dollar_volume)
                    & results["RSI (14)"].between(rsi_min, rsi_max)
                    & (results["1M (%)"] >= min_one_month_return)
                    & (results["3M (%)"] >= min_three_month_return)
                    & (results["Volatility (%)"] <= max_volatility)
                    & (results["Rel. Volume"] >= min_relative_volume)
                    & (results["ATR (14) (%)"] <= max_atr)
                ]
                if limit_beta:
                    filtered = filtered[
                        filtered["Beta vs SPY"].between(beta_min, beta_max)
                    ]
                if require_sma20:
                    filtered = filtered[filtered["Above SMA20"]]
                if require_sma50:
                    filtered = filtered[filtered["Above SMA50"]]
                if require_sma200:
                    filtered = filtered[filtered["Above SMA200"]]
                if require_macd:
                    filtered = filtered[filtered["MACD Bullish"]]

                st.markdown(
                    f"**{len(filtered)} of {len(results)} assets match** "
                    f"the active criteria."
                )
                st.dataframe(
                    filtered.sort_values(sort_by, ascending=ascending, na_position="last"),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Price ($)": st.column_config.NumberColumn(format="$%.2f"),
                        "Day (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "1M (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "3M (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "6M (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "1Y (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "RSI (14)": st.column_config.NumberColumn(format="%.1f"),
                        "Volatility (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "Avg Volume (20D)": st.column_config.NumberColumn(format="%,.0f"),
                        "Avg $ Volume (20D)": st.column_config.NumberColumn(format="$%,.0f"),
                        "Rel. Volume": st.column_config.NumberColumn(format="%.2fx"),
                        "From 52W High (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "From 52W Low (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "ATR (14) (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "Max Drawdown (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "Beta vs SPY": st.column_config.NumberColumn(format="%.2f"),
                        "Price vs SMA20 (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "Price vs SMA50 (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "Price vs SMA200 (%)": st.column_config.NumberColumn(format="%.2f%%")
                    }
                )
                if filtered.empty:
                    st.info("No assets match all selected criteria.")
            else:
                st.error("No usable market data was returned for the entered tickers.")

            if unavailable:
                st.warning(f"Skipped tickers with unavailable data: {', '.join(unavailable)}")

    st.caption(
        "Scan universe is user-defined. Metrics use recent historical data; "
        "beta is estimated against SPY and these screens are not investment advice."
    )

# -----------------------------------------
# GALAXY RADAR
# -----------------------------------------

elif page == "Galaxy Radar":

    st.title("Galaxy Intelligence Radar")
    st.caption("DISCOVERED ASSETS / RESEARCH WATCHLIST")

    new_ticker = st.text_input(
        "Add a company or ticker",
        placeholder="Example: AMD"
    )

    if st.button("DISCOVER AND ADD"):
        match = discover_stock(new_ticker)

        if match:
            ticker = match["symbol"]
            if ticker not in st.session_state.radar:
                st.session_state.radar.append(ticker)
            st.success(
                f"{match.get('longname') or match.get('shortname')} "
                f"({ticker}) added."
            )
        else:
            st.error("No matching stock found.")

    if st.session_state.radar:

        radar_rows = []

        for ticker in st.session_state.radar:
            data = get_stock_data(ticker, "1y")

            if not data.empty:
                metrics = calculate_metrics(data)
                radar_rows.append({
                    "Ticker": ticker,
                    "Latest Price": metrics["Latest Price"],
                    "1Y Return (%)": metrics["Total Return"],
                    "Volatility (%)": metrics["Volatility"],
                    "Sharpe": metrics["Sharpe"]
                })

        if radar_rows:
            st.dataframe(
                pd.DataFrame(radar_rows),
                use_container_width=True,
                hide_index=True
            )
    else:
        st.info("Your galaxy radar is waiting for its first asset.")

# -----------------------------------------
# PORTFOLIO ANALYTICS
# -----------------------------------------

elif page == "Portfolio Analytics":

    st.markdown('<p class="nova-eyebrow">NOVA // PORTFOLIO SYSTEM</p>', unsafe_allow_html=True)
    st.title("Portfolio Intelligence")
    st.caption("HOLDINGS / ALLOCATION / HISTORICAL RISK & PERFORMANCE")

    st.subheader("Edit Holdings")

    ticker_input = st.text_input("Ticker symbol")
    shares_input = st.number_input(
        "Number of shares",
        min_value=0,
        step=1
    )

    if st.button("UPDATE HOLDING"):
        ticker = ticker_input.strip().upper()

        if ticker and shares_input >= 0:
            if shares_input == 0:
                st.session_state.portfolio.pop(ticker, None)
            else:
                st.session_state.portfolio[ticker] = int(shares_input)

    rows = []
    price_history = {}

    for ticker, shares in st.session_state.portfolio.items():
        data = get_stock_data(ticker, "1y")

        if not data.empty:
            price = float(data["Close"].iloc[-1])
            previous_close = (
                float(data["Close"].iloc[-2])
                if len(data) > 1 else price
            )
            one_year_ago = float(data["Close"].iloc[0])
            rows.append({
                "Ticker": ticker,
                "Shares": shares,
                "Latest Price": price,
                "Day Change (%)": (price / previous_close - 1) * 100,
                "1Y Change (%)": (price / one_year_ago - 1) * 100,
                "Estimated Value": price * shares
            })
            price_history[ticker] = data["Close"]

    if rows:
        frame = pd.DataFrame(rows)
        total_value = frame["Estimated Value"].sum()
        frame["Weight (%)"] = frame["Estimated Value"] / total_value * 100

        if price_history:
            aligned_prices = pd.concat(price_history, axis=1).sort_index().ffill().dropna()
            held_values = pd.DataFrame({
                ticker: aligned_prices[ticker] * st.session_state.portfolio[ticker]
                for ticker in aligned_prices.columns
            })
            historical_portfolio = held_values.sum(axis=1)
            historical_returns = historical_portfolio.pct_change().dropna()
            portfolio_total_return = (
                historical_portfolio.iloc[-1] / historical_portfolio.iloc[0] - 1
            ) * 100
            portfolio_volatility = (
                historical_returns.std() * np.sqrt(252) * 100
                if not historical_returns.empty else 0
            )
            portfolio_drawdown = (
                historical_portfolio / historical_portfolio.cummax() - 1
            ).min() * 100
            daily_change = (
                historical_returns.iloc[-1] * 100
                if not historical_returns.empty else 0
            )

            a, b, c, d = st.columns(4)
            a.metric("Estimated Portfolio Value", f"${total_value:,.2f}")
            b.metric("Daily Change", f"{daily_change:.2f}%")
            c.metric("1Y Return*", f"{portfolio_total_return:.2f}%")
            d.metric("1Y Volatility", f"{portfolio_volatility:.2f}%")
            st.metric("Maximum Drawdown*", f"{portfolio_drawdown:.2f}%")

        st.dataframe(
            frame.sort_values("Estimated Value", ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Latest Price": st.column_config.NumberColumn(format="$%.2f"),
                "Day Change (%)": st.column_config.NumberColumn(format="%.2f%%"),
                "1Y Change (%)": st.column_config.NumberColumn(format="%.2f%%"),
                "Estimated Value": st.column_config.NumberColumn(format="$%.2f"),
                "Weight (%)": st.column_config.NumberColumn(format="%.2f%%")
            }
        )

        fig = go.Figure(go.Pie(
            labels=frame["Ticker"],
            values=frame["Estimated Value"],
            hole=0.62,
            marker=dict(colors=["#43c7d9", "#f0aa56", "#6e9eff", "#54d6a5", "#9d83eb"])
        ))

        fig.update_layout(
            title="CURRENT ALLOCATION",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )

        st.plotly_chart(fig, use_container_width=True)

        if len(price_history) > 1:
            st.subheader("Holdings Correlation")
            returns_by_ticker = aligned_prices.pct_change().dropna()
            st.dataframe(
                returns_by_ticker.corr().round(2),
                use_container_width=True
            )

    st.caption(
        "*Historical estimates hold today's share counts constant over the "
        "available period; they are not actual account performance and exclude "
        "cash flows, fees, taxes and transaction history."
    )

# -----------------------------------------
# STRATEGY RESEARCH
# -----------------------------------------

elif page == "Strategy Research":

    st.markdown('<p class="nova-eyebrow">NOVA // STRATEGY SIMULATION</p>', unsafe_allow_html=True)
    st.title("Strategy Research Lab")
    st.caption("HISTORICAL MOVING AVERAGE SIMULATION")

    ticker = st.text_input("Research ticker", "NVDA")

    if st.button("RUN HISTORICAL SIMULATION"):

        data = get_stock_data(ticker.strip().upper(), "5y")

        if not data.empty:

            data = data.copy()
            data["Signal"] = (
                data["SMA50"] > data["SMA200"]
            ).astype(int)

            data["Strategy"] = (
                data["Signal"].shift(1) * data["Returns"]
            )

            data["BuyHold"] = data["Returns"]

            strategy_return = (
                (1 + data["Strategy"].dropna()).prod() - 1
            ) * 100

            buyhold_return = (
                (1 + data["BuyHold"].dropna()).prod() - 1
            ) * 100

            a, b = st.columns(2)
            a.metric("Strategy Return", f"{strategy_return:.2f}%")
            b.metric("Buy & Hold Return", f"{buyhold_return:.2f}%")

            equity = pd.DataFrame({
                "Strategy": (1 + data["Strategy"].fillna(0)).cumprod(),
                "Buy & Hold": (1 + data["BuyHold"].fillna(0)).cumprod()
            })

            st.line_chart(equity)

            st.warning(
                "Historical simulation only. This simple model does not "
                "include all real-world trading costs, slippage or taxes."
            )
        else:
            st.error("Could not retrieve historical data.")

# -----------------------------------------
# SYSTEM INFORMATION
# -----------------------------------------

elif page == "System Information":

    st.title("System Information")

    st.markdown("""
    ### NOVA — MARKET INTELLIGENCE

    **Current modules**
    - Market data retrieval
    - Company and ticker discovery
    - Stock price, trend, momentum and risk analytics
    - Custom-universe market screening
    - Portfolio valuation, performance and correlation
    - Galaxy research radar
    - Historical strategy simulation

    **Planned modules**
    - Multi-strategy optimization
    - Research report generation
    - Persistent database
    - User authentication

    **System limitations**
    - Market data may be delayed.
    - Research outputs are historical simulations.
    - No brokerage connection or trade execution.
    - Notebook research modules are not automatically connected
      to this standalone application.
    - Screening is limited to the user-provided ticker universe.
    """)

