import yfinance as yf


class FundamentalAnalysis:
    def __init__(self, ticker: str):
        self.ticker = ticker
        self._info = yf.Ticker(ticker).info
        self._balance_sheet = yf.Ticker(ticker).balance_sheet
        self._financials = yf.Ticker(ticker).financials
        self._cashflow = yf.Ticker(ticker).cashflow

    def _get(self, source, key):
        try:
            return float(source.loc[key].iloc[0])
        except (KeyError, IndexError, TypeError):
            return None

    def current_ratio(self):
        assets = self._get(self._balance_sheet, "Current Assets")
        liabilities = self._get(self._balance_sheet, "Current Liabilities")
        if assets and liabilities:
            return assets / liabilities
        return None
