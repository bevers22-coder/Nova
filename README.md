# Nova

Nova is a Streamlit market-research dashboard with an animated sci-fi HUD.

The command center includes Naperville, Illinois weather, Chicago-area and
market headlines on request, and click-to-start browser voice controls. Its
control deck replaces the sidebar, and voice commands can navigate pages or
enter a ticker. Animated signal displays and a scrolling headline ticker add
live motion. Weather and news load only when requested, so an unavailable
external feed cannot hold up the initial dashboard. The market screener
combines price history and Yahoo Finance company-profile fundamentals (including
market cap, valuation, growth, dividends, margins, leverage, and returns on
equity/assets) with technical filters. Screening configurations persist in the
private local database. Provider fields may be missing or delayed; active filters
exclude rows whose required values are unavailable.

The backtesting lab compares a configurable long/cash moving-average rule with
buy-and-hold using historical data and estimated transaction costs; it does not
place trades.

The private portfolio is preloaded with NVDA (1), ORCL (5), PLTR (1), MRVL (2),
FTNT (1), ABBV (1), MP (1), and PG (12). No purchase prices or cost basis are
assumed. Holdings, optional per-share cost basis, watchlist, saved screener
configurations, settings, and saved study documents persist in a local SQLite
database with owner-only file permissions. Without `NOVA_ACCESS_PASSWORD`,
the app runs in public mode and shows a warning: anyone who can reach the app
may view this data. Configure a password to restrict access before deploying
privately. Today's P&L uses the latest
available intraday quote when available and shows both dollar and percentage
changes; provider quotes may be delayed. Historical estimates use
dividend-adjusted prices and apply current share counts to past prices, so they
are not actual account performance. Unavailable holdings are identified rather
than silently included in totals.

Study Studio is an AI-powered tutoring interface for explanations, practice,
planning, and draft feedback. It does not generate complete graded submissions.
To enable it on Streamlit Community Cloud, add these values under **App
settings → Secrets**:

```toml
OPENAI_API_KEY = "your-key"
OPENAI_MODEL = "gpt-4o-mini"
```

Never commit API keys to the repository. Study questions are sent to the
configured AI provider when submitted and may incur provider usage charges.
Browser speech recognition and speech playback depend on browser support and
microphone permission.

Market and news data require an internet connection. The dashboard is for
research only and does not execute trades.

The HUD artwork is drawn with CSS; no external background image is required.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

For a password-protected deployment, set `NOVA_ACCESS_PASSWORD` in the server
environment (or Streamlit secrets). Without it, Nova opens in public mode.

## Deploy with Streamlit Community Cloud

Connect this GitHub repository in Streamlit Community Cloud and set the
deployment entry point to `app.py`. Add `NOVA_ACCESS_PASSWORD` under **App
settings → Secrets** to require a password; otherwise, the app is publicly
accessible and displays a data-visibility warning. Streamlit installs the
packages listed in `requirements.txt` during deployment. The voice component
is included in `voice_component/` and microphone access requires a supported
browser and permission from the user.