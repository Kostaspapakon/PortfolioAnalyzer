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

    def debt_to_equity(self):
        total_debt = self._get(self._balance_sheet, "Total Debt")
        equity = self._get(self._balance_sheet, "Stockholders Equity")
        if total_debt and equity:
            return total_debt / equity
        return None
    
    def profit_margin(self):
        net_income = self._get(self._financials, "Net Income")
        revenue = self._get(self._financials, "Total Revenue")
        if net_income and revenue:
            return net_income / revenue
        return None
  
    def revenue_growth(self):
        try:
            revenue_now = self._get(self._financials, "Total Revenue")
            revenue_prev = float(self._financials.loc["Total Revenue"].iloc[1])
            if revenue_now and revenue_prev:
                return (revenue_now - revenue_prev) / revenue_prev
        except (KeyError, IndexError, TypeError):
            return None
        return None
    
    def eps(self):
        return self._info.get("trailingEps")
    
    def pe_ratio(self):
        return self._info.get("trailingPE")
    
    def pb_ratio(self):
        return self._info.get("priceToBook")

    def free_cash_flow(self):
        return self._get(self._cashflow, "Free Cash Flow")
    