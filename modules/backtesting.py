import numpy as np
import pandas as pd


BACKTEST_ENGINE_VERSION = "2"


class VeyroBacktester:

    def __init__(
        self, initial_capital=10000, transaction_cost=0.001, slippage_cost=0.0
    ):
        if initial_capital <= 0:
            raise ValueError("Initial capital must be greater than zero.")
        if not 0 <= transaction_cost < 1:
            raise ValueError("Transaction cost must be between 0 and 1.")
        if not 0 <= slippage_cost < 1:
            raise ValueError("Slippage cost must be between 0 and 1.")
        if transaction_cost + slippage_cost >= 1:
            raise ValueError("Combined transaction and slippage cost must be below 1.")
        self.initial_capital = initial_capital
        self.transaction_cost = transaction_cost
        self.slippage_cost = slippage_cost

    def moving_average_strategy(self, data, fast=20, slow=50, method="SMA"):

        if fast < 1 or slow <= fast:
            raise ValueError("Moving-average windows must satisfy 1 <= fast < slow.")
        if method.upper() not in {"SMA", "EMA"}:
            raise ValueError("Moving-average method must be SMA or EMA.")
        if "Close" not in data or data["Close"].dropna().empty:
            raise ValueError("Historical data must contain closing prices.")
        if data.index.has_duplicates:
            raise ValueError("Historical data contains duplicate session dates.")
        if not data.index.is_monotonic_increasing:
            raise ValueError("Historical data must be ordered by session date.")

        df = data.copy()
        df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
        if df.empty or df["Close"].isna().any():
            raise ValueError("Closing prices must be present for every supplied session.")
        if not np.isfinite(df["Close"]).all() or (df["Close"] <= 0).any():
            raise ValueError("Closing prices must be finite and greater than zero.")

        has_open_prices = "Open" in df.columns
        if has_open_prices:
            df["Open"] = pd.to_numeric(df["Open"], errors="coerce")
            if df["Open"].isna().any():
                raise ValueError("Opening prices must be present for every supplied session.")
            if not np.isfinite(df["Open"]).all() or (df["Open"] <= 0).any():
                raise ValueError("Opening prices must be finite and greater than zero.")

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

        if has_open_prices:
            df["Overnight_Return"] = (
                df["Open"] / df["Close"].shift(1) - 1
            ).replace([np.inf, -np.inf], np.nan).fillna(0)
            df["Intraday_Return"] = (
                df["Close"] / df["Open"] - 1
            ).replace([np.inf, -np.inf], np.nan).fillna(0)
            previous_position = df["Position"].shift(1).fillna(0)
            gross_return = (
                (1 + previous_position * df["Overnight_Return"])
                * (1 + df["Position"] * df["Intraday_Return"])
                - 1
            )
        else:
            gross_return = df["Position"] * df["Market_Return"]

        df["Strategy_Return"] = (
            gross_return
            - df["Turnover"] * (self.transaction_cost + self.slippage_cost)
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
        if equity.empty or not np.isfinite(equity).all():
            raise ValueError("Backtest equity must contain finite values.")

        total_return = (
            equity.iloc[-1] / self.initial_capital - 1
        ) * 100

        if isinstance(results.index, pd.DatetimeIndex) and len(results) > 1:
            years = (results.index[-1] - results.index[0]).days / 365.25
        else:
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
        drawdown_duration = 0
        current_drawdown_duration = 0
        for below_peak in drawdown < 0:
            current_drawdown_duration = (
                current_drawdown_duration + 1 if below_peak else 0
            )
            drawdown_duration = max(
                drawdown_duration, current_drawdown_duration
            )

        winning_days = (
            (returns > 0).sum() / (returns != 0).sum() * 100
            if (returns != 0).sum() > 0 else 0
        )
        downside_deviation = np.sqrt(np.square(returns.clip(upper=0)).mean())
        sortino = (
            returns.mean() / downside_deviation * np.sqrt(252)
            if downside_deviation > 0 else np.nan
        )
        calmar = (
            annualized_return / abs(max_drawdown)
            if max_drawdown < 0 and np.isfinite(annualized_return) else np.nan
        )
        gains = returns[returns > 0].sum()
        losses = -returns[returns < 0].sum()
        profit_factor = gains / losses if losses > 0 else np.nan
        benchmark_returns = results["Market_Return"]
        benchmark_variance = benchmark_returns.var()
        beta = (
            returns.cov(benchmark_returns) / benchmark_variance
            if benchmark_variance > 0 else np.nan
        )
        alpha = (
            (returns.mean() - beta * benchmark_returns.mean()) * 252 * 100
            if np.isfinite(beta) else np.nan
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
            "Sortino Ratio": round(sortino, 2) if np.isfinite(sortino) else np.nan,
            "Calmar Ratio": round(calmar, 2) if np.isfinite(calmar) else np.nan,
            "Annualized Volatility (%)": round(volatility, 2),
            "Maximum Drawdown (%)": round(max_drawdown, 2),
            "Maximum Drawdown Duration (sessions)": drawdown_duration,
            "Winning Days (%)": round(winning_days, 2),
            "Profit Factor": round(profit_factor, 2) if np.isfinite(profit_factor) else np.nan,
            "Exposure (%)": round(results["Position"].mean() * 100, 2),
            "Turnover": round(float(results["Turnover"].sum()), 2),
            "Alpha (%)": round(alpha, 2) if np.isfinite(alpha) else np.nan,
            "Beta": round(beta, 2) if np.isfinite(beta) else np.nan,
            "Position Changes": trades,
            "Ending Capital ($)": round(equity.iloc[-1], 2)
        }


backtester = VeyroBacktester(
    initial_capital=10000,
    transaction_cost=0.001
)

