import plotly.graph_objects as go
import plotly.figure_factory as ff

_BLUE   = "#4F8EF7"
_ORANGE = "#FF9800"
_GREEN  = "#2ECC71"
_RED    = "#E74C3C"
_PURPLE = "#9B59B6"
_CYAN   = "#1ABC9C"
_PALETTE = [_BLUE, _ORANGE, _GREEN, _RED, _PURPLE, _CYAN]


class Visualizer:

    def _style(self, fig):
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, system-ui, sans-serif", size=12),
            margin=dict(l=10, r=10, t=55, b=10),
            title_x=0.01,
            title_font_size=15,
            legend_bgcolor="rgba(0,0,0,0)",
            legend_borderwidth=0,
            hoverlabel=dict(
                bgcolor="rgba(20,20,30,0.9)",
                bordercolor="rgba(255,255,255,0.15)",
                font_color="white",
                font_size=12,
            ),
        )
        fig.update_xaxes(
            gridcolor="rgba(128,128,128,0.1)",
            gridwidth=1,
            linecolor="rgba(128,128,128,0.2)",
            zeroline=False,
            tickfont=dict(size=11),
        )
        fig.update_yaxes(
            gridcolor="rgba(128,128,128,0.1)",
            gridwidth=1,
            linecolor="rgba(128,128,128,0.2)",
            zeroline=False,
            tickfont=dict(size=11),
        )
        return fig

    def plot_comparison(self, portfolio_value, benchmark_value):
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=portfolio_value.index,
            y=portfolio_value.values,
            name="My Portfolio",
            line=dict(color=_BLUE, width=2.5),
            fill="tozeroy",
            fillcolor="rgba(79,142,247,0.06)",
        ))
        fig.add_trace(go.Scatter(
            x=benchmark_value.index,
            y=benchmark_value.values,
            name="S&P 500 Equivalent",
            line=dict(color=_ORANGE, width=2, dash="dash"),
        ))

        fig.update_layout(
            title="Portfolio vs S&P 500",
            yaxis_title="Value (€)",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        return self._style(fig)

    def plot_asset_assessment(self, scores: dict):
        categories = list(scores.keys())
        values = list(scores.values())
        values += values[:1]
        categories_closed = categories + [categories[0]]

        fig = go.Figure(go.Scatterpolar(
            r=values,
            theta=categories_closed,
            fill="toself",
            fillcolor="rgba(79,142,247,0.15)",
            line=dict(color=_BLUE, width=2),
            name="Score",
        ))

        fig.update_layout(
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(
                    visible=True,
                    range=[0, 10],
                    tickfont=dict(size=9),
                    gridcolor="rgba(128,128,128,0.2)",
                ),
                angularaxis=dict(gridcolor="rgba(128,128,128,0.15)"),
            ),
            title="Fundamental Health (0–10)",
            showlegend=False,
        )
        return self._style(fig)

    def plot_annual_returns(self, annual_returns):
        years = [str(d.year) for d in annual_returns.index]
        values = annual_returns.values
        colors = [_GREEN if v >= 0 else _RED for v in values]

        fig = go.Figure(go.Bar(
            x=years,
            y=values,
            marker_color=colors,
            marker_line_width=0,
            text=[f"{v:+.1%}" for v in values],
            textposition="outside",
            textfont=dict(size=11),
        ))

        fig.update_layout(
            title="Annual Returns",
            yaxis_tickformat=".0%",
            showlegend=False,
            bargap=0.35,
        )
        fig.add_hline(y=0, line_color="rgba(128,128,128,0.4)", line_width=1)
        return self._style(fig)

    def plot_sector_allocation(self, sector_weights):
        fig = go.Figure(go.Pie(
            labels=list(sector_weights.keys()),
            values=list(sector_weights.values()),
            hole=0.5,
            textinfo="label+percent",
            textfont=dict(size=12),
            marker=dict(
                colors=_PALETTE,
                line=dict(color="rgba(0,0,0,0)", width=0),
            ),
        ))

        fig.update_layout(
            title="Sector Allocation",
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
        )
        return self._style(fig)

    def plot_individual_stocks(self, individual_values):
        fig = go.Figure()

        for i, ticker in enumerate(individual_values.columns):
            fig.add_trace(go.Scatter(
                x=individual_values.index,
                y=individual_values[ticker],
                mode="lines",
                name=ticker,
                line=dict(color=_PALETTE[i % len(_PALETTE)], width=2),
            ))

        fig.update_layout(
            title="Individual Stock Performance",
            yaxis_title="Value (€)",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        return self._style(fig)

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
            annotation_text=[[f"{v:.2f}" for v in row] for row in values],
        )

        fig.update_layout(title="Correlation Matrix")
        return self._style(fig)

    def plot_monte_carlo(self, simulation_df, initial_investment):
        mean_path = simulation_df.mean(axis=1)
        p95 = simulation_df.quantile(0.95, axis=1)
        p05 = simulation_df.quantile(0.05, axis=1)
        days = list(range(len(mean_path)))

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=days + days[::-1],
            y=list(p95) + list(p05[::-1]),
            fill="toself",
            fillcolor="rgba(79,142,247,0.1)",
            line=dict(color="rgba(0,0,0,0)"),
            name="5th–95th Percentile",
            hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(x=days, y=p95, mode="lines", name="Best Case (95th)", line=dict(color=_GREEN, width=1.5, dash="dash")))
        fig.add_trace(go.Scatter(x=days, y=p05, mode="lines", name="Worst Case (5th)", line=dict(color=_RED, width=1.5, dash="dash")))
        fig.add_trace(go.Scatter(x=days, y=mean_path, mode="lines", name="Mean Outcome", line=dict(color=_BLUE, width=2.5)))

        fig.add_hline(
            y=initial_investment,
            line_dash="dot",
            line_color=_ORANGE,
            line_width=1.5,
            annotation_text="Initial Investment",
            annotation_font_size=11,
        )

        fig.update_layout(
            title=f"Monte Carlo Simulation ({simulation_df.shape[1]:,} scenarios, 1 year)",
            xaxis_title="Trading Days",
            yaxis_title="Portfolio Value (€)",
            hovermode="x unified",
        )
        return self._style(fig)

    def plot_technical(self, prices, sma50, sma200, bb_upper, bb_lower):
        fig = go.Figure()

        valid = bb_upper.dropna()
        valid_lower = bb_lower.reindex(valid.index)
        dates = list(valid.index)
        fig.add_trace(go.Scatter(
            x=dates + dates[::-1],
            y=list(valid) + list(valid_lower[::-1]),
            fill="toself",
            fillcolor="rgba(79,142,247,0.07)",
            line=dict(color="rgba(0,0,0,0)"),
            name="Bollinger Bands",
            hoverinfo="skip",
        ))

        fig.add_trace(go.Scatter(
            x=prices.index, y=prices.values,
            name="Price", line=dict(color=_BLUE, width=2),
        ))
        fig.add_trace(go.Scatter(
            x=sma50.index, y=sma50.values,
            name="SMA 50", line=dict(color=_ORANGE, width=1.5, dash="dash"),
        ))
        fig.add_trace(go.Scatter(
            x=sma200.index, y=sma200.values,
            name="SMA 200", line=dict(color=_RED, width=1.5, dash="dash"),
        ))

        fig.update_layout(
            title="Price Chart with Technical Indicators",
            yaxis_title="Price ($)",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        return self._style(fig)

    def plot_rsi(self, rsi):
        fig = go.Figure()

        fig.add_hrect(y0=70, y1=100, fillcolor="rgba(231,76,60,0.08)", line_width=0)
        fig.add_hrect(y0=0,  y1=30,  fillcolor="rgba(46,204,113,0.08)", line_width=0)

        fig.add_trace(go.Scatter(
            x=rsi.index, y=rsi.values,
            name="RSI", line=dict(color=_BLUE, width=2),
        ))

        fig.add_hline(y=70, line_dash="dash", line_color=_RED,   line_width=1,
                      annotation_text="Overbought (70)", annotation_position="left", annotation_font_size=10)
        fig.add_hline(y=30, line_dash="dash", line_color=_GREEN, line_width=1,
                      annotation_text="Oversold (30)",  annotation_position="left", annotation_font_size=10)

        fig.update_layout(
            title="RSI (14)",
            yaxis=dict(title="RSI", range=[0, 100]),
            hovermode="x unified",
            showlegend=False,
        )
        return self._style(fig)

    def plot_peer_comparison(self, all_scores: dict):
        metrics = list(next(iter(all_scores.values())).keys())
        tickers = list(all_scores.keys())

        fig = go.Figure()
        for i, ticker in enumerate(tickers):
            scores = all_scores[ticker]
            fig.add_trace(go.Bar(
                name=ticker,
                x=metrics,
                y=[scores.get(m, 0) for m in metrics],
                marker_color=_PALETTE[i % len(_PALETTE)],
                marker_line_width=0,
            ))

        fig.update_layout(
            title="Peer Comparison — Financial Health Scores (0–10)",
            yaxis=dict(title="Score", range=[0, 10]),
            barmode="group",
            bargap=0.15,
            bargroupgap=0.05,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        return self._style(fig)

    def plot_dividend_income(self, dividend_df):
        fig = go.Figure(go.Bar(
            x=dividend_df["Ticker"],
            y=dividend_df["Annual Income (€)"],
            marker_color=_GREEN,
            marker_line_width=0,
            text=[f"€{v:.2f}" for v in dividend_df["Annual Income (€)"]],
            textposition="outside",
            textfont=dict(size=11),
        ))
        fig.update_layout(
            title="Estimated Annual Dividend Income per Stock",
            yaxis_title="Annual Income (€)",
            showlegend=False,
            bargap=0.4,
        )
        return self._style(fig)

    def plot_dividend_history(self, dividends):
        annual = dividends.resample("YE").sum()
        years = [str(d.year) for d in annual.index]
        fig = go.Figure(go.Bar(
            x=years,
            y=annual.values,
            marker_color=_BLUE,
            marker_line_width=0,
            text=[f"${v:.4f}" for v in annual.values],
            textposition="outside",
            textfont=dict(size=11),
        ))
        fig.update_layout(
            title="Annual Dividends per Share",
            yaxis_title="Dividend per Share ($)",
            showlegend=False,
            bargap=0.4,
        )
        return self._style(fig)

    def plot_dca(self, dca_series, lump_sum_series, total_invested):
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=dca_series.index, y=dca_series.values,
            name="DCA Strategy",
            line=dict(color=_BLUE, width=2.5),
            fill="tozeroy",
            fillcolor="rgba(79,142,247,0.05)",
        ))
        fig.add_trace(go.Scatter(
            x=lump_sum_series.index, y=lump_sum_series.values,
            name="Lump Sum",
            line=dict(color=_ORANGE, width=2, dash="dash"),
        ))

        fig.add_hline(
            y=total_invested,
            line_dash="dot",
            line_color="rgba(128,128,128,0.6)",
            line_width=1.5,
            annotation_text=f"Total Invested (€{total_invested:,.0f})",
            annotation_font_size=11,
        )

        fig.update_layout(
            title="DCA vs Lump Sum Strategy",
            yaxis_title="Value (€)",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        return self._style(fig)

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
                colorbar=dict(title="Sharpe", thickness=12),
                size=4,
                opacity=0.5,
            ),
            name="Portfolios",
            hovertemplate="Risk: %{x:.2%}<br>Return: %{y:.2%}<extra></extra>",
        ))

        weights_str = ", ".join(f"{t}: {w:.1%}" for t, w in zip(tickers, best["Weights"]))
        fig.add_trace(go.Scatter(
            x=[best["Volatility"]],
            y=[best["Return"]],
            mode="markers",
            marker=dict(color=_RED, size=16, symbol="star"),
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
        return self._style(fig)
