import pandas as pd


class Portfolio:
    def __init__(self, stocks, weights):
        # List of Stock objects
        self.stocks = stocks

        # Portfolio weights
        self.weights = weights

        # Portfolio returns
        self.portfolio_returns = None