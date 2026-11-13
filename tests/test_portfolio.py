import unittest

import pandas as pd

from modules.portfolio import calculate_portfolio_analytics


class PortfolioAnalyticsTests(unittest.TestCase):

    def test_uses_raw_prices_for_value_and_adjusted_prices_for_returns(self):
        index = pd.to_datetime([
            "2024-01-05",
            "2024-01-08",
            "2025-01-05",
            "2025-01-06",
        ])
        histories = {
            "AAA": pd.DataFrame(
                {
                    "Close": [50, 51, 59, 61],
                    "Adj Close": [50, 51, 59, 60],
                },
                index=index,
            ),
            "BBB": pd.DataFrame(
                {
                    "Close": [25, 26, 29, 30],
                    "Adj Close": [25, 26, 29, 29],
                },
                index=index,
            ),
        }

        analytics = calculate_portfolio_analytics(
            {"AAA": 2, "BBB": 1},
            histories,
        )

        self.assertEqual(analytics.total_value, 152)
        self.assertEqual(analytics.daily_change_amount, 5)
        self.assertAlmostEqual(analytics.daily_change_pct, (152 / 147 - 1) * 100)
        self.assertAlmostEqual(analytics.one_year_return_pct, (149 / 125 - 1) * 100)
        self.assertAlmostEqual(
            analytics.holdings.loc[
                analytics.holdings["Ticker"] == "AAA", "Weight (%)"
            ].iloc[0],
            122 / 152 * 100,
        )

    def test_reports_quote_dates_when_a_holding_uses_a_stale_close(self):
        histories = {
            "AAA": pd.DataFrame(
                {"Close": [10, 11], "Adj Close": [10, 11]},
                index=pd.to_datetime(["2025-01-06", "2025-01-07"]),
            ),
            "BBB": pd.DataFrame(
                {"Close": [20], "Adj Close": [20]},
                index=pd.to_datetime(["2025-01-06"]),
            ),
        }

        analytics = calculate_portfolio_analytics(
            {"AAA": 1, "BBB": 2},
            histories,
        )

        self.assertEqual(analytics.as_of, pd.Timestamp("2025-01-07"))
        stale_holding = analytics.holdings.set_index("Ticker").loc["BBB"]
        self.assertEqual(stale_holding["Quote Date"], "2025-01-06")
        self.assertEqual(stale_holding["Latest Price"], 20)
        self.assertIsNone(analytics.one_year_return_pct)
        self.assertIsNone(analytics.daily_change_amount)

    def test_intraday_quotes_drive_todays_dollar_gain(self):
        daily_index = pd.to_datetime(["2026-11-12", "2026-11-13"])
        daily_history = {
            "AAA": pd.DataFrame(
                {"Close": [100, 96], "Adj Close": [100, 96]},
                index=daily_index,
            ),
            "BBB": pd.DataFrame(
                {"Close": [50, 49], "Adj Close": [50, 49]},
                index=daily_index,
            ),
        }
        intraday_index = pd.DatetimeIndex(
            ["2026-11-13 12:00"],
            tz="America/New_York",
        )
        intraday_history = {
            "AAA": pd.DataFrame({"Close": [105]}, index=intraday_index),
            "BBB": pd.DataFrame({"Close": [45]}, index=intraday_index),
        }

        analytics = calculate_portfolio_analytics(
            {"AAA": 2, "BBB": 1},
            daily_history,
            intraday_history,
        )

        self.assertEqual(analytics.total_value, 255)
        self.assertEqual(analytics.daily_change_amount, 5)
        self.assertAlmostEqual(analytics.daily_change_pct, 5 / 250 * 100)
        self.assertEqual(
            analytics.holdings.set_index("Ticker").loc["AAA", "Day Change ($)"],
            10,
        )
        self.assertEqual(
            analytics.holdings.set_index("Ticker").loc["BBB", "Day Change ($)"],
            -5,
        )

    def test_keeps_valuation_when_adjusted_history_is_unavailable(self):
        index = pd.to_datetime(["2024-01-05", "2025-01-06"])
        histories = {
            "AAA": pd.DataFrame({"Close": [10, 12]}, index=index),
        }

        analytics = calculate_portfolio_analytics({"AAA": 2}, histories)

        self.assertEqual(analytics.total_value, 24)
        self.assertIsNone(analytics.one_year_return_pct)
        self.assertIsNone(analytics.annualized_volatility_pct)
        self.assertIsNone(analytics.max_drawdown_pct)


if __name__ == "__main__":
    unittest.main()
