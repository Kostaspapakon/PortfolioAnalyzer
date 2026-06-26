import plotly.graph_objects as go


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
