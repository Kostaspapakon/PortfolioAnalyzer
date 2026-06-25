import matplotlib.pyplot as plt


class Visualizer:

    def plot_portfolio_value(self, portfolio_value):
        # Create chart figure
        plt.figure(figsize=(12, 6))

        # Plot portfolio value
        plt.plot(portfolio_value)

        # Chart title
        plt.title("Portfolio Value Over Time")

        # Axis labels
        plt.xlabel("Date")
        plt.ylabel("Portfolio Value (€)")

        # Grid for readability
        plt.grid(True)

        # Adjust layout
        plt.tight_layout()

        # Display chart
        plt.show()