import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta
from src.stock import Stock
from src.portfolio import Portfolio
from src.visualizer import Visualizer
from src.database import Database
from src.fundamentals import FundamentalAnalysis


def score_fundamentals(fa: FundamentalAnalysis) -> tuple[dict, list]:
    scores = {}
    checklist = []

    def add(label, value, score, passed, description):
        scores[label] = score
        checklist.append({"label": label, "value": value, "passed": passed, "description": description})

    cr = fa.current_ratio()
    if cr:
        s = min(10, cr / 1.5 * 10) if cr <= 3 else max(0, 10 - (cr - 3) * 2)
        add("Current Ratio", f"{cr:.2f}", round(s, 1), cr >= 1.5, "Current Ratio ≥ 1.5")

    de = fa.debt_to_equity()
    if de:
        s = max(0, 10 - de * 4)
        add("Debt/Equity", f"{de:.2f}", round(s, 1), de <= 1.0, "Debt/Equity ≤ 1.0")

    pm = fa.profit_margin()
    if pm:
        s = min(10, pm * 40)
        add("Profit Margin", f"{pm:.1%}", round(s, 1), pm >= 0.10, "Profit Margin ≥ 10%")

    rg = fa.revenue_growth()
    if rg:
        s = min(10, max(0, rg * 50 + 5))
        add("Revenue Growth", f"{rg:.1%}", round(s, 1), rg >= 0, "Revenue Growth > 0%")

    eps = fa.eps()
    if eps:
        add("EPS", f"{eps:.2f}", 8 if eps > 0 else 2, eps > 0, "EPS > 0")

    pe = fa.pe_ratio()
    if pe:
        s = max(0, 10 - (pe - 15) * 0.3) if pe > 15 else 10
        add("P/E Ratio", f"{pe:.1f}", round(s, 1), pe <= 30, "P/E Ratio ≤ 30")

    pb = fa.pb_ratio()
    if pb:
        s = max(0, 10 - (pb - 1) * 2)
        add("P/B Ratio", f"{pb:.2f}", round(s, 1), pb <= 3.0, "P/B Ratio ≤ 3.0")

    fcf = fa.free_cash_flow()
    if fcf:
        add("Free Cash Flow", f"€{fcf/1e9:.1f}B", 9 if fcf > 0 else 1, fcf > 0, "Free Cash Flow > 0")

    return scores, checklist


def generate_summary(scores: dict, checklist: list) -> tuple[str, str]:
    if not scores:
        return "Not enough data to generate a summary.", "info"

    avg_score = sum(scores.values()) / len(scores)
    passed = sum(1 for item in checklist if item["passed"])
    total = len(checklist)

    if avg_score >= 7.5:
        verdict = "This stock shows strong financial fundamentals and appears to be a relatively safe investment."
        level = "success"
    elif avg_score >= 5.5:
        verdict = "This stock has moderate fundamentals with a mix of strengths and weaknesses."
        level = "info"
    elif avg_score >= 3.5:
        verdict = "This stock shows some financial weaknesses and carries elevated risk."
        level = "warning"
    else:
        verdict = "This stock has significant financial red flags and should be approached with caution."
        level = "error"

    parts = [verdict]

    strengths = [label for label, score in scores.items() if score >= 7]
    weaknesses = [label for label, score in scores.items() if score < 4]

    if strengths:
        parts.append(f"Key strengths: {', '.join(strengths)}.")
    if weaknesses:
        parts.append(f"Areas of concern: {', '.join(weaknesses)}.")

    rg = scores.get("Revenue Growth", 0)
    pm = scores.get("Profit Margin", 0)
    if rg >= 6 and pm >= 6:
        parts.append("The company demonstrates solid growth potential with healthy revenue and margins.")
    elif rg >= 6:
        parts.append("Revenue growth is positive, though profitability could be improved.")
    elif pm >= 6:
        parts.append("Profitability is solid, but revenue growth appears limited.")

    pe = scores.get("P/E Ratio", 5)
    pb = scores.get("P/B Ratio", 5)
    if pe >= 7 and pb >= 7:
        parts.append("The stock appears fairly valued or undervalued based on P/E and P/B ratios.")
    elif pe < 4 or pb < 4:
        parts.append("The valuation appears stretched — investors are paying a premium for this stock.")

    fcf = scores.get("Free Cash Flow", 5)
    if fcf >= 8:
        parts.append("Strong free cash flow generation supports future investments and shareholder returns.")
    elif fcf <= 2:
        parts.append("Negative free cash flow raises concerns about the company's ability to self-fund growth.")

    parts.append(f"Overall: {passed}/{total} health checks passed (average score {avg_score:.1f}/10).")

    return " ".join(parts), level


