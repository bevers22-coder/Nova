from dataclasses import dataclass
from typing import Mapping

import numpy as np
import yfinance as yf
import pandas as pd


@dataclass
class PortfolioAnalytics:
    holdings: pd.DataFrame
    total_value: float
    as_of: pd.Timestamp
    daily_change_amount: float | None
    daily_change_pct: float | None
    one_year_return_pct: float | None
    annualized_volatility_pct: float | None
    max_drawdown_pct: float | None
    correlation: pd.DataFrame


@dataclass
class PortfolioQuote:
    price: float
    previous_close: float | None
    as_of: pd.Timestamp


def _one_year_return(prices: pd.Series, as_of: pd.Timestamp) -> float | None:
    cutoff = as_of - pd.DateOffset(years=1)
    baseline = prices.loc[prices.index <= cutoff]

    if baseline.empty or (cutoff - baseline.index[-1]).days > 7:
        return None

    return float((prices.iloc[-1] / baseline.iloc[-1] - 1) * 100)


def calculate_portfolio_analytics(
    holdings: Mapping[str, float],
    price_history: Mapping[str, pd.DataFrame],
    intraday_history: Mapping[str, pd.DataFrame] | None = None,
) -> PortfolioAnalytics:
    close_series = {}
    adjusted_series = {}
    adjusted_available = {}

    for ticker, history in price_history.items():
        if "Close" not in history:
            continue

        close = history["Close"].dropna().astype(float)
        if close.empty:
            continue

        has_adjusted_close = "Adj Close" in history
        adjusted = (
            history["Adj Close"].dropna().astype(float)
            if has_adjusted_close else close
        )
        if adjusted.empty:
            adjusted = close
            has_adjusted_close = False
        close_series[ticker] = close
        adjusted_series[ticker] = adjusted
        adjusted_available[ticker] = has_adjusted_close

    if not close_series:
        raise ValueError("No valid closing prices are available for the holdings.")

    close_prices = pd.concat(close_series, axis=1).sort_index().ffill().dropna()
    adjusted_prices = (
        pd.concat(adjusted_series, axis=1).sort_index().ffill().dropna()
    )
    available_tickers = [
        ticker for ticker in holdings if ticker in close_prices.columns
    ]

    if not available_tickers:
        raise ValueError("No valid closing prices are available for the holdings.")

    close_prices = close_prices[available_tickers]
    adjusted_prices = adjusted_prices.reindex(
        index=close_prices.index, columns=available_tickers
    ).ffill().dropna()
    close_prices = close_prices.loc[adjusted_prices.index]

    latest_quotes = {}
    for ticker in available_tickers:
        daily_close = close_series[ticker]
        latest_daily_date = pd.Timestamp(daily_close.index[-1]).date()
        intraday = (
            intraday_history.get(ticker)
            if intraday_history is not None else None
        )
        intraday_close = (
            intraday["Close"].dropna().astype(float)
            if intraday is not None and "Close" in intraday else pd.Series(dtype=float)
        )

        if (
            not intraday_close.empty
            and pd.Timestamp(intraday_close.index[-1]).date() >= latest_daily_date
        ):
            timestamp = pd.Timestamp(intraday_close.index[-1])
            quote_date = timestamp.date()
            prior_closes = daily_close.loc[
                [pd.Timestamp(date).date() < quote_date for date in daily_close.index]
            ]
            previous_close = (
                float(prior_closes.iloc[-1]) if not prior_closes.empty else None
            )
            latest_quotes[ticker] = PortfolioQuote(
                price=float(intraday_close.iloc[-1]),
                previous_close=previous_close,
                as_of=timestamp,
            )
        else:
            previous_close = (
                float(daily_close.iloc[-2]) if len(daily_close) > 1 else None
            )
            latest_quotes[ticker] = PortfolioQuote(
                price=float(daily_close.iloc[-1]),
                previous_close=previous_close,
                as_of=pd.Timestamp(daily_close.index[-1]),
            )

    as_of = max(
        (quote.as_of for quote in latest_quotes.values()),
        key=lambda timestamp: (
            timestamp.tz_localize("UTC")
            if timestamp.tzinfo is None else timestamp.tz_convert("UTC")
        ),
    )
    values = {
        ticker: latest_quotes[ticker].price * holdings[ticker]
        for ticker in available_tickers
    }
    total_value = sum(values.values())

    if total_value <= 0:
        raise ValueError("Portfolio value must be positive.")

    history_as_of = adjusted_prices.index[-1]
    rows = []
    for ticker in available_tickers:
        quote = latest_quotes[ticker]
        day_change_amount = (
            (quote.price - quote.previous_close) * holdings[ticker]
            if quote.previous_close is not None else None
        )
        day_change_pct = (
            (quote.price / quote.previous_close - 1) * 100
            if quote.previous_close is not None and quote.previous_close != 0
            else None
        )
        one_year_return = (
            _one_year_return(adjusted_prices[ticker], history_as_of)
            if adjusted_available[ticker] else None
        )
        rows.append({
            "Ticker": ticker,
            "Shares": holdings[ticker],
            "Quote Date": quote.as_of.strftime("%Y-%m-%d %H:%M %Z")
            if quote.as_of.tzinfo else quote.as_of.strftime("%Y-%m-%d"),
            "Latest Price": quote.price,
            "Day Change ($)": day_change_amount,
            "Day Change (%)": day_change_pct,
            "1Y Total Return (%)": one_year_return,
            "Market Value": values[ticker],
            "Weight (%)": values[ticker] / total_value * 100,
        })

    adjusted_portfolio_value = sum(
        adjusted_prices[ticker] * holdings[ticker]
        for ticker in available_tickers
    )
    daily_change_amount = None
    daily_change_pct = None
    quotes_share_session = len({
        quote.as_of.date() for quote in latest_quotes.values()
    }) == 1
    if quotes_share_session and all(
        latest_quotes[ticker].previous_close is not None
        for ticker in available_tickers
    ):
        previous_portfolio_value = sum(
            latest_quotes[ticker].previous_close * holdings[ticker]
            for ticker in available_tickers
        )
        if previous_portfolio_value > 0:
            daily_change_amount = sum(
                (latest_quotes[ticker].price - latest_quotes[ticker].previous_close)
                * holdings[ticker]
                for ticker in available_tickers
            )
            daily_change_pct = (
                daily_change_amount / previous_portfolio_value * 100
            )

    cutoff = history_as_of - pd.DateOffset(years=1)
    baseline = adjusted_portfolio_value.loc[
        adjusted_portfolio_value.index <= cutoff
    ]
    one_year_return = None
    annualized_volatility = None
    max_drawdown = None

    has_adjusted_history = all(
        adjusted_available[ticker] for ticker in available_tickers
    )
    if (
        has_adjusted_history
        and not baseline.empty
        and (cutoff - baseline.index[-1]).days <= 7
    ):
        one_year_return = float(
            (
                adjusted_portfolio_value.loc[history_as_of]
                / baseline.iloc[-1] - 1
            ) * 100
        )
        one_year_values = adjusted_portfolio_value.loc[
            adjusted_portfolio_value.index >= baseline.index[-1]
        ]
        one_year_returns = one_year_values.pct_change(
            fill_method=None
        ).dropna()
        volatility = one_year_returns.std()
        if np.isfinite(volatility):
            annualized_volatility = float(
                volatility * np.sqrt(252) * 100
            )
        max_drawdown = float(
            (one_year_values / one_year_values.cummax() - 1).min() * 100
        )

    stock_returns = close_prices.pct_change(fill_method=None).dropna()
    correlation = stock_returns.corr().round(2)

    return PortfolioAnalytics(
        holdings=pd.DataFrame(rows),
        total_value=float(total_value),
        as_of=as_of,
        daily_change_amount=(
            float(daily_change_amount) if daily_change_amount is not None else None
        ),
        daily_change_pct=float(daily_change_pct) if daily_change_pct is not None else None,
        one_year_return_pct=one_year_return,
        annualized_volatility_pct=annualized_volatility,
        max_drawdown_pct=max_drawdown,
        correlation=correlation,
    )


class VeyroPortfolio:

    def __init__(self, holdings):
        self.holdings = holdings
        self.prices = {}

    def retrieve_prices(self):

        for ticker in self.holdings:

            try:
                history = yf.Ticker(ticker).history(
                    period="5d"
                )

                if history.empty:
                    continue

                self.prices[ticker] = float(
                    history["Close"].dropna().iloc[-1]
                )

            except Exception as error:
                print(f"{ticker} data error: {error}")

        return self.prices

    def portfolio_report(self):

        rows = []

        for ticker, holding in self.holdings.items():

            if ticker not in self.prices:
                continue

            shares = holding["shares"]
            price = self.prices[ticker]
            value = shares * price

            rows.append({
                "Ticker": ticker,
                "Shares": shares,
                "Market Price": round(price, 2),
                "Market Value": round(value, 2)
            })

        report = pd.DataFrame(rows)

        if report.empty:
            return None

        total_value = report["Market Value"].sum()

        report["Portfolio Weight (%)"] = (
            report["Market Value"] / total_value * 100
        ).round(2)

        return report

