import yfinance as yf
import pandas as pd


class VeyroPortfolio:

    def __init__(self, holdings):
        self.holdings = holdings
        self.prices = {}

    def retrieve_prices(self):

        for ticker in self.holdings:

            try:
                history = yf.Ticker(ticker).history(
                    period="5d"
                )

                if history.empty:
                    continue

                self.prices[ticker] = float(
                    history["Close"].dropna().iloc[-1]
                )

            except Exception as error:
                print(f"{ticker} data error: {error}")

        return self.prices

    def portfolio_report(self):

        rows = []

        for ticker, holding in self.holdings.items():

            if ticker not in self.prices:
                continue

            shares = holding["shares"]
            price = self.prices[ticker]
            value = shares * price

            rows.append({
                "Ticker": ticker,
                "Shares": shares,
                "Market Price": round(price, 2),
                "Market Value": round(value, 2)
            })

        report = pd.DataFrame(rows)

        if report.empty:
            return None

        total_value = report["Market Value"].sum()

        report["Portfolio Weight (%)"] = (
            report["Market Value"] / total_value * 100
        ).round(2)

        return report

