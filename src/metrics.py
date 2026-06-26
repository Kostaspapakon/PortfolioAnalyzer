class Metrics:
    def __init__(self, risk_free_rate=0.04):
        self.risk_free_rate = risk_free_rate

    def sharpe_ratio(self, portfolio_returns):
        excess_returns = portfolio_returns - self.risk_free_rate / 252
        return (excess_returns.mean() / excess_returns.std()) * (252 ** 0.5)

    def max_drawdown(self, portfolio_value):
        rolling_max = portfolio_value.cummax()
        drawdown = (portfolio_value - rolling_max) / rolling_max
        return drawdown.min()
