import unittest

import pandas as pd

from modules.market_engine import (
    MarketDataEngine,
    MarketDataUnavailable,
    StooqDailyProvider,
)


class FakeProvider:
    def __init__(self, name, responses, supports=True):
        self.name = name
        self.responses = list(responses)
        self.supports = supports
        self.calls = 0

    def supports_download(self, tickers, kwargs):
        return self.supports

    def download(self, tickers, **kwargs):
        self.calls += 1
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def company_info(self, ticker):
        return {}

    def search(self, query, max_results):
        return []


class MarketDataEngineTests(unittest.TestCase):
    def test_retries_primary_then_marks_successful_fallback_source(self):
        fallback_data = pd.DataFrame(
            {"Close": [10.0]}, index=pd.to_datetime(["2025-01-02"])
        )
        primary = FakeProvider(
            "Yahoo Finance",
            [TimeoutError("temporary outage"), TimeoutError("still unavailable")],
        )
        fallback = FakeProvider("Stooq", [fallback_data])
        engine = MarketDataEngine(
            [primary, fallback], retry_attempts=2, sleep=lambda _: None
        )

        result = engine.download("AAPL", period="1y", auto_adjust=False)

        self.assertEqual(primary.calls, 2)
        self.assertEqual(fallback.calls, 1)
        self.assertEqual(result.attrs["source"], "Stooq")
        self.assertEqual(result.attrs["timing"], "HISTORICAL")
        self.assertEqual(len(result.attrs["provider_errors"]), 2)

    def test_primary_failure_is_explicit_when_no_fallback_supports_request(self):
        provider = FakeProvider("Yahoo Finance", [ConnectionError("offline")])
        fallback = FakeProvider("Stooq", [], supports=False)
        engine = MarketDataEngine(
            [provider, fallback], retry_attempts=1, sleep=lambda _: None
        )

        with self.assertRaisesRegex(MarketDataUnavailable, "offline"):
            engine.download("AAPL", interval="1m", auto_adjust=False)
        self.assertEqual(fallback.calls, 0)

    def test_empty_provider_responses_are_not_reported_as_success(self):
        primary = FakeProvider("Yahoo Finance", [pd.DataFrame()])
        fallback = FakeProvider("Stooq", [], supports=False)
        engine = MarketDataEngine(
            [primary, fallback], retry_attempts=1, sleep=lambda _: None
        )

        with self.assertRaisesRegex(MarketDataUnavailable, "no data returned"):
            engine.download("AAPL", auto_adjust=True)

    def test_stooq_is_not_used_for_adjusted_intraday_or_multi_symbol_data(self):
        provider = StooqDailyProvider()

        self.assertTrue(
            provider.supports_download("AAPL", {"period": "1y", "auto_adjust": False})
        )
        self.assertFalse(
            provider.supports_download("AAPL", {"period": "1y", "auto_adjust": True})
        )
        self.assertFalse(
            provider.supports_download(
                "AAPL", {"period": "1d", "interval": "1m", "auto_adjust": False}
            )
        )
        self.assertFalse(
            provider.supports_download(
                ["AAPL", "MSFT"], {"period": "1y", "auto_adjust": False}
            )
        )
        self.assertFalse(
            provider.supports_download(
                "AAPL&x=1", {"period": "1y", "auto_adjust": False}
            )
        )

    def test_provider_settings_are_validated(self):
        with self.assertRaises(ValueError):
            MarketDataEngine(retry_attempts=0)
        with self.assertRaises(ValueError):
            MarketDataEngine(backoff_seconds=-0.1)


if __name__ == "__main__":
    unittest.main()
