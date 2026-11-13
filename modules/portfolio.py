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
    daily_change_pct: float | None
    one_year_return_pct: float | None
    annualized_volatility_pct: float | None
    max_drawdown_pct: float | None
    correlation: pd.DataFrame


def _one_year_return(prices: pd.Series, as_of: pd.Timestamp) -> float | None:
    cutoff = as_of - pd.DateOffset(years=1)
    baseline = prices.loc[prices.index <= cutoff]

    if baseline.empty or (cutoff - baseline.index[-1]).days > 7:
        return None

    return float((prices.iloc[-1] / baseline.iloc[-1] - 1) * 100)


def calculate_portfolio_analytics(
    holdings: Mapping[str, int],
    price_history: Mapping[str, pd.DataFrame],
) -> PortfolioAnalytics:
    close_series = {}
    adjusted_series = {}
    adjusted_available = {}
    quote_dates = {}

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
        quote_dates[ticker] = close.index[-1]

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
    as_of = close_prices.index[-1]

    latest_prices = close_prices.iloc[-1]
    values = {
        ticker: float(latest_prices[ticker] * holdings[ticker])
        for ticker in available_tickers
    }
    total_value = sum(values.values())

    if total_value <= 0:
        raise ValueError("Portfolio value must be positive.")

    rows = []
    for ticker in available_tickers:
        one_year_return = (
            _one_year_return(adjusted_prices[ticker], as_of)
            if adjusted_available[ticker] else None
        )
        rows.append({
            "Ticker": ticker,
            "Shares": holdings[ticker],
            "Quote Date": quote_dates[ticker].strftime("%Y-%m-%d"),
            "Latest Price": float(latest_prices[ticker]),
            "Day Change (%)": None,
            "1Y Total Return (%)": one_year_return,
            "Market Value": values[ticker],
            "Weight (%)": values[ticker] / total_value * 100,
        })

    raw_portfolio_value = sum(
        close_prices[ticker] * holdings[ticker]
        for ticker in available_tickers
    )
    adjusted_portfolio_value = sum(
        adjusted_prices[ticker] * holdings[ticker]
        for ticker in available_tickers
    )
    raw_returns = raw_portfolio_value.pct_change(fill_method=None).dropna()

    if not raw_returns.empty:
        for row in rows:
            ticker = row["Ticker"]
            previous_price = close_prices[ticker].iloc[-2]
            row["Day Change (%)"] = (
                latest_prices[ticker] / previous_price - 1
            ) * 100

    cutoff = as_of - pd.DateOffset(years=1)
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
            (adjusted_portfolio_value.iloc[-1] / baseline.iloc[-1] - 1) * 100
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
        daily_change_pct=(
            float(raw_returns.iloc[-1] * 100) if not raw_returns.empty else None
        ),
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

