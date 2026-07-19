import yfinance as yf


class ETFAnalysis:
    def __init__(self, ticker: str):
        self.ticker = ticker
        self._yf = yf.Ticker(ticker)
        self._info = self._yf.info

    def fund_name(self) -> str:
        return self._info.get("longName") or self._info.get("shortName") or self.ticker

    def fund_family(self) -> str:
        return self._info.get("fundFamily") or "N/A"

    def category(self) -> str:
        return self._info.get("category") or "N/A"

    def description(self) -> str:
        return self._info.get("longBusinessSummary") or "No description available."

    def expense_ratio(self) -> float | None:
        return (
            self._info.get("annualReportExpenseRatio")
            or self._info.get("expenseRatio")
        )

    def total_assets(self) -> float | None:
        return self._info.get("totalAssets")

    def dividend_yield(self) -> float | None:
        return (
            self._info.get("yield")
            or self._info.get("trailingAnnualDividendYield")
            or self._info.get("dividendYield")
        )

    def beta(self) -> float | None:
        return self._info.get("beta3Year") or self._info.get("beta")

    def ytd_return(self) -> float | None:
        return self._info.get("ytdReturn")

    def three_year_return(self) -> float | None:
        return self._info.get("threeYearAverageReturn")

    def five_year_return(self) -> float | None:
        return self._info.get("fiveYearAverageReturn")

    def nav(self) -> float | None:
        return self._info.get("navPrice") or self._info.get("regularMarketPrice")

    def fifty_two_week_high(self) -> float | None:
        return self._info.get("fiftyTwoWeekHigh")

    def fifty_two_week_low(self) -> float | None:
        return self._info.get("fiftyTwoWeekLow")

    def get_price_history(self, period="1y"):
        return self._yf.history(period=period)["Close"]

    def dividend_history(self):
        return self._yf.dividends
