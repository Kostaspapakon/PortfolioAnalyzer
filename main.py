from src.stock import Stock
from src.portfolio import Portfolio

google = Stock("GOOGL")
nvidia = Stock("NVDA")

portfolio = Portfolio(
    stocks=[google, nvidia],
    weights=[0.5, 0.5]
)

portfolio.validate_weights()
portfolio.load_all_data()
portfolio_returns = portfolio.calculate_portfolio_returns()
volatility = portfolio.calculate_volatility()
growth = portfolio.calculate_cumulative_return()

print(growth.tail())
print(f"Portfolio volatility: {volatility:.2%}")
print(portfolio_returns.head())
