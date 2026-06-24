import pandas as pd


class Portfolio:
    def __init__(self, stocks, weights):
        # List of Stock objects
        self.stocks = stocks

        # Portfolio weights
        self.weights = weights

        # Portfolio returns
        self.portfolio_returns = None

    def validate_weights(self):
        # Weights must sum to 1
        if abs(sum(self.weights) - 1.0) > 0.0001:
            raise ValueError("Portfolio weights must sum to 1.")