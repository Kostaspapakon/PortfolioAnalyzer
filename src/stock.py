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
        self.prices = data["Close"]

        return self.prices
