import unittest

import pandas as pd

from modules.screener import apply_screener_filters


class ScreenerFilterTests(unittest.TestCase):
    def setUp(self):
        self.results = pd.DataFrame(
            {
                "Ticker": ["AAA", "BBB", "CCC"],
                "Market Cap ($B)": [20, 2, 8],
                "P/E": [18, 12, None],
                "Sector": ["Technology", "Healthcare", "Technology"],
                "Industry": ["Software", "Biotech", "Hardware"],
            }
        )

    def test_multiple_numeric_and_text_filters_are_applied_together(self):
        filtered = apply_screener_filters(
            self.results,
            [
                {"field": "Market Cap ($B)", "operator": "≥", "lower": 5},
                {"field": "P/E", "operator": "Between", "lower": 15, "upper": 20},
            ],
            sector_contains="tech",
            industry_contains="soft",
        )
        self.assertEqual(filtered["Ticker"].tolist(), ["AAA"])

    def test_missing_values_do_not_match_an_active_filter(self):
        filtered = apply_screener_filters(
            self.results,
            [{"field": "P/E", "operator": "≤", "lower": 20}],
        )
        self.assertEqual(filtered["Ticker"].tolist(), ["AAA", "BBB"])

    def test_unknown_metric_and_operator_are_rejected(self):
        with self.assertRaises(ValueError):
            apply_screener_filters(
                self.results,
                [{"field": "Unknown", "operator": "≥", "lower": 0}],
            )
        with self.assertRaises(ValueError):
            apply_screener_filters(
                self.results,
                [{"field": "P/E", "operator": "=", "lower": 0}],
            )


if __name__ == "__main__":
    unittest.main()
