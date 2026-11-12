import numpy as np
import pandas as pd


class VeyroBacktester:

    def __init__(self, initial_capital=10000, transaction_cost=0.001):
        self.initial_capital = initial_capital
        self.transaction_cost = transaction_cost

    def moving_average_strategy(self, data, fast=20, slow=50):

        df = data.copy()

        df["Fast_MA"] = df["Close"].rolling(fast).mean()
        df["Slow_MA"] = df["Close"].rolling(slow).mean()

        df["Signal"] = np.where(
            df["Fast_MA"] > df["Slow_MA"], 1, 0
        )

        df["Position"] = df["Signal"].shift(1).fillna(0)

        df["Market_Return"] = df["Close"].pct_change().fillna(0)

        df["Turnover"] = df["Position"].diff().abs()
        df["Turnover"] = df["Turnover"].fillna(
            df["Position"].abs()
        )

        df["Strategy_Return"] = (
            df["Position"] * df["Market_Return"]
            - df["Turnover"] * self.transaction_cost
        )

        df["Strategy_Equity"] = (
            self.initial_capital *
            (1 + df["Strategy_Return"]).cumprod()
        )

        df["Benchmark_Equity"] = (
            self.initial_capital *
            (1 + df["Market_Return"]).cumprod()
        )

        return df.dropna(subset=["Fast_MA", "Slow_MA"])

    def calculate_metrics(self, results):

        returns = results["Strategy_Return"]
        equity = results["Strategy_Equity"]

        total_return = (
            equity.iloc[-1] / self.initial_capital - 1
        ) * 100

        years = len(results) / 252

        annualized_return = (
            (equity.iloc[-1] / self.initial_capital)
            ** (1 / years) - 1
        ) * 100 if years > 0 else 0

        volatility = returns.std() * np.sqrt(252) * 100

        sharpe = (
            (returns.mean() / returns.std()) * np.sqrt(252)
            if returns.std() > 0 else 0
        )

        drawdown = equity / equity.cummax() - 1
        max_drawdown = drawdown.min() * 100

        winning_days = (
            (returns > 0).sum() / (returns != 0).sum() * 100
            if (returns != 0).sum() > 0 else 0
        )

        benchmark_return = (
            results["Benchmark_Equity"].iloc[-1]
            / self.initial_capital - 1
        ) * 100

        trades = int(results["Turnover"].sum())

        return {
            "Total Return (%)": round(total_return, 2),
            "Annualized Return (%)": round(annualized_return, 2),
            "Benchmark Return (%)": round(benchmark_return, 2),
            "Sharpe Ratio": round(sharpe, 2),
            "Annualized Volatility (%)": round(volatility, 2),
            "Maximum Drawdown (%)": round(max_drawdown, 2),
            "Winning Days (%)": round(winning_days, 2),
            "Position Changes": trades,
            "Ending Capital ($)": round(equity.iloc[-1], 2)
        }


backtester = VeyroBacktester(
    initial_capital=10000,
    transaction_cost=0.001
)