def show_risk_warnings(max_drawdown, sharpe, outperformance, beta):
    st.subheader("Risk Analysis")

    if abs(max_drawdown) > 0.40:
        st.error(f"High Risk: Max Drawdown is {max_drawdown:.2%}. Your portfolio lost more than 40% from its peak at some point.")
    elif abs(max_drawdown) > 0.20:
        st.warning(f"Moderate Risk: Max Drawdown is {max_drawdown:.2%}.")
    else:
        st.success(f"Low Risk: Max Drawdown is {max_drawdown:.2%}.")

    if sharpe < 0:
        st.error(f"Negative Sharpe Ratio: {sharpe:.2f}. Your portfolio is underperforming even a risk-free investment.")
    elif sharpe < 1:
        st.warning(f"Below Average Sharpe Ratio: {sharpe:.2f}. The return does not justify the risk taken.")
    else:
        st.success(f"Good Sharpe Ratio: {sharpe:.2f}. Your portfolio offers a solid return for the risk taken.")

    if outperformance < 0:
        st.warning(f"Underperforming S&P 500 by {abs(outperformance):.2%}. Consider reviewing your portfolio allocation.")
    else:
        st.success(f"Outperforming S&P 500 by {outperformance:.2%}. Your portfolio beats the market!")

    if beta > 1.5:
        st.error(f"High Beta: {beta:.2f}. Your portfolio is significantly more volatile than the market.")
    elif beta > 1.0:
        st.warning(f"Aggressive Beta: {beta:.2f}. Your portfolio moves more than the market.")
    elif beta > 0.5:
        st.success(f"Defensive Beta: {beta:.2f}. Your portfolio is less volatile than the market.")
    else:
        st.info(f"Low Beta: {beta:.2f}. Your portfolio moves very little relative to the market.")


def format_delta(value, initial):
    diff = value - initial
    sign = "+" if diff >= 0 else "-"
    return f"{sign}€{abs(diff):,.2f}"


st.set_page_config(page_title="Portfolio Analyzer", layout="wide")
st.title("Portfolio Analyzer")

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Portfolio Setup")

    db = Database()
    all_stocks = db.get_all_stocks()
    db.close()

    stock_options = [f"{name} ({ticker})" for ticker, name, _ in all_stocks]

    selected = st.multiselect("Search & Select Stocks", options=stock_options, default=["Apple (AAPL)", "NVIDIA (NVDA)"])
    tickers = [s.split("(")[-1].rstrip(")") for s in selected]

    weights_input = st.text_input("Weights (comma-separated, must sum to 1)", value=", ".join([f"{1/len(tickers):.2f}" for _ in tickers]) if tickers else "")
    initial_investment = st.number_input("Initial Investment (€)", min_value=1.0, value=10000.0, step=100.0)

    st.divider()
    st.subheader("Date Range")

    preset = st.radio("Period", ["1Y", "3Y", "5Y", "10Y", "Custom"], horizontal=True)

    today = date.today()
    presets = {"1Y": 365, "3Y": 3 * 365, "5Y": 5 * 365, "10Y": 10 * 365}

    if preset != "Custom":
        start_date = today - timedelta(days=presets[preset])
        end_date = today
        st.caption(f"From {start_date} to {end_date}")
    else:
        start_date = st.date_input("Start Date", value=date(2010, 1, 1))
        end_date = st.date_input("End Date", value=today)

    analyze = st.button("Analyze", use_container_width=True)

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_portfolio, tab_stock = st.tabs(["Portfolio Analysis", "Stock Analysis"])

