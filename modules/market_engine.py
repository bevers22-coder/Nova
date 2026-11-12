import yfinance as yf
import pandas as pd
import numpy as np


class VeyroMarketData:

    def get_stock_data(self, ticker, period="5y"):

        ticker = ticker.upper().strip()

        data = yf.download(
            ticker,
            period=period,
            auto_adjust=True,
            progress=False
        )

        if data is None or data.empty:
            raise ValueError(f"No market data found for {ticker}")

        # Handle newer yfinance MultiIndex columns
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        data["Returns"] = data["Close"].pct_change()
        data["SMA20"] = data["Close"].rolling(20).mean()
        data["SMA50"] = data["Close"].rolling(50).mean()
        data["SMA200"] = data["Close"].rolling(200).mean()
        data["EMA20"] = data["Close"].ewm(span=20).mean()

        return data


market_engine = VeyroMarketData()

