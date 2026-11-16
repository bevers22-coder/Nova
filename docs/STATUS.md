# NOVA project status

Updated: 2026-11-16

## Phase 1 — Stabilize

**Status: PARTIALLY COMPLETED**

- **COMPLETED:** Repository structure and dependency imports reviewed.
- **COMPLETED:** `app.py` and all project/test Python files compile in the supplied
  Python 3.11 environment.
- **COMPLETED:** The 23 existing `unittest` cases pass.
- **COMPLETED:** All eight Streamlit pages execute without AppTest exceptions;
  Streamlit starts and its health endpoint responds.
- **COMPLETED:** `yfinance` is declared in `requirements.txt`, installed in the
  inspected environment, and importable. The reported missing-module failure
  was not reproduced, so no dependency change was warranted.
- **COMPLETED:** `pytest` is not installed, and it is not needed for the
  standard-library `unittest` suite.
- **NEEDS TESTING:** A clean environment install and browser-level interaction
  with live external feeds were not verified.

## Roadmap

| Phase | Status | Notes |
|---|---|---|
| 1. Stabilize | PARTIALLY COMPLETED | Audit and runtime checks passed; clean install remains unverified. |
| 2. Centralize | PARTIALLY COMPLETED | Shared Yahoo/Stooq provider interface, retries, source metadata, and existing Streamlit TTL caches are wired through the app. Durable market-history storage, complete source badges, and live provider integration checks remain. |
| 3. Backtest core | PARTIALLY COMPLETED | SMA/EMA now use next-open execution when OHLC data is available; commission/slippage, quality checks, risk metrics, SQLite run records, and CSV export are implemented. Additional strategies and robustness analysis remain. |
| 4. Research | PARTIALLY COMPLETED | Existing stock, portfolio, RSS news, and screener pages are present; provider consistency and requested disclosure still need work. |
| 5. Robustness and discovery | NOT STARTED | Walk-forward, Monte Carlo, and parameter search are not implemented. |
| 6. Polish | PARTIALLY COMPLETED | Existing HUD is closest to the Orbital direction; styling is still embedded in `app.py`, and the requested UI package/command palette are not complete. |
| 7. Publish | NOT STARTED | CI, clean-install workflow, and complete limitations documentation remain. |
| 8. Voice and AI | PARKED | Existing browser voice and paid AI tutoring are legacy features; no new assistant work is planned before the earlier phases are complete. |

Phase labels describe the handoff scope, not a claim that existing pages meet
every acceptance criterion. See [ARCHITECTURE.md](ARCHITECTURE.md) and
[ASSIGNMENTS.md](ASSIGNMENTS.md) for boundaries and next work.
