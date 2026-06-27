import plotly.graph_objects as go
import plotly.figure_factory as ff


class Visualizer:

    def plot_comparison(self, portfolio_value, benchmark_value):
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=portfolio_value.index,
            y=portfolio_value.values,
            name="Portfolio",
            line=dict(color="#2196F3"),
        ))

        fig.add_trace(go.Scatter(
            x=benchmark_value.index,
            y=benchmark_value.values,
            name="S&P 500",
            line=dict(color="#FF9800"),
        ))

        fig.update_layout(
            title="Portfolio vs S&P 500",
            xaxis_title="Date",
            yaxis_title="Value (€)",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )

        return fig

    def plot_correlation(self, corr_matrix):
        tickers = list(corr_matrix.columns)
        values = corr_matrix.values.tolist()

        fig = ff.create_annotated_heatmap(
            z=values,
            x=tickers,
            y=tickers,
            colorscale="RdBu",
            reversescale=True,
            zmin=-1,
            zmax=1,
            showscale=True,
        )

        fig.update_layout(title="Correlation Matrix")

        return fig

    def plot_efficient_frontier(self, frontier_df, tickers):
        best_idx = frontier_df["Sharpe"].idxmax()
        best = frontier_df.loc[best_idx]

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=frontier_df["Volatility"],
            y=frontier_df["Return"],
            mode="markers",
            marker=dict(
                color=frontier_df["Sharpe"],
                colorscale="Viridis",
                colorbar=dict(title="Sharpe Ratio"),
                size=4,
                opacity=0.6,
            ),
            name="Portfolios",
            hovertemplate="Volatility: %{x:.2%}<br>Return: %{y:.2%}<extra></extra>",
        ))

        weights_str = ", ".join(f"{t}: {w:.1%}" for t, w in zip(tickers, best["Weights"]))
        fig.add_trace(go.Scatter(
            x=[best["Volatility"]],
            y=[best["Return"]],
            mode="markers",
            marker=dict(color="red", size=14, symbol="star"),
            name=f"Max Sharpe ({weights_str})",
        ))

        fig.update_layout(
            title="Efficient Frontier",
            xaxis_title="Volatility (Risk)",
            yaxis_title="Expected Return",
            xaxis_tickformat=".0%",
            yaxis_tickformat=".0%",
            hovermode="closest",
        )

        return fig