# ── Portfolio Analysis Tab ─────────────────────────────────────────────────────
with tab_portfolio:
    if analyze:
        try:
            if not tickers:
                st.error("Please select at least one stock.")
                st.stop()

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
            portfolio.load_all_data(start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"))

            portfolio_returns = portfolio.calculate_portfolio_returns()
            volatility = portfolio.calculate_volatility()
            portfolio_value = portfolio.calculate_portfolio_value(initial_investment)
            benchmark = portfolio.load_benchmark(start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"))
            benchmark_value = portfolio.calculate_benchmark_value(benchmark, initial_investment)
            portfolio_return = portfolio.calculate_total_return(portfolio_value, initial_investment)
            benchmark_return = portfolio.calculate_benchmark_return(benchmark_value, initial_investment)
            outperformance = portfolio.calculate_outperformance(portfolio_return, benchmark_return)
            sharpe = portfolio.calculate_sharpe_ratio()
            max_drawdown = portfolio.calculate_max_drawdown(portfolio_value)
            beta = portfolio.calculate_beta(benchmark)

            db_s = Database()
            sector_map = db_s.get_sectors(tickers)
            db_s.close()
            sector_weights = {}
            for t, w in zip(tickers, weights):
                sector = sector_map.get(t, "Other")
                sector_weights[sector] = sector_weights.get(sector, 0) + w

            individual_values = portfolio.calculate_individual_values(initial_investment) if len(tickers) > 1 else None
            annual_returns = portfolio.calculate_annual_returns()
            optimal_weights = portfolio.optimize_portfolio() if len(tickers) > 1 else None
            simulation_df = portfolio.simulate_monte_carlo(initial_investment)
            frontier_df = portfolio.calculate_efficient_frontier() if len(tickers) > 1 else None
            corr_matrix = portfolio.calculate_correlation() if len(tickers) > 1 else None
            dividend_df, portfolio_yield, total_income = portfolio.calculate_dividend_income(initial_investment)

        st.session_state["res"] = {
            "portfolio": portfolio,
            "portfolio_value": portfolio_value,
            "benchmark_value": benchmark_value,
            "portfolio_return": portfolio_return,
            "benchmark_return": benchmark_return,
            "outperformance": outperformance,
            "sharpe": sharpe,
            "max_drawdown": max_drawdown,
            "beta": beta,
            "volatility": volatility,
            "tickers": tickers,
            "weights": weights,
            "initial_investment": initial_investment,
            "sector_weights": sector_weights,
            "individual_values": individual_values,
            "annual_returns": annual_returns,
            "optimal_weights": optimal_weights,
            "simulation_df": simulation_df,
            "frontier_df": frontier_df,
            "corr_matrix": corr_matrix,
            "dividend_df": dividend_df,
            "portfolio_yield": portfolio_yield,
            "total_income": total_income,
        }
        st.session_state.pop("dca_res", None)

    if "res" in st.session_state:
        r = st.session_state["res"]
        portfolio = r["portfolio"]
        portfolio_value = r["portfolio_value"]
        benchmark_value = r["benchmark_value"]
        portfolio_return = r["portfolio_return"]
        benchmark_return = r["benchmark_return"]
        outperformance = r["outperformance"]
        sharpe = r["sharpe"]
        max_drawdown = r["max_drawdown"]
        beta = r["beta"]
        volatility = r["volatility"]
        tickers = r["tickers"]
        weights = r["weights"]
        initial_investment = r["initial_investment"]
        sector_weights = r["sector_weights"]
        individual_values = r["individual_values"]
        annual_returns = r["annual_returns"]
        optimal_weights = r["optimal_weights"]
        simulation_df = r["simulation_df"]
        frontier_df = r["frontier_df"]
        corr_matrix = r["corr_matrix"]
        dividend_df = r["dividend_df"]
        portfolio_yield = r["portfolio_yield"]
        total_income = r["total_income"]

        visualizer = Visualizer()

        # ── Chart ──────────────────────────────────────────────────────────────
        fig = visualizer.plot_comparison(portfolio_value, benchmark_value)
        st.plotly_chart(fig, use_container_width=True)

        # ── Metrics ────────────────────────────────────────────────────────────
        st.subheader("Portfolio Summary")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Initial Investment", f"€{initial_investment:,.2f}")
        col2.metric("Final Value", f"€{portfolio_value.iloc[-1]:,.2f}")
        col3.metric("Portfolio Return", f"{portfolio_return:.2%}")
        col4.metric("Benchmark Return", f"{benchmark_return:.2%}")

        col5, col6, col7, col8, col9 = st.columns(5)
        col5.metric("Outperformance", f"{outperformance:.2%}")
        col6.metric("Volatility", f"{volatility:.2%}")
        col7.metric("Sharpe Ratio", f"{sharpe:.2f}")
        col8.metric("Max Drawdown", f"{max_drawdown:.2%}")
        col9.metric("Beta", f"{beta:.2f}")

        # ── Sector Allocation ──────────────────────────────────────────────────
        st.subheader("Sector Allocation")
        sector_fig = visualizer.plot_sector_allocation(sector_weights)
        st.plotly_chart(sector_fig, use_container_width=True)

        # ── Dividend Analysis ──────────────────────────────────────────────────
        st.subheader("Dividend Analysis")
        div_col1, div_col2, div_col3 = st.columns(3)
        div_col1.metric("Portfolio Dividend Yield", f"{portfolio_yield:.2%}")
        div_col2.metric("Est. Annual Income", f"€{total_income:,.2f}")
        div_col3.metric("Est. Monthly Income", f"€{total_income / 12:,.2f}")

        if total_income > 0:
            div_fig = visualizer.plot_dividend_income(dividend_df)
            st.plotly_chart(div_fig, use_container_width=True)
        else:
            st.info("None of the selected stocks pay dividends.")

        # ── Individual Stock Performance ───────────────────────────────────────
        if individual_values is not None:
            st.subheader("Individual Stock Performance")
            individual_fig = visualizer.plot_individual_stocks(individual_values)
            st.plotly_chart(individual_fig, use_container_width=True)

        # ── Annual Returns ─────────────────────────────────────────────────────
        st.subheader("Annual Returns")
        annual_fig = visualizer.plot_annual_returns(annual_returns)
        st.plotly_chart(annual_fig, use_container_width=True)

        # ── Risk Warnings ──────────────────────────────────────────────────────
        show_risk_warnings(max_drawdown, sharpe, outperformance, beta)

        # ── Markowitz Optimization ─────────────────────────────────────────────
        if optimal_weights is not None:
            st.subheader("Markowitz Portfolio Optimization")
            opt_col1, opt_col2 = st.columns([1, 2])
            with opt_col1:
                st.markdown("**Optimal Weights:**")
                for ticker, weight in optimal_weights.items():
                    st.metric(ticker, f"{weight:.1%}")
            with opt_col2:
                opt_fig = go.Figure(go.Pie(
                    labels=list(optimal_weights.keys()),
                    values=list(optimal_weights.values()),
                    hole=0.4,
                ))
                opt_fig.update_layout(title="Optimal Allocation", margin=dict(t=40, b=0, l=0, r=0))
                st.plotly_chart(opt_fig, use_container_width=True)

        # ── Monte Carlo Simulation ─────────────────────────────────────────────
        st.subheader("Monte Carlo Simulation")
        monte_fig = visualizer.plot_monte_carlo(simulation_df, initial_investment)
        st.plotly_chart(monte_fig, use_container_width=True)

        final_values = simulation_df.iloc[-1]
        mean_val = final_values.mean()
        best_val = final_values.quantile(0.95)
        worst_val = final_values.quantile(0.05)

        mc_col1, mc_col2, mc_col3 = st.columns(3)
        mc_col1.metric("Mean Final Value", f"€{mean_val:,.2f}", delta=format_delta(mean_val, initial_investment))
        mc_col2.metric("Best Case (95th percentile)", f"€{best_val:,.2f}", delta=format_delta(best_val, initial_investment))
        mc_col3.metric("Worst Case (5th percentile)", f"€{worst_val:,.2f}", delta=format_delta(worst_val, initial_investment))

        # ── Efficient Frontier ─────────────────────────────────────────────────
        if frontier_df is not None:
            st.subheader("Efficient Frontier")
            frontier_fig = visualizer.plot_efficient_frontier(frontier_df, tickers)
            st.plotly_chart(frontier_fig, use_container_width=True)

        # ── Correlation Matrix ─────────────────────────────────────────────────
        if corr_matrix is not None:
            st.subheader("Correlation Matrix")
            corr_fig = visualizer.plot_correlation(corr_matrix)
            st.plotly_chart(corr_fig, use_container_width=True)

        # ── DCA Simulator ─────────────────────────────────────────────────────
        st.subheader("Dollar Cost Averaging Simulator")
        st.caption("Compare investing a fixed amount every month vs. investing the total sum upfront.")

        monthly_amount = st.number_input("Monthly Investment (€)", min_value=1.0, value=200.0, step=50.0)

        if st.button("Simulate DCA", use_container_width=True):
            dca_series, lump_sum_series, total_invested = portfolio.calculate_dca(monthly_amount)
            st.session_state["dca_res"] = {
                "dca_series": dca_series,
                "lump_sum_series": lump_sum_series,
                "total_invested": total_invested,
            }

        if "dca_res" in st.session_state:
            dr = st.session_state["dca_res"]
            dca_fig = visualizer.plot_dca(dr["dca_series"], dr["lump_sum_series"], dr["total_invested"])
            st.plotly_chart(dca_fig, use_container_width=True)

            dca_final = dr["dca_series"].iloc[-1]
            ls_final = dr["lump_sum_series"].iloc[-1]
            total_invested = dr["total_invested"]

            dca_col1, dca_col2, dca_col3 = st.columns(3)
            dca_col1.metric("Total Invested", f"€{total_invested:,.2f}")
            dca_col2.metric("DCA Final Value", f"€{dca_final:,.2f}", delta=format_delta(dca_final, total_invested))
            dca_col3.metric("Lump Sum Final Value", f"€{ls_final:,.2f}", delta=format_delta(ls_final, total_invested))

            diff = abs(dca_final - ls_final)
            if dca_final > ls_final:
                st.success(f"DCA outperformed Lump Sum by €{diff:,.2f} over this period.")
            else:
                st.info(f"Lump Sum outperformed DCA by €{diff:,.2f} over this period.")

        # ── Download ───────────────────────────────────────────────────────────
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

# ── Stock Analysis Tab ─────────────────────────────────────────────────────────
with tab_stock:
    st.subheader("Stock Fundamental Analysis")

    db_sa = Database()
    all_stocks_sa = db_sa.get_all_stocks()
    db_sa.close()

    stock_options_sa = [f"{name} ({ticker})" for ticker, name, _ in all_stocks_sa]
    selected_stock = st.selectbox("Select a Stock", options=stock_options_sa)
    run_analysis = st.button("Run Analysis", use_container_width=True)

    if run_analysis and selected_stock:
        stock_ticker = selected_stock.split("(")[-1].rstrip(")")

        with st.spinner(f"Loading fundamentals for {stock_ticker}..."):
            fa = FundamentalAnalysis(stock_ticker)
            scores, checklist = score_fundamentals(fa)

        visualizer_sa = Visualizer()

        col_chart, col_check = st.columns([1, 1])

        with col_chart:
            radar_fig = visualizer_sa.plot_asset_assessment(scores)
            st.plotly_chart(radar_fig, use_container_width=True)

        with col_check:
            st.markdown("**Financial Health Checklist**")
            for item in checklist:
                icon = "✅" if item["passed"] else "❌"
                st.markdown(f"{icon} **{item['description']}** — {item['value']}")

        st.divider()
        summary_text, summary_level = generate_summary(scores, checklist)
        st.subheader("Summary")
        if summary_level == "success":
            st.success(summary_text)
        elif summary_level == "warning":
            st.warning(summary_text)
        elif summary_level == "error":
            st.error(summary_text)
        else:
            st.info(summary_text)

        st.divider()
        st.subheader("Dividend History")
        dividends = fa.dividend_history()
        if not dividends.empty:
            div_hist_fig = visualizer_sa.plot_dividend_history(dividends)
            st.plotly_chart(div_hist_fig, use_container_width=True)
            info = fa._info
            div_yield = info.get("dividendYield")
            div_rate = info.get("dividendRate")
            payout = info.get("payoutRatio")
            dh_col1, dh_col2, dh_col3 = st.columns(3)
            dh_col1.metric("Dividend Yield", f"{div_yield:.2%}" if div_yield else "N/A")
            dh_col2.metric("Annual Dividend Rate", f"${div_rate:.2f}" if div_rate else "N/A")
            dh_col3.metric("Payout Ratio", f"{payout:.2%}" if payout else "N/A")
        else:
            st.info("This stock does not pay dividends.")

        st.divider()
        st.subheader("Latest News")
        news = fa.get_news()
        if news:
            for article in news:
                st.markdown(f"**[{article['title']}]({article['link']})**")
                st.caption(f"{article['publisher']} · {article['date']}")
                st.divider()
        else:
            st.info("No recent news found for this stock.")
