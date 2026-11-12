import pandas as pd
import numpy as np


class VeyroStrategyLab:

    def __init__(self, initial_capital=10000, transaction_cost=0.001):
        self.initial_capital = initial_capital
        self.transaction_cost = transaction_cost
        self.results = {}

    def calculate_rsi(self, prices, period=14):
        delta = prices.diff()

        gains = delta.clip(lower=0)
        losses = -delta.clip(upper=0)

        avg_gain = gains.ewm(
            alpha=1/period, min_periods=period, adjust=False
        ).mean()

        avg_loss = losses.ewm(
            alpha=1/period, min_periods=period, adjust=False
        ).mean()

        rs = avg_gain / avg_loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    def run_strategy(self, prices, strategy):
        df = pd.DataFrame({"Close": prices}).dropna().copy()

        if strategy == "SMA 20/50":
            fast = df["Close"].rolling(20).mean()
            slow = df["Close"].rolling(50).mean()
            signal = (fast > slow).astype(int)

        elif strategy == "SMA 50/200":
            fast = df["Close"].rolling(50).mean()
            slow = df["Close"].rolling(200).mean()
            signal = (fast > slow).astype(int)

        elif strategy == "RSI 14":
            rsi = self.calculate_rsi(df["Close"], 14)
            signal_values = []
            position = 0

            for value in rsi:
                if pd.isna(value):
                    position = 0
                elif value < 30:
                    position = 1
                elif value > 70:
                    position = 0

                signal_values.append(position)

            signal = pd.Series(signal_values, index=df.index)

        else:
            raise ValueError("Unknown strategy")

        df["Position"] = signal.shift(1).fillna(0)
        df["Market_Return"] = df["Close"].pct_change().fillna(0)

        df["Turnover"] = (
            df["Position"].diff().abs()
        ).fillna(df["Position"].abs())

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

    def calculate_metrics(self, df):
        returns = df["Strategy_Return"]
        equity = df["Strategy_Equity"]

        years = len(df) / 252

        total_return = (
            equity.iloc[-1] / self.initial_capital - 1
        ) * 100

        annualized_return = (
            ((equity.iloc[-1] / self.initial_capital)
             ** (1 / years) - 1) * 100
            if years > 0 and equity.iloc[-1] > 0 else np.nan
        )

        volatility = returns.std() * np.sqrt(252) * 100

        sharpe = (
            returns.mean() / returns.std() * np.sqrt(252)
            if returns.std() > 0 else np.nan
        )

        drawdown = equity / equity.cummax() - 1

        benchmark_return = (
            df["Benchmark_Equity"].iloc[-1]
            / self.initial_capital - 1
        ) * 100

        return {
            "Total Return (%)": round(total_return, 2),
            "Annualized Return (%)": round(annualized_return, 2),
            "Benchmark Return (%)": round(benchmark_return, 2),
            "Sharpe Ratio": round(sharpe, 2),
            "Volatility (%)": round(volatility, 2),
            "Maximum Drawdown (%)": round(drawdown.min() * 100, 2),
            "Position Changes": int(df["Turnover"].sum()),
            "Ending Capital ($)": round(equity.iloc[-1], 2)
        }

    def research_stock(self, ticker, prices):
        strategies = ["SMA 20/50", "SMA 50/200", "RSI 14"]
        stock_results = []

        for strategy in strategies:
            tested = self.run_strategy(prices, strategy)
            metrics = self.calculate_metrics(tested)

            stock_results.append({
                "Ticker": ticker,
                "Strategy": strategy,
                **metrics
            })

        buy_hold = pd.DataFrame({"Close": prices}).dropna().copy()
        buy_hold_return = buy_hold["Close"].pct_change().fillna(0)

        buy_hold_equity = (
            self.initial_capital * (1 + buy_hold_return).cumprod()
        )

        stock_results.append({
            "Ticker": ticker,
            "Strategy": "Buy & Hold",
            "Total Return (%)": round(
                (buy_hold_equity.iloc[-1] /
                 self.initial_capital - 1) * 100, 2
            ),
            "Annualized Return (%)": np.nan,
            "Benchmark Return (%)": round(
                (buy_hold_equity.iloc[-1] /
                 self.initial_capital - 1) * 100, 2
            ),
            "Sharpe Ratio": np.nan,
            "Volatility (%)": np.nan,
            "Maximum Drawdown (%)": round(
                (buy_hold_equity / buy_hold_equity.cummax() - 1)
                .min() * 100, 2
            ),
            "Position Changes": 0,
            "Ending Capital ($)": round(
                buy_hold_equity.iloc[-1], 2
            )
        })

        return stock_results


strategy_lab = VeyroStrategyLab()

