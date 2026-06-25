import matplotlib.pyplot as plt


class Visualizer:

    def plot_comparison(self, portfolio_value, benchmark_value):
        plt.figure(figsize=(12, 6))

        plt.plot(portfolio_value, label="Portfolio")

        plt.plot(benchmark_value, label="S&P 500")

        plt.title("Portfolio vs Benchmark")

        plt.xlabel("Date")
        plt.ylabel("Value (€)")

        plt.grid(True)

        plt.legend()

        plt.tight_layout()

        plt.show()