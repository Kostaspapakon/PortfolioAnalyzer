import streamlit as st
import pandas as pd
from src.stock import Stock
from src.portfolio import Portfolio
from src.visualizer import Visualizer

st.set_page_config(page_title="Portfolio Analyzer", layout="wide")
st.title("Portfolio Analyzer")

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Portfolio Setup")

    tickers_input = st.text_input("Stock Tickers (comma-separated)", value="AAPL, NVDA")
    weights_input = st.text_input("Weights (comma-separated, must sum to 1)", value="0.5, 0.5")
    initial_investment = st.number_input("Initial Investment (€)", min_value=1.0, value=10000.0, step=100.0)
    analyze = st.button("Analyze", use_container_width=True)

# ── Main ───────────────────────────────────────────────────────────────────────
if analyze:
    # Parse and validate inputs
    try:
        tickers = [t.strip().upper() for t in tickers_input.split(",")]
        weights = [float(w.strip()) for w in weights_input.split(",")]

        if len(tickers) != len(weights):
            st.error("Number of tickers and weights must match.")
            st.stop()

        if abs(sum(weights) - 1.0) > 0.0001:
            st.error(f"Weights must sum to 1.0 (currently {sum(weights):.4f}).")
            st.stop()

    except ValueError:
        st.error("Invalid input. Make sure weights are numbers.")
        st.stop()

    with st.spinner("Downloading data and calculating..."):
        stocks = [Stock(ticker) for ticker in tickers]
        portfolio = Portfolio(stocks=stocks, weights=weights)
        portfolio.validate_weights()
        portfolio.load_all_data()

        portfolio_returns = portfolio.calculate_portfolio_returns()
        volatility = portfolio.calculate_volatility()
        portfolio_value = portfolio.calculate_portfolio_value(initial_investment)
        benchmark = portfolio.load_benchmark()
        benchmark_value = portfolio.calculate_benchmark_value(benchmark, initial_investment)
        portfolio_return = portfolio.calculate_total_return(portfolio_value, initial_investment)
        benchmark_return = portfolio.calculate_benchmark_return(benchmark_value, initial_investment)
        outperformance = portfolio.calculate_outperformance(portfolio_return, benchmark_return)
        sharpe = portfolio.calculate_sharpe_ratio()
        max_drawdown = portfolio.calculate_max_drawdown(portfolio_value)

    # ── Chart ──────────────────────────────────────────────────────────────────
    visualizer = Visualizer()
    fig = visualizer.plot_comparison(portfolio_value, benchmark_value)
    st.plotly_chart(fig, use_container_width=True)

    # ── Metrics ────────────────────────────────────────────────────────────────
    st.subheader("Portfolio Summary")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Initial Investment", f"€{initial_investment:,.2f}")
    col2.metric("Final Value", f"€{portfolio_value.iloc[-1]:,.2f}")
    col3.metric("Portfolio Return", f"{portfolio_return:.2%}")
    col4.metric("Benchmark Return", f"{benchmark_return:.2%}")

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Outperformance", f"{outperformance:.2%}")
    col6.metric("Volatility", f"{volatility:.2%}")
    col7.metric("Sharpe Ratio", f"{sharpe:.2f}")
    col8.metric("Max Drawdown", f"{max_drawdown:.2%}")

    # ── Efficient Frontier ─────────────────────────────────────────────────────
    if len(tickers) > 1:
        st.subheader("Efficient Frontier")
        with st.spinner("Simulating portfolios..."):
            frontier_df = portfolio.calculate_efficient_frontier()
        frontier_fig = visualizer.plot_efficient_frontier(frontier_df, tickers)
        st.plotly_chart(frontier_fig, use_container_width=True)

    # ── Correlation Matrix ─────────────────────────────────────────────────────
    if len(tickers) > 1:
        st.subheader("Correlation Matrix")
        corr_matrix = portfolio.calculate_correlation()
        corr_fig = visualizer.plot_correlation(corr_matrix)
        st.plotly_chart(corr_fig, use_container_width=True)

    # ── Download ───────────────────────────────────────────────────────────────
    st.subheader("Export Results")

    values_df = pd.DataFrame({
        "Portfolio Value (€)": portfolio_value,
        "Benchmark Value (€)": benchmark_value,
    })

    summary = {
        "Initial Investment (€)": initial_investment,
        "Final Portfolio Value (€)": portfolio_value.iloc[-1],
        "Portfolio Return": f"{portfolio_return:.2%}",
        "Benchmark Return": f"{benchmark_return:.2%}",
        "Outperformance": f"{outperformance:.2%}",
        "Volatility": f"{volatility:.2%}",
        "Sharpe Ratio": f"{sharpe:.2f}",
        "Max Drawdown": f"{max_drawdown:.2%}",
    }
    summary_df = pd.DataFrame([summary])

    col_dl1, col_dl2 = st.columns(2)
    col_dl1.download_button(
        label="Download Portfolio Values (CSV)",
        data=values_df.to_csv().encode("utf-8"),
        file_name="portfolio_values.csv",
        mime="text/csv",
        use_container_width=True,
    )
    col_dl2.download_button(
        label="Download Summary (CSV)",
        data=summary_df.to_csv(index=False).encode("utf-8"),
        file_name="portfolio_summary.csv",
        mime="text/csv",
        use_container_width=True,
    )
