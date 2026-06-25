from src.stock import Stock
from src.portfolio import Portfolio
from src.visualizer import Visualizer

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
initial_investment = float(input("Enter initial investment amount (€): "))
portfolio_value = portfolio.calculate_portfolio_value(initial_investment)
benchmark = portfolio.load_benchmark()

benchmark_value = (portfolio.calculate_benchmark_value(benchmark,initial_investment))
visualizer = Visualizer()
visualizer.plot_comparison(portfolio_value, benchmark_value)

portfolio_return = portfolio.calculate_total_return(portfolio_value, initial_investment)

benchmark_return = portfolio.calculate_benchmark_return(benchmark_value, initial_investment)

outperformance = portfolio.calculate_outperformance(portfolio_return, benchmark_return)


print("\n===== PORTFOLIO SUMMARY =====\n")

print(
    f"Initial Investment: "
    f"€{initial_investment:,.2f}"
)

print(
    f"Final Portfolio Value: "
    f"€{portfolio_value.iloc[-1]:,.2f}"
)

print(
    f"Portfolio Return: "
    f"{portfolio_return:.2%}"
)

print(
    f"Benchmark Return: "
    f"{benchmark_return:.2%}"
)

print(
    f"Outperformance: "
    f"{outperformance:.2%}"
)

print(
    f"Portfolio Volatility: "
    f"{volatility:.2%}"
)