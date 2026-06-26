from src.stock import Stock
from src.portfolio import Portfolio
from src.visualizer import Visualizer


def get_user_input():
    print("===== PORTFOLIO ANALYZER =====\n")

    tickers_input = input("Enter stock tickers separated by commas (e.g. AAPL, MSFT, TSLA): ")
    tickers = [t.strip().upper() for t in tickers_input.split(",")]

    weights_input = input("Enter weights separated by commas (e.g. 0.4, 0.4, 0.2): ")
    weights = [float(w.strip()) for w in weights_input.split(",")]

    if len(tickers) != len(weights):
        raise ValueError("Number of tickers and weights must match.")

    if abs(sum(weights) - 1.0) > 0.0001:
        raise ValueError(f"Weights must sum to 1.0 (currently sum to {sum(weights):.4f}).")

    investment_input = input("Enter initial investment amount (€): ")
    initial_investment = float(investment_input)

    if initial_investment <= 0:
        raise ValueError("Initial investment must be a positive number.")

    return tickers, weights, initial_investment


tickers, weights, initial_investment = get_user_input()

stocks = [Stock(ticker) for ticker in tickers]

portfolio = Portfolio(
    stocks=stocks,
    weights=weights
)

portfolio.validate_weights()
portfolio.load_all_data()
portfolio_returns = portfolio.calculate_portfolio_returns()
volatility = portfolio.calculate_volatility()
growth = portfolio.calculate_cumulative_return()
portfolio_value = portfolio.calculate_portfolio_value(initial_investment)
benchmark = portfolio.load_benchmark()

benchmark_value = portfolio.calculate_benchmark_value(benchmark, initial_investment)
visualizer = Visualizer()
visualizer.plot_comparison(portfolio_value, benchmark_value)

portfolio_return = portfolio.calculate_total_return(portfolio_value, initial_investment)
benchmark_return = portfolio.calculate_benchmark_return(benchmark_value, initial_investment)
outperformance = portfolio.calculate_outperformance(portfolio_return, benchmark_return)
sharpe = portfolio.calculate_sharpe_ratio()
max_drawdown = portfolio.calculate_max_drawdown(portfolio_value)


print("\n===== PORTFOLIO SUMMARY =====\n")

print(f"Initial Investment:    €{initial_investment:,.2f}")
print(f"Final Portfolio Value: €{portfolio_value.iloc[-1]:,.2f}")
print(f"Portfolio Return:      {portfolio_return:.2%}")
print(f"Benchmark Return:      {benchmark_return:.2%}")
print(f"Outperformance:        {outperformance:.2%}")
print(f"Portfolio Volatility:  {volatility:.2%}")
print(f"Sharpe Ratio:          {sharpe:.2f}")
print(f"Max Drawdown:          {max_drawdown:.2%}")
