import os
import numpy as np
import pandas as pd
from scipy.optimize import minimize
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
        
    def load_all_data(self, start="2020-01-01", end=None):
        for stock in self.stocks:
            stock.load_data(start=start, end=end)
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
    
    def load_benchmark(self, ticker="^GSPC", start="2020-01-01", end=None):
        benchmark = Stock(ticker)

        benchmark.load_data(start=start, end=end)
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

    def calculate_individual_values(self, initial_investment):
        individual_values = pd.DataFrame()

        for stock, weight in zip(self.stocks, self.weights):
            cumulative_growth = (1 + stock.returns).cumprod()
            individual_values[stock.ticker] = cumulative_growth * (initial_investment * weight)

        return individual_values

    def calculate_correlation(self):
        returns_df = pd.DataFrame({stock.ticker: stock.returns for stock in self.stocks})
        return returns_df.corr()

    def simulate_monte_carlo(self, initial_investment, simulations=1000, days=252):
        mean = self.portfolio_returns.mean()
        std = self.portfolio_returns.std()

        shocks = np.random.normal(mean, std, (days, simulations))
        daily_returns = 1 + shocks
        paths = np.cumprod(daily_returns, axis=0)

        return pd.DataFrame(paths * initial_investment)

    def optimize_portfolio(self):
        returns_df = pd.DataFrame({stock.ticker: stock.returns for stock in self.stocks})
        n = len(self.stocks)

        def negative_sharpe(weights):
            r = (returns_df * weights).sum(axis=1)
            ret = r.mean() * 252
            vol = r.std() * (252 ** 0.5)
            return -(ret - self.metrics.risk_free_rate) / vol

        initial_weights = [1 / n for _ in range(n)]
        bounds = [(0, 1) for _ in range(n)]
        constraints = {"type": "eq", "fun": lambda w: sum(w) - 1}

        result = minimize(
            fun=negative_sharpe,
            x0=initial_weights,
            bounds=bounds,
            constraints=constraints,
            method="SLSQP"
        )

        return dict(zip([stock.ticker for stock in self.stocks], result.x))

    def calculate_efficient_frontier(self, num_portfolios=5000):
        returns_df = pd.DataFrame({stock.ticker: stock.returns for stock in self.stocks})
        n = len(self.stocks)
        results = []

        for _ in range(num_portfolios):
            w = np.random.dirichlet(np.ones(n))
            ret = (returns_df * w).sum(axis=1).mean() * 252
            vol = (returns_df * w).sum(axis=1).std() * (252 ** 0.5)
            sharpe = (ret - self.metrics.risk_free_rate) / vol
            results.append({"Return": ret, "Volatility": vol, "Sharpe": sharpe, "Weights": w})

        return pd.DataFrame(results)

    def export_to_csv(self, portfolio_value, benchmark_value, summary: dict, output_dir="results"):
        os.makedirs(output_dir, exist_ok=True)

        values_df = pd.DataFrame({
            "Portfolio Value (€)": portfolio_value,
            "Benchmark Value (€)": benchmark_value,
        })
        values_df.to_csv(os.path.join(output_dir, "portfolio_values.csv"))

        summary_df = pd.DataFrame([summary])
        summary_df.to_csv(os.path.join(output_dir, "portfolio_summary.csv"), index=False)

        print(f"\nResults exported to '{output_dir}/' folder.")