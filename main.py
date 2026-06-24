from src.stock import Stock

apple = Stock("AAPL")

apple.load_data()
apple.calculate_returns()

print(apple.get_latest_price())
print(apple.returns.head())