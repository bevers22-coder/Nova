


import yfinance as yf
import pandas as pd
import numpy as np


class VeyroPortfolioIntelligence:

    def __init__(self, holdings):
        self.holdings = holdings
        self.prices = None
        self.portfolio_values = None
        self.daily_returns = None

    def retrieve_history(self, period="5y"):

        tickers = list(self.holdings.keys()) + ["SPY"]

        data = yf.download(
            tickers,
            period=period,
            interval="1d",
            auto_adjust=True,
            progress=False
        )

        if data.empty:
            raise ValueError("Historical market data unavailable.")

        if isinstance(data.columns, pd.MultiIndex):
            if "Close" not in data.columns.get_level_values(0):
                raise ValueError("Closing prices unavailable.")

            prices = data["Close"]

        else:
            prices = data[["Close"]].rename(
                columns={"Close": tickers[0]}
            )

        missing = [
            ticker for ticker in tickers
            if ticker not in prices.columns
        ]

        if missing:
            raise ValueError(f"Missing stock data: {missing}")

        self.prices = prices[tickers].dropna()

        if self.prices.empty:
            raise ValueError("No complete historical data available.")

        return self.prices

    def build_portfolio_history(self):

        if self.prices is None:
            raise ValueError("Retrieve historical data first.")

        stock_values = pd.DataFrame(index=self.prices.index)

        for ticker, holding in self.holdings.items():
            stock_values[ticker] = (
                self.prices[ticker] * holding["shares"]
            )

        portfolio_value = stock_values.sum(axis=1)

        benchmark_value = (
            self.prices["SPY"] / self.prices["SPY"].iloc[0]
        ) * portfolio_value.iloc[0]

        self.portfolio_values = pd.DataFrame({
            "Portfolio": portfolio_value,
            "S&P 500": benchmark_value
        })

        self.daily_returns = (
            self.portfolio_values.pct_change().dropna()
        )

        return self.portfolio_values

    def calculate_risk_metrics(self):

        if self.daily_returns is None:
            raise ValueError("Build portfolio history first.")

        returns = self.daily_returns["Portfolio"]
        equity = self.portfolio_values["Portfolio"]

        benchmark = self.portfolio_values["S&P 500"]

        years = len(returns) / 252

        total_return = (
            equity.iloc[-1] / equity.iloc[0] - 1
        ) * 100

        cagr = (
            (equity.iloc[-1] / equity.iloc[0])
            ** (1 / years) - 1
        ) * 100 if years > 0 else 0

        volatility = returns.std() * np.sqrt(252) * 100

        sharpe = (
            returns.mean() / returns.std() * np.sqrt(252)
            if returns.std() > 0 else 0
        )

        drawdown = equity / equity.cummax() - 1

        benchmark_return = (
            benchmark.iloc[-1] / benchmark.iloc[0] - 1
        ) * 100

        return {
            "Portfolio Return (%)": round(total_return, 2),
            "Annualized Return (%)": round(cagr, 2),
            "S&P 500 Return (%)": round(benchmark_return, 2),
            "Annualized Volatility (%)": round(volatility, 2),
            "Sharpe Ratio": round(sharpe, 2),
            "Maximum Drawdown (%)": round(
                drawdown.min() * 100, 2
            ),
            "Best Daily Return (%)": round(
                returns.max() * 100, 2
            ),
            "Worst Daily Return (%)": round(
                returns.min() * 100, 2
            )
        }

    def calculate_correlations(self):

        if self.prices is None:
            raise ValueError("Retrieve historical data first.")

        stock_returns = self.prices[
            list(self.holdings.keys())
        ].pct_change().dropna()

        return stock_returns.corr().round(2)

    def calculate_allocation(self):

        if self.prices is None:
            raise ValueError("Retrieve historical data first.")

        latest_prices = self.prices.iloc[-1]

        values = {
            ticker: latest_prices[ticker] * holding["shares"]
            for ticker, holding in self.holdings.items()
        }

        total = sum(values.values())

        if total <= 0:
            raise ValueError("Portfolio value must be positive.")

        allocation = pd.DataFrame([
            {
                "Ticker": ticker,
                "Market Value ($)": round(value, 2),
                "Weight (%)": round(value / total * 100, 2)
            }
            for ticker, value in values.items()
        ])

        return allocation.sort_values(
            "Weight (%)", ascending=False
        )

