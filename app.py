import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date, timedelta
import yfinance as yf
from src.stock import Stock
from src.portfolio import Portfolio
from src.visualizer import Visualizer
from src.database import Database
from src.fundamentals import FundamentalAnalysis
from src.technical import TechnicalAnalysis
from src.report import generate_report
from src.etf import ETFAnalysis


def calculate_portfolio_score(sharpe, max_drawdown, outperformance, sector_weights):
    if sharpe < 0:
        sharpe_score = 0.0
    elif sharpe < 0.5:
        sharpe_score = 0.5
    elif sharpe < 1.0:
        sharpe_score = 1.0
    elif sharpe < 1.5:
        sharpe_score = 1.5
    else:
        sharpe_score = 2.0

    dd = abs(max_drawdown)
    if dd > 0.40:
        dd_score = 0.0
    elif dd > 0.25:
        dd_score = 0.5
    elif dd > 0.15:
        dd_score = 1.0
    else:
        dd_score = 1.5

    n_sectors = len(sector_weights)
    if n_sectors == 1:
        div_score = 0.0
    elif n_sectors == 2:
        div_score = 0.35
    elif n_sectors == 3:
        div_score = 0.65
    else:
        div_score = 1.0

    if outperformance < -0.05:
        out_score = 0.0
    elif outperformance < 0:
        out_score = 0.15
    elif outperformance < 0.05:
        out_score = 0.35
    else:
        out_score = 0.5

    total = sharpe_score + dd_score + div_score + out_score
    return total, sharpe_score, dd_score, div_score, out_score


def portfolio_verdict(score):
    if score >= 4.5:
        return "Excellent Portfolio ✅", "success"
    elif score >= 3.5:
        return "Good Portfolio 👍", "success"
    elif score >= 2.5:
        return "Average Portfolio 📊", "info"
    elif score >= 1.5:
        return "Below Average ⚠️", "warning"
    else:
        return "Needs Improvement ❌", "error"


def score_to_stars(score):
    filled = round(score)
    return "⭐" * filled + "☆" * (5 - filled)


def show_diversification_warnings(sector_weights, corr_matrix, tickers, weights):
    warnings_found = False

    max_sector = max(sector_weights, key=sector_weights.get)
    max_sector_w = sector_weights[max_sector]
    if max_sector_w > 0.60:
        st.error(f"High sector concentration: {max_sector_w:.0%} of your portfolio is in **{max_sector}**. Consider spreading across more sectors.")
        warnings_found = True
    elif max_sector_w > 0.40:
        st.warning(f"Moderate sector concentration: {max_sector_w:.0%} in **{max_sector}**.")
        warnings_found = True

    max_w = max(weights)
    max_ticker = tickers[weights.index(max_w)]
    if max_w > 0.50:
        st.error(f"**{max_ticker}** represents {max_w:.0%} of your portfolio — very high single-stock risk.")
        warnings_found = True
    elif max_w > 0.35:
        st.warning(f"**{max_ticker}** represents {max_w:.0%} of your portfolio.")
        warnings_found = True

    if corr_matrix is not None and len(tickers) > 1:
        vals = corr_matrix.values
        upper = vals[np.triu_indices_from(vals, k=1)]
        avg_corr = upper.mean()
        if avg_corr > 0.80:
            st.error(f"Very high average correlation ({avg_corr:.2f}) — your stocks move almost identically. Diversification benefit is minimal.")
            warnings_found = True
        elif avg_corr > 0.65:
            st.warning(f"High average correlation ({avg_corr:.2f}) — your stocks tend to move together.")
            warnings_found = True

    if len(tickers) < 3:
        st.warning(f"Only {len(tickers)} stock(s) in your portfolio. Consider adding more holdings for better diversification.")
        warnings_found = True

    if not warnings_found:
        st.success("Your portfolio appears well diversified across sectors, stocks, and shows healthy correlation between holdings.")


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


