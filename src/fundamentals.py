import yfinance as yf
from datetime import datetime


class FundamentalAnalysis:
    def __init__(self, ticker: str):
        self.ticker = ticker
        self._yf = yf.Ticker(ticker)
        self._info = self._yf.info
        self._balance_sheet = self._yf.balance_sheet
        self._financials = self._yf.financials
        self._cashflow = self._yf.cashflow

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

    def get_news(self, n=6):
        try:
            articles = []
            for item in (self._yf.news or [])[:n]:
                content = item.get("content", item)
                title = content.get("title", "No title")
                link = (
                    content.get("clickThroughUrl", {}).get("url")
                    or content.get("canonicalUrl", {}).get("url")
                    or item.get("link", "#")
                )
                publisher = (
                    content.get("provider", {}).get("displayName")
                    or item.get("publisher", "Unknown")
                )
                pub_date = content.get("pubDate")
                if not pub_date:
                    ts = item.get("providerPublishTime")
                    if ts:
                        pub_date = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                articles.append({
                    "title": title,
                    "link": link,
                    "publisher": publisher,
                    "date": pub_date or "Unknown date",
                })
            return articles
        except Exception:
            return []
    