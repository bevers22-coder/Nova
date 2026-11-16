# NOVA implementation assignments

Assignments are executed in sequence; review their diffs and full test output
before merging or starting conflicting work. Keep one owner per file and one
task branch per implementation assignment.

## A1 — Stabilize and document

- **Inspect:** `README.md`, `requirements.txt`, `.devcontainer/devcontainer.json`,
  `app.py`, `modules/`, `tests/`.
- **Modify:** directly relevant dependency/setup/docs files only.
- **Preserve:** all eight current pages, current portfolio persistence, public
  mode warning, and existing behavior.
- **Add:** reproducible setup and baseline status/architecture docs.
- **Errors:** report missing imports and failed page execution; don't hide a
  missing package behind an optional import.
- **Tests:** Python compilation, `python -m unittest discover -v`, all-page
  Streamlit AppTest, server health, and clean install when available.
- **Acceptance:** requirements are truthful, baseline is recorded, and output
  includes the diff and full test results.
- **Do not touch:** strategy behavior, provider credentials, or deploy settings
  without a demonstrated blocker.

**Result:** `yfinance` was already declared and importable; the suspected error
was not reproduced. Compilation, 23 tests, eight AppTest pages, and the health
endpoint passed. `pytest` is not installed and is not required by the existing
`unittest` suite. Clean install and browser interactions remain unverified.

## A2 — Central market data

- **Inspect:** `modules/market_engine.py`, market-fetch functions in `app.py`,
  portfolio fetches in `modules/portfolio.py`, and relevant UI source labels.
- **Modify:** the shared provider engine and call sites necessary to remove
  direct provider access from UI code; add focused market-engine tests.
- **Preserve:** current cache TTLs and DataFrame shapes consumed by pages.
- **Add:** free-source fallback with strict adjusted/intraday restrictions,
  bounded retries, and source/retrieval/data-date metadata.
- **Errors:** expose provider failures when no suitable source succeeds and log
  degraded fallback use.
- **Tests:** retry and fallback routing, provider metadata, constraints on
  adjusted/intraday/multi-symbol requests, full existing suite, and all pages.
- **Acceptance:** no `yfinance` calls remain in `app.py`; fallback never supplies
  raw daily close to adjusted-price or intraday calculations.
- **Do not touch:** broker integration, paid providers, or backtest semantics.

**Result:** shared provider routing, bounded retries, constrained Stooq fallback,
source metadata, provider error reporting, and routing for portfolio fetches are
implemented. The full unit suite and all eight page smoke tests pass. Persistent
market-history storage, all-panel provenance badges, and live Stooq integration
remain unverified.

## A3 — Reproducible backtest core

- **Inspect:** `modules/backtesting.py`, `tests/test_backtesting.py`, current
  Backtesting Lab rendering in `app.py`, and the data engine.
- **Modify:** backtest engine/tests and the minimal dependent UI.
- **Preserve:** current defaults and clearly labeled historical research-only
  behavior.
- **Add:** close-signal/open-next-session execution, explicit commission and
  slippage, adjusted-price data validation, reproducibility record, caveats, and
  core risk metrics.
- **Errors:** reject invalid, duplicate, non-positive, or insufficient prices
  with actionable messages.
- **Tests:** hand-checked 10-session case, no-look-ahead, costs, and an
  independent calculation.
- **Acceptance:** deterministic run details and documented limitations appear
  with every result.
- **Do not touch:** order execution, paid feeds, or unrelated portfolio UX.

**Result:** SMA/EMA calculations use next-open execution when opening prices are
available, input-price validation is stricter, commission and slippage are
separate, core risk metrics are added, and parameter/metric run records persist
in SQLite. The backtest page shows provider/date/version details, saved run
history, caveats, and CSV export. Focused tests, compilation, and the full test
suite passed. The full requested strategy catalog, OOS/walk-forward, optimizer,
Monte Carlo, multi-asset engine, and durable source-data snapshots remain.

## A4 — Research modules

- **Inspect:** stock/portfolio/screener pages, `modules/portfolio.py`, RSS
  parsing, and current provider disclosures.
- **Modify:** those modules and focused tests only.
- **Preserve:** unknown cost basis and missing provider metrics as unknown.
- **Add:** common source/date/timing disclosures; verified free RSS and official
  embeddable streams only.
- **Errors:** show source-specific unavailable states rather than fabricated
  or silently incomplete results.
- **Tests:** missing-data behavior, timestamp/source labeling, RSS parse edge
  cases, and page renders.
- **Acceptance:** no panel calls unverified data "real time"; external embeds
  fail visibly and safely.
- **Do not touch:** unauthorized rebroadcasts or brokerage integrations.

## A5 — Robustness and discovery

- **Inspect:** A3 backtest outputs and current screener state/persistence.
- **Modify:** backtest robustness functions, optimizer, screener and their tests.
- **Preserve:** risk-adjusted ranking and saved screen/run data.
- **Add:** in/out-of-sample, walk-forward, parameter heatmaps, Monte Carlo, and
  clearly counted trials.
- **Errors:** bound compute, validate inputs, and disclose insufficient data.
- **Tests:** deterministic seeded simulations, split boundaries, and a known
  parameter ranking.
- **Acceptance:** no result is ranked solely by raw return; trial count and
  sample boundaries are explicit.
- **Do not touch:** paid optimization services or hidden network jobs.

## A6 — HUD and reports

- **Inspect:** existing CSS/UI, Streamlit capabilities, and accessibility
  preferences.
- **Modify:** `ui/theme.py`, `ui/components.py`, `.streamlit/config.toml`, and
  direct UI call sites.
- **Preserve:** current page behavior and legible data tables/charts.
- **Add:** Orbital HUD direction, reduced-motion support, shared Plotly theme,
  command-palette ticker search, and report exports.
- **Errors:** unsupported browser features degrade without blocking core
  research.
- **Tests:** CSS/theme helpers, report output, and all page renders; manually
  verify responsive layout and reduced motion.
- **Acceptance:** styles live in the shared UI package/config, not duplicated
  page markup; reports state their data date and caveats.
- **Do not touch:** backend migrations or add external fonts as a runtime
  dependency.

## A7 — Publish readiness

- **Inspect:** all tests, install instructions, secrets handling, and deployment
  configuration.
- **Modify:** CI, README, and limitations docs.
- **Preserve:** free/open-source operation and no-secret-in-git guarantee.
- **Add:** clean-install CI and reproducible test commands.
- **Errors:** CI must fail on install, tests, compile, or import errors.
- **Tests:** fresh environment install, full test suite, app smoke test, secret
  scanning/config review.
- **Acceptance:** documented supported setup and limitations match verified
  behavior; no claim that deployment succeeded without deployment evidence.
- **Do not touch:** publish secrets or trigger a paid deployment.
