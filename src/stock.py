import yfinance as yf
import pandas as pd

class Stock: 
    def __init__(self, ticker: str):
        self.ticker = ticker
        self.prices = None
        self.returns = None
    
    def load_data(self, start="2020-01-01", end=None):
        # Download historical price data from Yahoo Finance
        data = yf.download(self.ticker, start=start, end=end)

        # Keep only closing prices
        self.prices = data["Close"].squeeze()

        return self.prices
    
    def calculate_returns(self):
        #Ensure data is loaded before calculation
        if self.prices is None:
            raise ValueError("Data not loaded. Call load_data() first.")
        #Calculate daily percentage returns 
        self.returns = self.prices.pct_change().dropna()
        return self.returns
    
    def get_latest_price(self):
        # Ensure data exists
        if self.prices is None:
            raise ValueError("Data not loaded. Call load_data() first.")

        # Return most recent price
        return self.prices.iloc[-1]

