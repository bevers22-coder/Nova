# Nova

Nova is a Streamlit market-research dashboard with an animated sci-fi HUD.

The command center includes Naperville, Illinois weather, Chicago-area and
market headlines on request, and click-to-start browser voice controls. Its
control deck replaces the sidebar, and voice commands can navigate pages or
enter a ticker. Animated signal displays and a scrolling headline ticker add
live motion. Weather and news load only when requested, so an unavailable
external feed cannot hold up the initial dashboard. The market screener
compares returns, trend levels, trading volume, volatility, drawdown, ATR, and
beta versus SPY.

The backtesting lab compares a configurable long/cash moving-average rule with
buy-and-hold using historical data and estimated transaction costs; it does not
place trades.

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

## Deploy with Streamlit Community Cloud

Connect this GitHub repository in Streamlit Community Cloud and set the
deployment entry point to `app.py`. Streamlit installs the packages listed in
`requirements.txt` during deployment. The voice component is included in
`voice_component/` and microphone access requires a supported browser and
permission from the user.