class TechnicalAnalysis:

    def __init__(self, prices):
        self.prices = prices

    def sma(self, window):
        return self.prices.rolling(window).mean()

    def bollinger_bands(self):
        sma20 = self.prices.rolling(20).mean()
        std20 = self.prices.rolling(20).std()
        upper = sma20 + 2 * std20
        lower = sma20 - 2 * std20 
        return upper, sma20, lower
    
    def rsi(self):
        delta = self.prices.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs =gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def signals(self):
        rsi = self.rsi()
        last_rsi = rsi.iloc[-1]
        results = []
        if last_rsi < 30:
            results.append(("RSI (14)", f"{last_rsi:.1f}", "Oversold - potential buy", "buy"))
        elif last_rsi > 70:
            results.append(("RSI (14)", f"{last_rsi:.1f}", "Overbought - potential sell", "sell"))
        else:
            results.append(("RSI (14)", f"{last_rsi:.1f}", "Neutral zone", "neutral"))

        sma50 = self.sma(50)
        sma200 = self.sma(200)
        last_sma50 = sma50.iloc[-1]
        last_sma200 = sma200.iloc[-1]
        if last_sma50 > last_sma200:
            results.append(("MA Cross", "Golden Cross", "SMA50 above SMA200 — Bullish", "buy"))
        else:
            results.append(("MA Cross", "Death Cross", "SMA50 below SMA200 — Bearish", "sell"))

        last_price = self.prices.iloc[-1]
        if last_price > last_sma200:
            results.append(("Trend", "Uptrend", f"Price above SMA200 (${last_sma200:.2f})", "buy"))
        else:
            results.append(("Trend", "Downtrend", f"Price below SMA200 (${last_sma200:.2f})", "sell"))

        return results
