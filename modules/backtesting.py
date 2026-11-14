import numpy as np
import pandas as pd


class VeyroBacktester:

    def __init__(self, initial_capital=10000, transaction_cost=0.001):
        if initial_capital <= 0:
            raise ValueError("Initial capital must be greater than zero.")
        if not 0 <= transaction_cost < 1:
            raise ValueError("Transaction cost must be between 0 and 1.")
        self.initial_capital = initial_capital
        self.transaction_cost = transaction_cost

    def moving_average_strategy(self, data, fast=20, slow=50, method="SMA"):

        if fast < 1 or slow <= fast:
            raise ValueError("Moving-average windows must satisfy 1 <= fast < slow.")
        if method.upper() not in {"SMA", "EMA"}:
            raise ValueError("Moving-average method must be SMA or EMA.")
        if "Close" not in data or data["Close"].dropna().empty:
            raise ValueError("Historical data must contain closing prices.")

        df = data.copy()
        df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
        df = df.dropna(subset=["Close"])
        if df.empty:
            raise ValueError("Historical data contains no usable closing prices.")

        if method.upper() == "EMA":
            df["Fast_MA"] = df["Close"].ewm(
                span=fast, adjust=False, min_periods=fast
            ).mean()
            df["Slow_MA"] = df["Close"].ewm(
                span=slow, adjust=False, min_periods=slow
            ).mean()
        else:
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

        return df

    def calculate_metrics(self, results):

        if results.empty or "Strategy_Return" not in results:
            raise ValueError("Backtest results are empty or incomplete.")

        returns = results["Strategy_Return"]
        equity = results["Strategy_Equity"]

        total_return = (
            equity.iloc[-1] / self.initial_capital - 1
        ) * 100

        years = len(results) / 252

        annualized_return = (
            (equity.iloc[-1] / self.initial_capital)
            ** (1 / years) - 1
        ) * 100 if years > 0 and equity.iloc[-1] > 0 else np.nan

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

