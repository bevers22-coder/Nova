
%%writefile app.py

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# -----------------------------------------
# VEYRO SIGMA — STANDALONE APPLICATION
# -----------------------------------------

st.set_page_config(
    page_title="Veyro Sigma",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.stApp {
    background: radial-gradient(circle at 50% 0%, #101e38, #050914 65%);
    color: #e1edff;
}
[data-testid="stSidebar"] {
    background: #071020;
    border-right: 1px solid #183c65;
}
h1, h2, h3 {
    color: #d8eaff !important;
}
div[data-testid="stMetric"] {
    background: #0b1930;
    border: 1px solid #1d4168;
    padding: 15px;
    border-radius: 10px;
}
.stButton button {
    background: #10365c;
    color: white;
    border: 1px solid #2c83c8;
    border-radius: 7px;
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
    data["Volatility"] = data["Returns"].rolling(20).std() * np.sqrt(252)

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

    drawdown = (
        (prices / prices.cummax() - 1).min() * 100
    )

    return {
        "Latest Price": float(prices.iloc[-1]),
        "Total Return": float(total_return),
        "CAGR": float(cagr),
        "Volatility": float(volatility),
        "Sharpe": float(sharpe),
        "Max Drawdown": float(drawdown)
    }


def price_chart(data, ticker):
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=data.index,
        y=data["Close"],
        name="Price",
        line=dict(color="#45b8ff", width=2)
    ))

    for column, color in [
        ("SMA20", "#c084fc"),
        ("SMA50", "#f59e0b"),
        ("SMA200", "#5ee6bd")
    ]:
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data[column],
            name=column,
            line=dict(color=color, width=1)
        ))

    fig.update_layout(
        title=f"{ticker} — Historical Price Intelligence",
        template="plotly_dark",
        paper_bgcolor="#071020",
        plot_bgcolor="#071020",
        height=480,
        hovermode="x unified"
    )

    return fig


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

# -----------------------------------------
# SIDEBAR NAVIGATION
# -----------------------------------------

st.sidebar.markdown("## 🌌 VEYRO SIGMA")
st.sidebar.caption("CAPITAL INTELLIGENCE SYSTEM")
st.sidebar.divider()

page = st.sidebar.radio(
    "NAVIGATION",
    [
        "Command Center",
        "Stock Intelligence",
        "Galaxy Radar",
        "Portfolio Analytics",
        "Strategy Research",
        "System Information"
    ]
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

    st.title("VEYRO SIGMA")
    st.caption("QUANTITATIVE RESEARCH & MARKET INTELLIGENCE")

    st.markdown("### SYSTEM OVERVIEW")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Research Modules", "6")
    col2.metric("Portfolio Assets", len(st.session_state.portfolio))
    col3.metric("Radar Assets", len(st.session_state.radar))
    col4.metric("System Mode", "Research")

    st.divider()

    st.subheader("Research Command Interface")

    command = st.text_input(
        "Enter a company name or ticker",
        placeholder="Example: NVIDIA, AAPL, Microsoft..."
    )

    if st.button("INITIATE RESEARCH", use_container_width=True):
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

# -----------------------------------------
# STOCK INTELLIGENCE
# -----------------------------------------

elif page == "Stock Intelligence":

    st.title("Stock Intelligence")
    st.caption("COMPANY DISCOVERY / PRICE ANALYSIS / RISK METRICS")

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
                b.metric("Historical Return", f"{metrics['Total Return']:.2f}%")
                c.metric("Annualized Return", f"{metrics['CAGR']:.2f}%")

                d, e, f = st.columns(3)
                d.metric("Annualized Volatility", f"{metrics['Volatility']:.2f}%")
                e.metric("Sharpe Ratio", f"{metrics['Sharpe']:.2f}")
                f.metric("Maximum Drawdown", f"{metrics['Max Drawdown']:.2f}%")

                st.plotly_chart(
                    price_chart(data, ticker),
                    use_container_width=True
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

    st.title("Portfolio Intelligence")
    st.caption("HOLDINGS / ALLOCATION / HISTORICAL PERFORMANCE")

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

    for ticker, shares in st.session_state.portfolio.items():
        data = get_stock_data(ticker, "5d")

        if not data.empty:
            price = float(data["Close"].iloc[-1])
            rows.append({
                "Ticker": ticker,
                "Shares": shares,
                "Latest Price": price,
                "Estimated Value": price * shares
            })

    if rows:
        frame = pd.DataFrame(rows)
        total_value = frame["Estimated Value"].sum()

        st.metric("Estimated Portfolio Value", f"${total_value:,.2f}")
        st.dataframe(frame, use_container_width=True, hide_index=True)

        fig = go.Figure(go.Pie(
            labels=frame["Ticker"],
            values=frame["Estimated Value"],
            hole=0.55
        ))

        fig.update_layout(
            title="Portfolio Allocation",
            template="plotly_dark",
            paper_bgcolor="#071020"
        )

        st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "Estimated current holdings value. This is not historical account "
        "performance and excludes fees, taxes and transaction history."
    )

# -----------------------------------------
# STRATEGY RESEARCH
# -----------------------------------------

elif page == "Strategy Research":

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
    ### VEYRO SIGMA — DEVELOPMENT BUILD

    **Current modules**
    - Market data retrieval
    - Company and ticker discovery
    - Stock price intelligence
    - Portfolio valuation
    - Galaxy research radar
    - Historical strategy simulation

    **Planned modules**
    - AI research assistant
    - Voice command system
    - Advanced risk analytics
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
    """)

