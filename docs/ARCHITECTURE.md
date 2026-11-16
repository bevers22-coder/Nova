# NOVA architecture

## Current shape

- `app.py` is the Streamlit entry point and currently owns page routing,
  presentation, cached fetch helpers, and much of the CSS.
- `modules/storage.py` owns private local SQLite persistence for holdings,
  settings, the watchlist, and saved study documents.
- `modules/market_engine.py` is the shared boundary for market downloads,
  company fundamentals, and symbol search.
- `modules/backtesting.py` validates input prices, shifts close-based signals to
  the next session, and simulates separately charged commission and slippage.
- `modules/storage.py` persists backtest parameters, metric summaries, provider,
  dates, and engine version alongside other local app data.
- Other `modules/` files contain portfolio analytics, screening, backtesting,
  exports, document handling, and voice command parsing.
- `tests/` uses `unittest`; run it with `python -m unittest discover -v`.

## Market data boundary

`MarketDataEngine` routes downloads to providers and retries provider errors
with bounded exponential backoff. Yahoo Finance (`yfinance`) is the primary
source. Stooq is a free fallback only for one-symbol, unadjusted daily history;
it is deliberately excluded from adjusted-price, intraday, index-symbol, and
multi-symbol requests. The fallback's limits avoid treating raw close as
dividend-adjusted performance or pretending end-of-day data is real time.

Successful downloads carry `source`, `fetched_at`, `data_as_of`, and `timing`
in Pandas `DataFrame.attrs`. Existing Streamlit `st.cache_data` decorators are
the current in-process TTL cache. Durable market-history caching, common
provider-status presentation, and refresh/error status remain future work.

Provider errors are retried and then raised as `MarketDataUnavailable` if no
eligible provider succeeds. A successful fallback records primary-provider
errors in metadata and the application logger.

## Backtest caveats

- The current lab contains SMA and EMA crossovers, not the full requested
  strategy plug-in catalog or no-code builder.
- When OHLC history is available, a signal formed at a close is applied at the
  next session's open. Open-to-close and held-position overnight returns are
  modeled separately. A close-only input retains the legacy close-to-close
  simulation.
- The engine assumes fully invested long/cash exposure. Shorting, multi-asset
  rebalancing, stops, take-profit rules, and point-in-time fundamentals are not
  implemented.
- Run records capture data dates, provider, parameters, metrics, and engine
  version; they do not archive a copy of every provider's source data.

## Financial-data caveats

- Free market feeds may be delayed, incomplete, rate-limited, or unavailable.
- Stooq fallback data is end-of-day and not dividend-adjusted.
- Yahoo Finance access is unofficial and may change or fail.
- Historical portfolio analytics apply current holdings to available history;
  they do not represent actual account performance.
- The current backtester has limited strategies and cost assumptions; it is not
  the reproducible, point-in-time research engine in the roadmap.
- NOVA does not connect to a brokerage or place orders.
- Historical results do not guarantee future performance.

## Design and operational constraints

- Python and Streamlit remain the application stack.
- New functionality should use free/open-source providers and dependencies.
- No paid provider, AI model, or hosted service should be added without
  discussing its cost and a free alternative first.
- API keys and passwords belong in environment variables or Streamlit secrets,
  never in source control.
- Preserve explicit unavailability and data provenance; do not invent missing
  values or relabel historical data as live.
- Extract shared styling to `ui/theme.py` and `ui/components.py` during the
  polish phase, after the visual direction is confirmed. The current default
  direction is Orbital.
