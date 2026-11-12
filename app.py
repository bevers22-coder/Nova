

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# -----------------------------------------
# NOVA — MARKET INTELLIGENCE
# -----------------------------------------

st.set_page_config(
    page_title="Nova | Market Intelligence",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.stApp {
    background:
        radial-gradient(ellipse at 50% -18%, rgba(19, 103, 140, .28), transparent 48%),
        linear-gradient(rgba(18, 54, 75, .10) 1px, transparent 1px),
        linear-gradient(90deg, rgba(18, 54, 75, .10) 1px, transparent 1px),
        #07111b;
    background-size: auto, 42px 42px, 42px 42px, auto;
    color: #dcecf2;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0a1924, #07111b 78%);
    border-right: 1px solid rgba(81, 196, 218, .28);
}
h1, h2, h3, h4 {
    color: #e4f6fa !important;
    letter-spacing: .025em;
}
[data-testid="stCaptionContainer"] {
    color: #82a9b5;
}
div[data-testid="stMetric"] {
    background: linear-gradient(145deg, rgba(16, 39, 53, .96), rgba(8, 24, 35, .96));
    border: 1px solid rgba(74, 190, 213, .25);
    border-radius: 4px;
    padding: 16px;
    box-shadow: inset 0 1px 0 rgba(150, 233, 245, .05);
}
[data-testid="stMetricLabel"] {
    color: #86aeb8;
    text-transform: uppercase;
    letter-spacing: .08em;
    font-size: .72rem;
}
[data-testid="stMetricValue"] {
    color: #e6f8fa;
}
.stButton button {
    background: linear-gradient(110deg, #0e4b60, #12364a);
    color: #e7fbff;
    border: 1px solid #39b6cb;
    border-radius: 3px;
    letter-spacing: .06em;
}
.stButton button:hover {
    background: #17637a;
    border-color: #8befff;
    color: white;
}
[data-testid="stDataFrame"] {
    border: 1px solid rgba(74, 190, 213, .20);
}
div[data-testid="stAlert"] {
    border-radius: 3px;
}
.nova-eyebrow {
    color: #69d7e8;
    font-size: .76rem;
    letter-spacing: .18em;
    text-transform: uppercase;
}
.nova-panel {
    border: 1px solid rgba(74, 190, 213, .30);
    border-left: 3px solid #49c5d9;
    padding: 18px 20px;
    background: linear-gradient(110deg, rgba(13, 43, 58, .92), rgba(9, 24, 35, .78));
    margin: 8px 0 22px;
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
        title=f"{ticker} | PRICE & TREND",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#091722",
        height=440,
        hovermode="x unified",
        margin=dict(l=20, r=20, t=55, b=20),
        legend=dict(orientation="h", y=1.08)
    )

    return fig


def volume_chart(data, ticker):
    fig = go.Figure(go.Bar(
        x=data.index,
        y=data["Volume"],
        name="Volume",
        marker_color="#268da5",
        opacity=0.8
    ))
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data["AverageVolume20"],
        name="20D average",
        line=dict(color="#f1ae57", width=1.5)
    ))
    fig.update_layout(
        title=f"{ticker} | TRADING VOLUME",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#091722",
        height=280,
        margin=dict(l=20, r=20, t=55, b=20),
        hovermode="x unified"
    )
    return fig


def screen_ticker(ticker):
    data = get_stock_data(ticker, "1y")
    if data.empty or len(data) < 22:
        return None

    metrics = calculate_metrics(data)
    latest = data.iloc[-1]
    return {
        "Ticker": ticker,
        "Price ($)": metrics["Latest Price"],
        "Day (%)": metrics["Daily Change"],
        "1M (%)": metrics["1M Return"],
        "1Y (%)": metrics["Total Return"],
        "RSI (14)": metrics["RSI (14)"],
        "Volatility (%)": metrics["Volatility"],
        "Avg Volume (20D)": metrics["Average Volume (20D)"],
        "Rel. Volume": (
            float(latest["Volume"] / latest["AverageVolume20"])
            if latest["AverageVolume20"] > 0 else np.nan
        ),
        "From 52W High (%)": metrics["From 52W High"],
        "Above SMA50": bool(latest["Close"] > latest["SMA50"]),
        "Above SMA200": bool(latest["Close"] > latest["SMA200"])
    }


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