def analyze_real_portfolio(transactions_df):
    rows = []
    value_series_list = []
    spy_series_list = []

    # Download SPY once from the earliest purchase date
    min_date = str(pd.to_datetime(transactions_df["Purchase Date"]).min().date())
    _spy_raw = yf.download("SPY", start=min_date, progress=False, auto_adjust=True)
    spy_all = _spy_raw["Close"].squeeze().dropna()
    if hasattr(spy_all.index, "tz") and spy_all.index.tz is not None:
        spy_all.index = spy_all.index.tz_convert(None)

    for _, row in transactions_df.iterrows():
        stock_str = str(row["Stock"])
        ticker = stock_str.split("(")[-1].rstrip(")").strip().upper()
        company = stock_str.split(" (")[0].strip()
        purchase_date = str(row["Purchase Date"])
        amount = float(row["Amount (EUR)"])

        try:
            data = yf.download(ticker, start=purchase_date, progress=False, auto_adjust=True)
            if data.empty or len(data) < 2:
                st.warning(f"No data for **{ticker}** from {purchase_date}. Skipping.")
                continue

            close = data["Close"].squeeze().dropna()
            if hasattr(close.index, "tz") and close.index.tz is not None:
                close.index = close.index.tz_convert(None)

            price_at_buy = float(close.iloc[0])
            shares = amount / price_at_buy
            val_series = close * shares
            val_series.name = f"{ticker}_{len(rows)}"

            # Slice SPY from this transaction's purchase date
            spy_close = spy_all[spy_all.index >= pd.Timestamp(purchase_date)]
            if spy_close.empty:
                spy_close = spy_all
            spy_shares = amount / float(spy_close.iloc[0])
            spy_val = spy_close * spy_shares
            spy_val.name = f"SPY_{len(rows)}"

            current_val = float(val_series.iloc[-1])
            profit = current_val - amount

            rows.append({
                "Company": company,
                "Ticker": ticker,
                "Purchase Date": purchase_date,
                "Invested (EUR)": amount,
                "Shares": round(shares, 4),
                "Buy Price": round(price_at_buy, 2),
                "Current Price": round(float(close.iloc[-1]), 2),
                "Current Value (EUR)": round(current_val, 2),
                "Profit / Loss (EUR)": round(profit, 2),
                "Return": profit / amount,
            })
            value_series_list.append(val_series)
            spy_series_list.append(spy_val)

        except Exception as e:
            st.warning(f"Error loading {ticker}: {e}")

    if not rows:
        return None, None, None, None

    results_df = pd.DataFrame(rows)

    portfolio_series = pd.concat(value_series_list, axis=1).ffill().fillna(0).sum(axis=1)
    spy_series = pd.concat(spy_series_list, axis=1).ffill().fillna(0).sum(axis=1)

    # Individual values per ticker (sum duplicate tickers)
    ind_by_ticker = {}
    for i, row_data in enumerate(rows):
        t = row_data["Ticker"]
        s = value_series_list[i]
        if t in ind_by_ticker:
            ind_by_ticker[t] = ind_by_ticker[t].add(s, fill_value=0)
        else:
            ind_by_ticker[t] = s.copy()

    individual_values = (
        pd.concat(ind_by_ticker, axis=1).ffill().fillna(0)
        if len(ind_by_ticker) > 1 else None
    )

    return results_df, portfolio_series, spy_series, individual_values


# ── App ────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Portfolio Analyzer", layout="wide")

