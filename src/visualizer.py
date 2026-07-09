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

    def plot_asset_assessment(self, scores: dict):
        categories = list(scores.keys())
        values = list(scores.values())
        values += values[:1]
        categories_closed = categories + [categories[0]]

        fig = go.Figure(go.Scatterpolar(
            r=values,
            theta=categories_closed,
            fill="toself",
            fillcolor="rgba(33, 150, 243, 0.2)",
            line=dict(color="#2196F3", width=2),
            name="Score",
        ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 10], tickfont=dict(size=10)),
            ),
            title="Asset Assessment (0–10)",
            showlegend=False,
        )

        return fig

    def plot_annual_returns(self, annual_returns):
        years = [str(d.year) for d in annual_returns.index]
        values = annual_returns.values
        colors = ["#4CAF50" if v >= 0 else "#F44336" for v in values]

        fig = go.Figure(go.Bar(
            x=years,
            y=values,
            marker_color=colors,
            text=[f"{v:.1%}" for v in values],
            textposition="outside",
        ))

        fig.update_layout(
            title="Annual Returns",
            xaxis_title="Year",
            yaxis_title="Return",
            yaxis_tickformat=".0%",
            showlegend=False,
        )

        fig.add_hline(y=0, line_color="white", line_width=1)

        return fig

    def plot_sector_allocation(self, sector_weights):
        fig = go.Figure(go.Pie(
            labels=list(sector_weights.keys()),
            values=list(sector_weights.values()),
            hole=0.4,
            textinfo="label+percent",
        ))

        fig.update_layout(
            title="Sector Allocation",
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        )

        return fig

    def plot_individual_stocks(self, individual_values):
        fig = go.Figure()

        for ticker in individual_values.columns:
            fig.add_trace(go.Scatter(
                x=individual_values.index,
                y=individual_values[ticker],
                mode="lines",
                name=ticker,
            ))

        fig.update_layout(
            title="Individual Stock Performance",
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

    def plot_monte_carlo(self, simulation_df, initial_investment):
        mean_path = simulation_df.mean(axis=1)
        p95 = simulation_df.quantile(0.95, axis=1)
        p05 = simulation_df.quantile(0.05, axis=1)
        days = list(range(len(mean_path)))

        fig = go.Figure()

        # Shaded area between 5th and 95th percentile
        fig.add_trace(go.Scatter(
            x=days + days[::-1],
            y=list(p95) + list(p05[::-1]),
            fill="toself",
            fillcolor="rgba(33, 150, 243, 0.15)",
            line=dict(color="rgba(255,255,255,0)"),
            name="5th–95th Percentile Range",
            hoverinfo="skip",
        ))

        fig.add_trace(go.Scatter(x=days, y=p95, mode="lines", name="Best Case (95th)", line=dict(color="#4CAF50", width=1.5, dash="dash")))
        fig.add_trace(go.Scatter(x=days, y=p05, mode="lines", name="Worst Case (5th)", line=dict(color="#F44336", width=1.5, dash="dash")))
        fig.add_trace(go.Scatter(x=days, y=mean_path, mode="lines", name="Mean", line=dict(color="#2196F3", width=2.5)))

        fig.add_hline(y=initial_investment, line_dash="dot", line_color="orange", annotation_text="Initial Investment")

        fig.update_layout(
            title=f"Monte Carlo Simulation ({simulation_df.shape[1]} scenarios, 1 year)",
            xaxis_title="Trading Days",
            yaxis_title="Portfolio Value (€)",
            hovermode="x unified",
        )

        return fig

    def plot_dca(self, dca_series, lump_sum_series, total_invested):
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=dca_series.index, y=dca_series.values,
            name="DCA Strategy", line=dict(color="#2196F3", width=2)
        ))

        fig.add_trace(go.Scatter(
            x=lump_sum_series.index, y=lump_sum_series.values,
            name="Lump Sum", line=dict(color="#FF9800", width=2)
        ))

        fig.add_hline(
            y=total_invested, line_dash="dot", line_color="gray",
            annotation_text=f"Total Invested (€{total_invested:,.0f})"
        )

        fig.update_layout(
            title="DCA vs Lump Sum Strategy",
            xaxis_title="Date",
            yaxis_title="Value (€)",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )

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
