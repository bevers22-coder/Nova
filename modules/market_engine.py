from __future__ import annotations

import io
import logging
import re
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol
from urllib.error import URLError
from urllib.request import urlopen

import pandas as pd
import yfinance as yf


_LOGGER = logging.getLogger(__name__)
_STOOQ_PERIOD_DAYS = {
    "1d": 2,
    "5d": 7,
    "1mo": 31,
    "3mo": 92,
    "6mo": 183,
    "1y": 366,
    "2y": 732,
    "5y": 1827,
    "10y": 3652,
}


class MarketDataUnavailable(RuntimeError):
    """Raised when every suitable market data provider fails."""


class MarketDataProvider(Protocol):
    name: str

    def download(self, tickers: str | Sequence[str], **kwargs: Any) -> pd.DataFrame:
        ...

    def supports_download(
        self, tickers: str | Sequence[str], kwargs: Mapping[str, Any]
    ) -> bool:
        ...

    def company_info(self, ticker: str) -> dict[str, Any]:
        ...

    def search(self, query: str, max_results: int) -> list[dict[str, Any]]:
        ...


class YahooFinanceProvider:
    name = "Yahoo Finance"

    def __init__(
        self,
        download: Callable[..., pd.DataFrame] | None = None,
        ticker_factory: Callable[[str], Any] | None = None,
        search_factory: Callable[..., Any] | None = None,
    ) -> None:
        self._download = download or yf.download
        self._ticker_factory = ticker_factory or yf.Ticker
        self._search_factory = search_factory or yf.Search

    def supports_download(
        self, tickers: str | Sequence[str], kwargs: Mapping[str, Any]
    ) -> bool:
        return True

    def download(self, tickers: str | Sequence[str], **kwargs: Any) -> pd.DataFrame:
        return self._download(tickers, **kwargs)

    def company_info(self, ticker: str) -> dict[str, Any]:
        return self._ticker_factory(ticker).get_info()

    def search(self, query: str, max_results: int) -> list[dict[str, Any]]:
        return self._search_factory(query, max_results=max_results).quotes or []


class StooqDailyProvider:
    """Free end-of-day fallback; intentionally excludes adjusted and intraday data."""

    name = "Stooq"

    def __init__(self, timeout: float = 10) -> None:
        self.timeout = timeout

    def supports_download(
        self, tickers: str | Sequence[str], kwargs: Mapping[str, Any]
    ) -> bool:
        return (
            isinstance(tickers, str)
            and re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9.-]{0,14}", tickers.strip()
            ) is not None
            and kwargs.get("interval", "1d") == "1d"
            and kwargs.get("auto_adjust", False) is False
            and not tickers.startswith("^")
        )

    def download(self, tickers: str | Sequence[str], **kwargs: Any) -> pd.DataFrame:
        if not self.supports_download(tickers, kwargs):
            raise ValueError(
                "Stooq fallback supports only single-symbol, unadjusted daily history."
            )

        symbol = f"{tickers.strip().lower()}.us"
        request = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
        try:
            with urlopen(request, timeout=self.timeout) as response:
                data = pd.read_csv(io.BytesIO(response.read()))
        except (OSError, URLError, pd.errors.ParserError) as error:
            raise MarketDataUnavailable(
                f"Stooq could not retrieve daily data for {tickers}: {error}"
            ) from error

        required = {"Date", "Open", "High", "Low", "Close", "Volume"}
        if data.empty or not required.issubset(data.columns):
            return pd.DataFrame()

        data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
        data = data.dropna(subset=["Date"]).set_index("Date").sort_index()
        data = data.loc[~data.index.duplicated(keep="last")]

        period = kwargs.get("period")
        if period == "ytd":
            data = data.loc[data.index >= pd.Timestamp(datetime.now().year, 1, 1)]
        elif period in _STOOQ_PERIOD_DAYS:
            cutoff = pd.Timestamp.now().normalize() - timedelta(
                days=_STOOQ_PERIOD_DAYS[period]
            )
            data = data.loc[data.index >= cutoff]

        data.attrs.update(
            source=self.name,
            fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            data_as_of=data.index[-1].isoformat() if not data.empty else None,
            timing="HISTORICAL",
        )
        return data

    def company_info(self, ticker: str) -> dict[str, Any]:
        raise NotImplementedError("Stooq does not provide company fundamentals.")

    def search(self, query: str, max_results: int) -> list[dict[str, Any]]:
        raise NotImplementedError("Stooq does not provide symbol search.")


