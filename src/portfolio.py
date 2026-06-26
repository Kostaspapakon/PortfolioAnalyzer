import pandas as pd
from src.stock import Stock
from src.metrics import Metrics


class Portfolio:
    def __init__(self, stocks, weights):
        # List of Stock objects
        self.stocks = stocks

        # Portfolio weights
        self.weights = weights

        # Portfolio returns
        self.portfolio_returns = None

        self.metrics = Metrics()

    def validate_weights(self):
        # Weights must sum to 1
        if abs(sum(self.weights) - 1.0) > 0.0001:
            raise ValueError("Portfolio weights must sum to 1.")
        
    def load_all_data(self):
        # Download data for every stock
        for stock in self.stocks:
            stock.load_data()
            stock.calculate_returns()

    def calculate_portfolio_returns(self):
         # Create a dataframe with all stock returns
        returns_df = pd.DataFrame()

        for stock in self.stocks:
            returns_df[stock.ticker] = stock.returns

        # Calculate weighted portfolio returns
        self.portfolio_returns = (returns_df * self.weights).sum(axis=1)

        return self.portfolio_returns
    
    def calculate_volatility(self):
        # Annualized portfolio volatility
        return self.portfolio_returns.std() * (252 ** 0.5)
    
    def calculate_cumulative_return(self):
        # Calculate portfolio growth over time
        cumulative_growth = (1 + self.portfolio_returns).cumprod()

        return cumulative_growth
    
    def calculate_portfolio_value(self, initial_investment):
        # Calculate cumulative growth factor
        cumulative_growth = (1 + self.portfolio_returns).cumprod()

        # Convert growth factor to portfolio value
        portfolio_value = cumulative_growth * initial_investment

        return portfolio_value
    
    def load_benchmark(self, ticker="^GSPC"):
        benchmark = Stock(ticker)

        benchmark.load_data()
        benchmark.calculate_returns()

        return benchmark
    
    def calculate_benchmark_value(self, benchmark, initial_investment):
        cumulative_growth = (1 + benchmark.returns).cumprod()
        benchmark_value = (cumulative_growth * initial_investment)
        
        return benchmark_value
    
    def calculate_total_return(self, portfolio_value, initial_investment):
        # Calculate total portfolio return
        total_return = (portfolio_value.iloc[-1] / initial_investment - 1)

        return total_return
    
    def calculate_benchmark_return(self, benchmark_value, initial_investment):
        benchmark_return = (benchmark_value.iloc[-1] / initial_investment - 1)

        return benchmark_return
    
    def calculate_outperformance(self, portfolio_return, benchmark_return):
        return portfolio_return - benchmark_return

    def calculate_sharpe_ratio(self):
        return self.metrics.sharpe_ratio(self.portfolio_returns)

    def calculate_max_drawdown(self, portfolio_value):
        return self.metrics.max_drawdown(portfolio_value)