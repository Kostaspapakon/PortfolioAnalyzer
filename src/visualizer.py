import matplotlib.pyplot as plt


class Visualizer:

    def plot_portfolio_value(self, portfolio_value):
        # Create figure
        plt.figure(figsize=(12, 6))

        # Plot portfolio value through time
        plt.plot(portfolio_value)

        # Add chart title
        plt.title("Portfolio Value Over Time")

        # Label axes
        plt.xlabel("Date")
        plt.ylabel("Portfolio Value (€)")

        # Add grid
        plt.grid(True)

        # Display chart
        plt.show()