class MarketDataEngine:
    def __init__(
        self,
        providers: Sequence[MarketDataProvider] | None = None,
        retry_attempts: int = 2,
        backoff_seconds: float = 0.25,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if retry_attempts < 1:
            raise ValueError("retry_attempts must be at least one.")
        if backoff_seconds < 0:
            raise ValueError("backoff_seconds cannot be negative.")
        self.providers = tuple(
            providers
            if providers is not None
            else (YahooFinanceProvider(), StooqDailyProvider())
        )
        if not self.providers:
            raise ValueError("At least one market data provider is required.")
        self.retry_attempts = retry_attempts
        self.backoff_seconds = backoff_seconds
        self._sleep = sleep

    def download(
        self, tickers: str | Sequence[str], **kwargs: Any
    ) -> pd.DataFrame:
        errors: list[str] = []

        for provider in self.providers:
            if not provider.supports_download(tickers, kwargs):
                continue
            for attempt in range(self.retry_attempts):
                try:
                    data = provider.download(tickers, **kwargs)
                    if data is None or data.empty:
                        errors.append(f"{provider.name}: no data returned")
                        break
                    result = data.copy()
                    result.attrs.update(
                        source=provider.name,
                        fetched_at=datetime.now(timezone.utc).isoformat(
                            timespec="seconds"
                        ),
                        data_as_of=(
                            pd.Timestamp(result.index[-1]).isoformat()
                            if len(result.index)
                            else None
                        ),
                        timing="HISTORICAL",
                    )
                    if errors:
                        _LOGGER.warning(
                            "Market data fell back to %s after provider errors: %s",
                            provider.name,
                            "; ".join(errors),
                        )
                        result.attrs["provider_errors"] = tuple(errors)
                    return result
                except Exception as error:
                    errors.append(f"{provider.name}: {error}")
                    if attempt + 1 < self.retry_attempts:
                        self._sleep(self.backoff_seconds * (2**attempt))

        detail = "; ".join(errors) if errors else "no provider supports this request"
        raise MarketDataUnavailable(f"Market data request failed: {detail}")

    def company_info(self, ticker: str) -> dict[str, Any]:
        provider = self.providers[0]
        errors: list[str] = []
        for attempt in range(self.retry_attempts):
            try:
                return provider.company_info(ticker)
            except Exception as error:
                errors.append(f"{provider.name}: {error}")
                if attempt + 1 < self.retry_attempts:
                    self._sleep(self.backoff_seconds * (2**attempt))
        raise MarketDataUnavailable(
            f"Company data is unavailable for {ticker}: {'; '.join(errors)}"
        )

    def search(self, query: str, max_results: int = 8) -> list[dict[str, Any]]:
        provider = self.providers[0]
        errors: list[str] = []
        for attempt in range(self.retry_attempts):
            try:
                return provider.search(query, max_results)
            except Exception as error:
                errors.append(f"{provider.name}: {error}")
                if attempt + 1 < self.retry_attempts:
                    self._sleep(self.backoff_seconds * (2**attempt))
        raise MarketDataUnavailable(
            f"Asset search failed: {'; '.join(errors)}"
        )


class VeyroMarketData:
    def __init__(self, engine: MarketDataEngine | None = None) -> None:
        self.engine = engine or MarketDataEngine()

    def get_stock_data(self, ticker: str, period: str = "5y") -> pd.DataFrame:
        symbol = ticker.upper().strip()
        data = self.engine.download(
            symbol, period=period, auto_adjust=True, progress=False
        )
        if data.empty or "Close" not in data:
            raise ValueError(f"No market data found for {symbol}")

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        data["Returns"] = data["Close"].pct_change()
        data["SMA20"] = data["Close"].rolling(20).mean()
        data["SMA50"] = data["Close"].rolling(50).mean()
        data["SMA200"] = data["Close"].rolling(200).mean()
        data["EMA20"] = data["Close"].ewm(span=20).mean()
        return data


market_engine = MarketDataEngine()
