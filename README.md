# Nova

Nova is a Streamlit market-research dashboard with an animated sci-fi HUD.

The command center includes Naperville, Illinois weather, Chicago-area and
market headlines, and click-to-start browser voice controls. Voice commands
can open dashboard sections or enter a ticker for lookup. The market screener
compares returns, trend levels, trading volume, volatility, drawdown, ATR, and
beta versus SPY across a user-provided ticker list.

Market and news data require an internet connection. Voice recognition depends
on browser support and microphone permission. The dashboard is for research
only and does not execute trades.

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