st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 1.35rem; font-weight: 700; }
[data-testid="stMetricLabel"] { font-size: 0.8rem; opacity: 0.7; }
hr { border-color: rgba(128,128,128,0.15) !important; margin: 1.2rem 0 !important; }
.stDataFrame { border-radius: 8px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

st.title("Portfolio Analyzer")

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("My Portfolio")
    st.caption("Add your real stock purchases below.")

    db = Database()
    all_stocks = db.get_all_stocks()
    db.close()
    stock_display = sorted([f"{n} ({t})" for t, n, _ in all_stocks])

    default_tx = pd.DataFrame({
        "Stock": ["Apple (AAPL)", "NVIDIA (NVDA)"],
        "Purchase Date": [
            date.today() - timedelta(days=365),
            date.today() - timedelta(days=730),
        ],
        "Amount (EUR)": [1000.0, 500.0],
    })

    transactions = st.data_editor(
        default_tx,
        num_rows="dynamic",
        column_config={
            "Stock": st.column_config.SelectboxColumn(
                "Stock", options=stock_display, required=True
            ),
            "Purchase Date": st.column_config.DateColumn(
                "Purchase Date", required=True
            ),
            "Amount (EUR)": st.column_config.NumberColumn(
                "Amount (EUR)", min_value=1.0, step=100.0
            ),
        },
        use_container_width=True,
    )

    analyze = st.button("Analyze Portfolio", use_container_width=True)

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_portfolio, tab_markowitz, tab_stock = st.tabs(
    ["Portfolio Analysis", "Markowitz Optimization", "Stock Analysis"]
)

# ── Portfolio Analysis Tab ─────────────────────────────────────────────────────
with tab_portfolio:
    if analyze:
        valid_tx = transactions.dropna(subset=["Stock", "Purchase Date", "Amount (EUR)"])
        valid_tx = valid_tx[valid_tx["Amount (EUR)"] > 0]

        if valid_tx.empty:
            st.error("Please add at least one stock purchase.")
            st.stop()

        with st.spinner("Downloading market data and calculating..."):
            results_df, portfolio_series, spy_series, individual_values = analyze_real_portfolio(valid_tx)

            if results_df is None:
                st.error("Could not load data for any of the specified stocks.")
                st.stop()

            total_invested = results_df["Invested (EUR)"].sum()
            total_current = results_df["Current Value (EUR)"].sum()
            portfolio_return = (total_current - total_invested) / total_invested
            benchmark_return = (float(spy_series.iloc[-1]) - total_invested) / total_invested
            outperformance = portfolio_return - benchmark_return

            # Risk metrics from actual portfolio series
            port_rets = portfolio_series.pct_change().dropna()
            volatility = float(port_rets.std() * np.sqrt(252))
            rf_daily = 0.05 / 252
            excess = port_rets - rf_daily
            sharpe = float((excess.mean() / excess.std()) * np.sqrt(252)) if excess.std() > 0 else 0.0
            peak = portfolio_series.cummax()
            max_drawdown = float(((portfolio_series - peak) / peak).min())

            spy_rets = spy_series.pct_change().dropna()
            p_aligned, s_aligned = port_rets.align(spy_rets, join="inner")
            cov_matrix = np.cov(p_aligned, s_aligned)
            beta = float(cov_matrix[0, 1] / cov_matrix[1, 1]) if cov_matrix[1, 1] > 0 else 1.0

            annual_returns = portfolio_series.resample("YE").last().pct_change().dropna()

            # Unique tickers with weights from invested amounts for Portfolio object
            ticker_amounts = results_df.groupby("Ticker")["Invested (EUR)"].sum()
            tickers = list(ticker_amounts.index)
            weights = [float(ticker_amounts[t] / ticker_amounts.sum()) for t in tickers]
            min_date = str(pd.to_datetime(valid_tx["Purchase Date"]).min().date())

            stocks = [Stock(t) for t in tickers]
            portfolio = Portfolio(stocks=stocks, weights=weights)
            portfolio.load_all_data(
                start=min_date, end=date.today().strftime("%Y-%m-%d")
            )
            portfolio.calculate_portfolio_returns()

            db_s = Database()
            sector_map = db_s.get_sectors(tickers)
            db_s.close()
            sector_weights = {}
            for t, w in zip(tickers, weights):
                sector = sector_map.get(t, "Other")
                sector_weights[sector] = sector_weights.get(sector, 0) + w

            score_total, score_sharpe, score_dd, score_div, score_out = calculate_portfolio_score(
                sharpe, max_drawdown, outperformance, sector_weights
            )

            simulation_df = portfolio.simulate_monte_carlo(total_invested)
            frontier_df = portfolio.calculate_efficient_frontier() if len(tickers) > 1 else None
            corr_matrix = portfolio.calculate_correlation() if len(tickers) > 1 else None
            dividend_df, portfolio_yield, total_income = portfolio.calculate_dividend_income(total_invested)

        st.session_state["res"] = {
            "results_df": results_df,
            "portfolio": portfolio,
            "portfolio_value": portfolio_series,
            "benchmark_value": spy_series,
            "portfolio_return": portfolio_return,
            "benchmark_return": benchmark_return,
            "outperformance": outperformance,
            "sharpe": sharpe,
            "max_drawdown": max_drawdown,
            "beta": beta,
            "volatility": volatility,
            "tickers": tickers,
            "weights": weights,
            "initial_investment": total_invested,
            "sector_weights": sector_weights,
            "individual_values": individual_values,
            "annual_returns": annual_returns,
            "simulation_df": simulation_df,
            "frontier_df": frontier_df,
            "corr_matrix": corr_matrix,
            "dividend_df": dividend_df,
            "portfolio_yield": portfolio_yield,
            "total_income": total_income,
            "score_total": score_total,
            "score_sharpe": score_sharpe,
            "score_dd": score_dd,
            "score_div": score_div,
            "score_out": score_out,
        }
        st.session_state.pop("dca_res", None)
        st.session_state.pop("markowitz_res", None)
        st.session_state.pop("pdf_bytes", None)

    if "res" in st.session_state:
        r = st.session_state["res"]
        results_df = r["results_df"]
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
        simulation_df = r["simulation_df"]
        frontier_df = r["frontier_df"]
        corr_matrix = r["corr_matrix"]
        dividend_df = r["dividend_df"]
        portfolio_yield = r["portfolio_yield"]
        total_income = r["total_income"]
        score_total = r["score_total"]
        score_sharpe = r["score_sharpe"]
        score_dd = r["score_dd"]
        score_div = r["score_div"]
        score_out = r["score_out"]

        visualizer = Visualizer()

        # ── Holdings Breakdown ─────────────────────────────────────────────────
        st.subheader("Holdings")
        display_df = results_df[["Company", "Ticker", "Purchase Date", "Invested (EUR)",
                                  "Shares", "Buy Price", "Current Price",
                                  "Current Value (EUR)", "Profit / Loss (EUR)", "Return"]].copy()
        styled = (
            display_df.style
            .format({
                "Invested (EUR)":       "€{:.2f}",
                "Shares":               "{:.4f}",
                "Buy Price":            "${:.2f}",
                "Current Price":        "${:.2f}",
                "Current Value (EUR)":  "€{:.2f}",
                "Profit / Loss (EUR)":  lambda x: f"+€{x:.2f}" if x >= 0 else f"-€{abs(x):.2f}",
                "Return":               "{:+.2%}",
            })
            .map(
                lambda v: "color: #2ECC71; font-weight: 600" if isinstance(v, (int, float)) and v >= 0
                          else ("color: #E74C3C; font-weight: 600" if isinstance(v, (int, float)) else ""),
                subset=["Profit / Loss (EUR)", "Return"],
            )
        )
        st.dataframe(styled, use_container_width=True, hide_index=True)

        st.divider()

        # ── Portfolio Score ────────────────────────────────────────────────────
        verdict, verdict_level = portfolio_verdict(score_total)
        stars = score_to_stars(score_total)

        sc1, sc2, sc3 = st.columns([1, 1, 2])
        sc1.metric("Portfolio Score", f"{score_total:.1f} / 5.0")
        sc2.markdown(f"<h2 style='margin:0'>{stars}</h2>", unsafe_allow_html=True)
        with sc3:
            if verdict_level == "success":
                st.success(verdict)
            elif verdict_level == "warning":
                st.warning(verdict)
            elif verdict_level == "error":
                st.error(verdict)
            else:
                st.info(verdict)

        b1, b2, b3, b4 = st.columns(4)
        b1.metric("Sharpe", f"{score_sharpe:.1f} / 2.0")
        b2.metric("Risk (Drawdown)", f"{score_dd:.2f} / 1.5")
        b3.metric("Diversification", f"{score_div:.2f} / 1.0")
        b4.metric("vs S&P 500", f"{score_out:.2f} / 0.5")

        st.divider()

        # ── Chart ──────────────────────────────────────────────────────────────
        fig = visualizer.plot_comparison(portfolio_value, benchmark_value)
        st.plotly_chart(fig, use_container_width=True)

        # ── Metrics ────────────────────────────────────────────────────────────
        st.subheader("Portfolio Summary")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Invested", f"€{initial_investment:,.2f}")
        col2.metric("Current Value", f"€{results_df['Current Value (EUR)'].sum():,.2f}")
        col3.metric("Portfolio Return", f"{portfolio_return:.2%}")
        col4.metric("S&P 500 Return", f"{benchmark_return:.2%}")

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

        # ── Diversification Analysis ───────────────────────────────────────────
        st.subheader("Diversification Analysis")
        show_diversification_warnings(sector_weights, corr_matrix, tickers, weights)

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
            dca_series, lump_sum_series, total_invested_dca = portfolio.calculate_dca(monthly_amount)
            st.session_state["dca_res"] = {
                "dca_series": dca_series,
                "lump_sum_series": lump_sum_series,
                "total_invested": total_invested_dca,
            }

        if "dca_res" in st.session_state:
            dr = st.session_state["dca_res"]
            dca_fig = visualizer.plot_dca(dr["dca_series"], dr["lump_sum_series"], dr["total_invested"])
            st.plotly_chart(dca_fig, use_container_width=True)

            dca_final = dr["dca_series"].iloc[-1]
            ls_final = dr["lump_sum_series"].iloc[-1]
            total_invested_dca = dr["total_invested"]

            dca_col1, dca_col2, dca_col3 = st.columns(3)
            dca_col1.metric("Total Invested", f"€{total_invested_dca:,.2f}")
            dca_col2.metric("DCA Final Value", f"€{dca_final:,.2f}", delta=format_delta(dca_final, total_invested_dca))
            dca_col3.metric("Lump Sum Final Value", f"€{ls_final:,.2f}", delta=format_delta(ls_final, total_invested_dca))

            diff = abs(dca_final - ls_final)
            if dca_final > ls_final:
                st.success(f"DCA outperformed Lump Sum by €{diff:,.2f} over this period.")
            else:
                st.info(f"Lump Sum outperformed DCA by €{diff:,.2f} over this period.")

        # ── Export ─────────────────────────────────────────────────────────────
        st.subheader("Export Results")

        values_df = pd.DataFrame({
            "Portfolio Value (€)": portfolio_value,
            "S&P 500 Equivalent (€)": benchmark_value,
        })

        summary = {
            "Total Invested (€)": initial_investment,
            "Current Value (€)": results_df["Current Value (EUR)"].sum(),
            "Portfolio Return": f"{portfolio_return:.2%}",
            "S&P 500 Return": f"{benchmark_return:.2%}",
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

        st.divider()
        if st.button("Generate PDF Report", use_container_width=True, type="primary"):
            with st.spinner("Generating PDF report — this may take a few seconds..."):
                report_data = {**r, "visualizer": visualizer}
                st.session_state["pdf_bytes"] = generate_report(report_data)

        if "pdf_bytes" in st.session_state:
            st.download_button(
                label="Download PDF Report",
                data=st.session_state["pdf_bytes"],
                file_name=f"portfolio_report_{date.today()}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

# ── Markowitz Optimization Tab ────────────────────────────────────────────────
with tab_markowitz:
    st.subheader("Markowitz Portfolio Optimization")

    if "res" not in st.session_state:
        st.info("Run a portfolio analysis first from the Portfolio Analysis tab.")
    else:
        r = st.session_state["res"]
        portfolio = r["portfolio"]
        tickers = r["tickers"]

        if len(tickers) < 2:
            st.warning("Markowitz optimization requires at least 2 stocks.")
        else:
            st.caption("Find the optimal allocation that maximizes the Sharpe Ratio given your constraints.")

            mk_col1, mk_col2 = st.columns(2)
            max_w_pct = mk_col1.slider("Max weight per stock (%)", min_value=10, max_value=100, value=100, step=5, format="%d%%")
            min_w_pct = mk_col2.slider("Min weight per stock (%)", min_value=0, max_value=20, value=0, step=1, format="%d%%")

            max_w = max_w_pct / 100
            min_w = min_w_pct / 100
            n = len(tickers)

            feasible = (n * max_w >= 1.0) and (n * min_w <= 1.0)
            if not feasible:
                st.warning(
                    f"Infeasible: {n} stocks × {max_w_pct}% max = {n * max_w_pct}% < 100%. "
                    "Increase max weight or reduce min weight."
                )

            if st.button("Optimize", use_container_width=True, disabled=not feasible):
                with st.spinner("Optimizing weights..."):
                    try:
                        optimal_weights = portfolio.optimize_portfolio(min_weight=min_w, max_weight=max_w)
                        st.session_state["markowitz_res"] = optimal_weights
                    except ValueError as e:
                        st.error(str(e))

            if "markowitz_res" in st.session_state:
                optimal_weights = st.session_state["markowitz_res"]
                st.divider()
                opt_col1, opt_col2 = st.columns([1, 2])
                with opt_col1:
                    st.markdown("**Optimal Weights:**")
                    for t, w in optimal_weights.items():
                        st.metric(t, f"{w:.1%}")
                with opt_col2:
                    opt_fig = go.Figure(go.Pie(
                        labels=list(optimal_weights.keys()),
                        values=list(optimal_weights.values()),
                        hole=0.4,
                    ))
                    opt_fig.update_layout(title="Optimal Allocation", margin=dict(t=40, b=0, l=0, r=0))
                    st.plotly_chart(opt_fig, use_container_width=True)

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

        db_check = Database()
        sector_check = db_check.get_sector(stock_ticker)
        db_check.close()
        is_etf = bool(sector_check and sector_check.startswith("ETF"))

        with st.spinner(f"Loading data for {stock_ticker}..."):
            if is_etf:
                etf = ETFAnalysis(stock_ticker)
                prices = etf.get_price_history()
                ta = TechnicalAnalysis(prices)
                st.session_state["stock_res"] = {
                    "is_etf": True,
                    "etf": etf,
                    "stock_ticker": stock_ticker,
                    "sector": sector_check,
                    "prices": prices,
                    "tech_signals": ta.signals(),
                    "sma50": ta.sma(50),
                    "sma200": ta.sma(200),
                    "bb_upper": ta.bollinger_bands()[0],
                    "bb_lower": ta.bollinger_bands()[2],
                    "rsi_series": ta.rsi(),
                }
            else:
                fa = FundamentalAnalysis(stock_ticker)
                scores, checklist = score_fundamentals(fa)
                db_peer = Database()
                sector = db_peer.get_sector(stock_ticker)
                peers = db_peer.get_stocks_by_sector(sector, stock_ticker, limit=3)
                db_peer.close()
                prices = fa.get_price_history()
                ta = TechnicalAnalysis(prices)
                st.session_state["stock_res"] = {
                    "is_etf": False,
                    "fa": fa,
                    "scores": scores,
                    "checklist": checklist,
                    "stock_ticker": stock_ticker,
                    "sector": sector,
                    "peers": peers,
                    "prices": prices,
                    "tech_signals": ta.signals(),
                    "sma50": ta.sma(50),
                    "sma200": ta.sma(200),
                    "bb_upper": ta.bollinger_bands()[0],
                    "bb_lower": ta.bollinger_bands()[2],
                    "rsi_series": ta.rsi(),
                }
        st.session_state.pop("peer_res", None)

    if "stock_res" in st.session_state:
        sr = st.session_state["stock_res"]
        stock_ticker = sr["stock_ticker"]
        prices      = sr["prices"]
        tech_signals = sr["tech_signals"]
        sma50       = sr["sma50"]
        sma200      = sr["sma200"]
        bb_upper    = sr["bb_upper"]
        bb_lower    = sr["bb_lower"]
        rsi_series  = sr["rsi_series"]

        visualizer_sa = Visualizer()

        # ── ETF Analysis ───────────────────────────────────────────────────────
        if sr["is_etf"]:
            etf = sr["etf"]
            st.subheader(etf.fund_name())
            st.caption(f"{etf.fund_family()}  ·  {etf.category()}  ·  {sr['sector']}")

            # Key metrics
            expense = etf.expense_ratio()
            aum = etf.total_assets()
            div_y = etf.dividend_yield()
            beta_v = etf.beta()

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Expense Ratio", f"{expense:.3%}" if expense else "N/A")
            k2.metric("AUM", f"${aum/1e9:.1f}B" if aum else "N/A")
            k3.metric("Dividend Yield", f"{div_y:.2%}" if div_y else "N/A")
            k4.metric("Beta (3Y)", f"{beta_v:.2f}" if beta_v else "N/A")

            st.divider()

            # Performance returns
            ytd = etf.ytd_return()
            ret3 = etf.three_year_return()
            ret5 = etf.five_year_return()

            p1, p2, p3 = st.columns(3)
            p1.metric("YTD Return",       f"{ytd:.2%}"  if ytd  else "N/A")
            p2.metric("3Y Avg Return",    f"{ret3:.2%}" if ret3 else "N/A")
            p3.metric("5Y Avg Return",    f"{ret5:.2%}" if ret5 else "N/A")

            returns_chart = {
                "YTD": ytd,
                "3Y Avg": ret3,
                "5Y Avg": ret5,
            }
            if any(v is not None for v in returns_chart.values()):
                etf_ret_fig = visualizer_sa.plot_etf_returns(returns_chart)
                st.plotly_chart(etf_ret_fig, use_container_width=True)

            st.divider()

            # 52-week range
            hi = etf.fifty_two_week_high()
            lo = etf.fifty_two_week_low()
            nav_price = etf.nav()
            r1, r2, r3 = st.columns(3)
            r1.metric("NAV / Price",     f"${nav_price:.2f}" if nav_price else "N/A")
            r2.metric("52-Week High",    f"${hi:.2f}" if hi else "N/A")
            r3.metric("52-Week Low",     f"${lo:.2f}" if lo else "N/A")

            st.divider()

            # Description
            desc = etf.description()
            if desc and desc != "No description available.":
                with st.expander("Fund Description"):
                    st.write(desc)

            # Dividend history
            st.subheader("Dividend History")
            dividends = etf.dividend_history()
            if not dividends.empty:
                div_hist_fig = visualizer_sa.plot_dividend_history(dividends)
                st.plotly_chart(div_hist_fig, use_container_width=True)
            else:
                st.info("This ETF does not pay dividends.")

        # ── Stock Fundamental Analysis ─────────────────────────────────────────
        else:
            fa = sr["fa"]
            scores = sr["scores"]
            checklist = sr["checklist"]
            sector = sr["sector"]
            peers = sr["peers"]

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

            # Peer Comparison
            st.subheader("Peer Comparison")
            if peers and sector:
                st.caption(f"Sector: {sector} — comparing with {', '.join(t for t, _ in peers)}")
                if st.button("Compare with Sector Peers", use_container_width=True):
                    with st.spinner("Loading peer data..."):
                        all_scores = {stock_ticker: scores}
                        peer_rows = []
                        for peer_ticker, _ in peers:
                            fa_peer = FundamentalAnalysis(peer_ticker)
                            peer_scores, _ = score_fundamentals(fa_peer)
                            all_scores[peer_ticker] = peer_scores
                            peer_rows.append({
                                "Ticker": peer_ticker,
                                "P/E": fa_peer.pe_ratio(),
                                "P/B": fa_peer.pb_ratio(),
                                "Profit Margin": fa_peer.profit_margin(),
                                "Debt/Equity": fa_peer.debt_to_equity(),
                                "EPS": fa_peer.eps(),
                            })
                    st.session_state["peer_res"] = {"all_scores": all_scores, "peer_rows": peer_rows}

                if "peer_res" in st.session_state:
                    pr = st.session_state["peer_res"]
                    peer_fig = visualizer_sa.plot_peer_comparison(pr["all_scores"])
                    st.plotly_chart(peer_fig, use_container_width=True)
                    selected_row = {
                        "Ticker": stock_ticker,
                        "P/E": fa.pe_ratio(),
                        "P/B": fa.pb_ratio(),
                        "Profit Margin": fa.profit_margin(),
                        "Debt/Equity": fa.debt_to_equity(),
                        "EPS": fa.eps(),
                    }
                    table_df = pd.DataFrame([selected_row] + pr["peer_rows"]).set_index("Ticker")
                    table_df["Profit Margin"] = table_df["Profit Margin"].apply(lambda x: f"{x:.1%}" if x else "N/A")
                    for col in ["P/E", "P/B", "Debt/Equity", "EPS"]:
                        table_df[col] = table_df[col].apply(lambda x: f"{x:.2f}" if x else "N/A")
                    st.dataframe(table_df, use_container_width=True)
            else:
                st.info("No sector peers found in the database.")

            st.divider()
            st.subheader("Dividend History")
            dividends = fa.dividend_history()
            if not dividends.empty:
                div_hist_fig = visualizer_sa.plot_dividend_history(dividends)
                st.plotly_chart(div_hist_fig, use_container_width=True)
                div_yield = fa._info.get("dividendYield")
                div_rate  = fa._info.get("dividendRate")
                payout    = fa._info.get("payoutRatio")
                dh_col1, dh_col2, dh_col3 = st.columns(3)
                dh_col1.metric("Dividend Yield",      f"{div_yield:.2%}" if div_yield else "N/A")
                dh_col2.metric("Annual Dividend Rate", f"${div_rate:.2f}" if div_rate else "N/A")
                dh_col3.metric("Payout Ratio",         f"{payout:.2%}" if payout else "N/A")
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

        # ── Technical Analysis (both stocks and ETFs) ──────────────────────────
        st.divider()
        st.subheader("Technical Analysis")

        sig_cols = st.columns(3)
        for i, (label, value, description, signal_type) in enumerate(tech_signals):
            col = sig_cols[i % 3]
            if signal_type == "buy":
                col.success(f"**{label}**: {value}  \n{description}")
            elif signal_type == "sell":
                col.error(f"**{label}**: {value}  \n{description}")
            else:
                col.info(f"**{label}**: {value}  \n{description}")

        tech_fig = visualizer_sa.plot_technical(prices, sma50, sma200, bb_upper, bb_lower)
        st.plotly_chart(tech_fig, use_container_width=True)

        rsi_fig = visualizer_sa.plot_rsi(rsi_series)
        st.plotly_chart(rsi_fig, use_container_width=True)