st.sidebar.markdown("## ✦ NOVA")
st.sidebar.caption("MARKET INTELLIGENCE SYSTEM")
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

    st.markdown('<p class="nova-eyebrow">NOVA // MARKET INTELLIGENCE SYSTEM</p>', unsafe_allow_html=True)
    st.title("Command Center")
    st.markdown("""
    <div class="nova-panel">
      <strong>MARKET RESEARCH CONSOLE</strong><br>
      Discover an asset, inspect its signals, or scan a custom universe.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### SYSTEM STATUS")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Research Modules", "7")
    col2.metric("Portfolio Assets", len(st.session_state.portfolio))
    col3.metric("Radar Assets", len(st.session_state.radar))
    col4.metric("System Mode", "Research")

    st.divider()

    st.subheader("Asset Discovery")

    command = st.text_input(
        "Enter a company name or ticker",
        placeholder="Example: NVIDIA, AAPL, Microsoft..."
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

                st.plotly_chart(
                    price_chart(data, ticker),
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
    st.caption("Filter a custom ticker universe by momentum, trend, liquidity, and risk.")

    universe = st.text_input(
        "Ticker universe",
        value="NVDA, AAPL, MSFT, AMZN, GOOGL, META, TSLA, AMD, ORCL, PLTR",
        help="Enter comma-separated stock or ETF tickers. Screening is limited to this list."
    )

    with st.expander("Screening criteria", expanded=True):
        first, second = st.columns(2)
        min_price = first.number_input("Minimum price ($)", min_value=0.0, value=0.0, step=5.0)
        min_avg_volume = second.number_input(
            "Minimum average daily volume",
            min_value=0,
            value=0,
            step=100_000
        )
        third, fourth = st.columns(2)
        rsi_min, rsi_max = third.slider(
            "RSI (14) range",
            min_value=0,
            max_value=100,
            value=(0, 100)
        )
        min_one_month_return = fourth.number_input(
            "Minimum 1-month return (%)",
            value=-100.0,
            step=5.0
        )
        fifth, sixth = st.columns(2)
        require_sma50 = fifth.checkbox("Price above 50-day average")
        require_sma200 = sixth.checkbox("Price above 200-day average")

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
            progress = st.progress(0, text="Scanning ticker universe...")

            for index, ticker in enumerate(tickers):
                result = screen_ticker(ticker)
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
                    & results["RSI (14)"].between(rsi_min, rsi_max)
                    & (results["1M (%)"] >= min_one_month_return)
                ]
                if require_sma50:
                    filtered = filtered[filtered["Above SMA50"]]
                if require_sma200:
                    filtered = filtered[filtered["Above SMA200"]]

                st.markdown(
                    f"**{len(filtered)} of {len(results)} assets match** "
                    f"the active criteria."
                )
                st.dataframe(
                    filtered.sort_values("1M (%)", ascending=False),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Price ($)": st.column_config.NumberColumn(format="$%.2f"),
                        "Day (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "1M (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "1Y (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "RSI (14)": st.column_config.NumberColumn(format="%.1f"),
                        "Volatility (%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "Avg Volume (20D)": st.column_config.NumberColumn(format="%,.0f"),
                        "Rel. Volume": st.column_config.NumberColumn(format="%.2fx"),
                        "From 52W High (%)": st.column_config.NumberColumn(format="%.2f%%")
                    }
                )
                if filtered.empty:
                    st.info("No assets match all selected criteria.")
            else:
                st.error("No usable market data was returned for the entered tickers.")

            if unavailable:
                st.warning(f"Skipped tickers with unavailable data: {', '.join(unavailable)}")

    st.caption("Scan universe is user-defined. Metrics use recent historical data and are not investment recommendations.")

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

