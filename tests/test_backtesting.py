import unittest

import pandas as pd

from modules.backtesting import VeyroBacktester


class VeyroBacktesterTests(unittest.TestCase):

    def test_strategy_uses_previous_session_signal_and_charges_cost(self):
        index = pd.date_range("2025-01-01", periods=8, freq="D")
        prices = pd.DataFrame(
            {"Close": [10, 10, 10, 10, 20, 22, 22, 20]},
            index=index
        )
        backtester = VeyroBacktester(
            initial_capital=1000,
            transaction_cost=0.001
        )

        results = backtester.moving_average_strategy(
            prices, fast=2, slow=3
        )

        self.assertEqual(results.loc[index[4], "Position"], 0)
        self.assertEqual(results.loc[index[5], "Position"], 1)
        self.assertAlmostEqual(results.loc[index[5], "Strategy_Return"], 0.099)
        self.assertEqual(len(results), len(prices))

    def test_invalid_window_and_capital_settings_are_rejected(self):
        with self.assertRaises(ValueError):
            VeyroBacktester(initial_capital=0)

        with self.assertRaises(ValueError):
            VeyroBacktester(transaction_cost=1)

        backtester = VeyroBacktester()
        with self.assertRaises(ValueError):
            backtester.moving_average_strategy(
                pd.DataFrame({"Close": [10, 11, 12]}),
                fast=3,
                slow=2
            )

    def test_ema_mode_uses_exponential_averages_and_rejects_unknown_methods(self):
        data = pd.DataFrame({"Close": [10, 12, 9, 14, 11, 17, 15, 20]})
        backtester = VeyroBacktester()
        results = backtester.moving_average_strategy(
            data, fast=2, slow=4, method="EMA"
        )
        expected_fast = data["Close"].ewm(
            span=2, adjust=False, min_periods=2
        ).mean()
        self.assertAlmostEqual(results["Fast_MA"].iloc[-1], expected_fast.iloc[-1])
        with self.assertRaises(ValueError):
            backtester.moving_average_strategy(data, fast=2, slow=4, method="VWAP")


if __name__ == "__main__":
    unittest.main()
