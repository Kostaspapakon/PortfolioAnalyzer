import os
import tempfile
from datetime import date

from fpdf import FPDF

BLUE = (33, 150, 243)
DARK_BLUE = (21, 101, 192)
GRAY = (120, 120, 120)
LIGHT = (248, 249, 250)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (76, 175, 80)
RED = (244, 67, 54)


class _PDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_fill_color(*BLUE)
            self.set_text_color(*WHITE)
            self.set_font("Helvetica", "B", 8)
            self.cell(0, 6, "PORTFOLIO ANALYZER  |  INVESTMENT REPORT", fill=True, align="C",
                      new_x="LMARGIN", new_y="NEXT")
            self.ln(3)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*GRAY)
        self.cell(0, 5,
                  f"Page {self.page_no()}  |  {date.today().strftime('%B %d, %Y')}  |  "
                  "For informational purposes only. Not financial advice.",
                  align="C")

    def section_title(self, title):
        self.set_fill_color(*BLUE)
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 8, f"  {title}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*BLACK)
        self.ln(4)

    def add_chart(self, fig, h=75):
        try:
            img_bytes = fig.to_image(format="png", width=900, height=int(h * 5), scale=1)
        except Exception:
            self.set_font("Helvetica", "I", 9)
            self.set_text_color(*GRAY)
            self.cell(0, h, "[Chart could not be rendered]", align="C", new_x="LMARGIN", new_y="NEXT")
            self.set_text_color(*BLACK)
            return
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(img_bytes)
            path = f.name
        try:
            self.image(path, x=self.l_margin, w=self.epw, h=h)
        finally:
            os.unlink(path)
        self.ln(4)

    def metric_boxes(self, items):
        w = self.epw / len(items)
        for label, _ in items:
            self.set_fill_color(*LIGHT)
            self.set_font("Helvetica", "", 8)
            self.set_text_color(*GRAY)
            self.cell(w, 5, label, align="C", fill=True)
        self.ln()
        for _, value in items:
            self.set_fill_color(*LIGHT)
            self.set_font("Helvetica", "B", 11)
            self.set_text_color(*BLACK)
            self.cell(w, 9, str(value), align="C", fill=True)
        self.ln(14)

    def two_col_table(self, rows, col_w=None):
        if col_w is None:
            col_w = self.epw / 2
        for label, value in rows:
            self.set_fill_color(*LIGHT)
            self.set_font("Helvetica", "", 9)
            self.set_text_color(*GRAY)
            self.cell(col_w, 6, label, fill=True)
            self.set_font("Helvetica", "B", 9)
            self.set_text_color(*BLACK)
            self.cell(col_w, 6, str(value), fill=True)
            self.ln()
        self.ln(4)


def generate_report(data: dict) -> bytes:
    tickers = data["tickers"]
    weights = data["weights"]
    initial = data["initial_investment"]
    portfolio_value = data["portfolio_value"]
    benchmark_value = data["benchmark_value"]
    portfolio_return = data["portfolio_return"]
    benchmark_return = data["benchmark_return"]
    outperformance = data["outperformance"]
    volatility = data["volatility"]
    sharpe = data["sharpe"]
    max_drawdown = data["max_drawdown"]
    beta = data["beta"]
    score_total = data["score_total"]
    score_sharpe = data["score_sharpe"]
    score_dd = data["score_dd"]
    score_div = data["score_div"]
    score_out = data["score_out"]
    sector_weights = data["sector_weights"]
    annual_returns = data["annual_returns"]
    simulation_df = data["simulation_df"]
    frontier_df = data.get("frontier_df")
    corr_matrix = data.get("corr_matrix")
    dividend_df = data["dividend_df"]
    portfolio_yield = data["portfolio_yield"]
    total_income = data["total_income"]
    viz = data["visualizer"]

    pdf = _PDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=18)

    # ── Cover Page ──────────────────────────────────────────────────────────────
    pdf.add_page()

    # Blue header band
    pdf.set_fill_color(*BLUE)
    pdf.rect(0, 0, 210, 65, "F")

    pdf.set_y(12)
    pdf.set_text_color(*WHITE)
    pdf.set_font("Helvetica", "B", 28)
    pdf.cell(0, 14, "Portfolio Analyzer", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 14)
    pdf.cell(0, 8, "Investment Report", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, f"Generated on {date.today().strftime('%B %d, %Y')}", align="C",
             new_x="LMARGIN", new_y="NEXT")

    # Score card
    pdf.set_y(74)
    pdf.set_text_color(*BLACK)
    filled = round(score_total)
    stars = "*" * filled + "-" * (5 - filled)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, f"Portfolio Score:  {score_total:.1f} / 5.0   [ {stars} ]",
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # Holdings table
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 7, "Portfolio Holdings", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    col_w = pdf.epw / 3
    pdf.set_fill_color(*BLUE)
    pdf.set_text_color(*WHITE)
    pdf.set_font("Helvetica", "B", 9)
    for h in ["Ticker", "Weight", "Allocated"]:
        pdf.cell(col_w, 7, h, align="C", fill=True)
    pdf.ln()

    pdf.set_text_color(*BLACK)
    for i, (ticker, weight) in enumerate(zip(tickers, weights)):
        fill = i % 2 == 0
        bg = LIGHT if fill else WHITE
        pdf.set_fill_color(*bg)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(col_w, 6, ticker, align="C", fill=fill)
        pdf.cell(col_w, 6, f"{weight:.1%}", align="C", fill=fill)
        pdf.cell(col_w, 6, f"EUR {initial * weight:,.2f}", align="C", fill=fill)
        pdf.ln()
    pdf.ln(8)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*GRAY)
    pdf.cell(0, 5, f"Initial Investment: EUR {initial:,.2f}", align="C")

    # ── Section 1: Performance ───────────────────────────────────────────────────
    pdf.add_page()
    pdf.section_title("1. Portfolio Performance")
    pdf.metric_boxes([
        ("Portfolio Return", f"{portfolio_return:.2%}"),
        ("Benchmark (S&P 500)", f"{benchmark_return:.2%}"),
        ("Outperformance", f"{outperformance:+.2%}"),
        ("Final Value", f"EUR {portfolio_value.iloc[-1]:,.0f}"),
    ])
    pdf.add_chart(viz.plot_comparison(portfolio_value, benchmark_value), h=78)

    pdf.section_title("Annual Returns")
    pdf.add_chart(viz.plot_annual_returns(annual_returns), h=68)

    # ── Section 2: Risk Analysis ─────────────────────────────────────────────────
    pdf.add_page()
    pdf.section_title("2. Risk Analysis")
    pdf.metric_boxes([
        ("Sharpe Ratio", f"{sharpe:.2f}"),
        ("Max Drawdown", f"{max_drawdown:.2%}"),
        ("Volatility", f"{volatility:.2%}"),
        ("Beta", f"{beta:.2f}"),
    ])

    pdf.section_title("Portfolio Score Breakdown")
    pdf.metric_boxes([
        ("Sharpe Score", f"{score_sharpe:.1f} / 2.0"),
        ("Risk Score", f"{score_dd:.2f} / 1.5"),
        ("Diversification", f"{score_div:.2f} / 1.0"),
        ("vs S&P 500", f"{score_out:.2f} / 0.5"),
    ])

    # ── Section 3: Sector Allocation ─────────────────────────────────────────────
    pdf.section_title("3. Sector Allocation")
    pdf.add_chart(viz.plot_sector_allocation(sector_weights), h=85)

    # ── Section 4: Correlation Matrix (if available) ─────────────────────────────
    if corr_matrix is not None:
        pdf.add_page()
        pdf.section_title("4. Correlation Matrix")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*GRAY)
        pdf.multi_cell(0, 5,
            "Values close to 1.0 mean stocks move together (low diversification benefit). "
            "Values close to 0 or negative mean stocks move independently (good diversification).")
        pdf.ln(3)
        pdf.set_text_color(*BLACK)
        pdf.add_chart(viz.plot_correlation(corr_matrix), h=90)

    # ── Section 5: Monte Carlo Simulation ────────────────────────────────────────
    pdf.add_page()
    pdf.section_title("5. Monte Carlo Simulation")
    final_vals = simulation_df.iloc[-1]
    pdf.metric_boxes([
        ("Mean Outcome", f"EUR {final_vals.mean():,.0f}"),
        ("Best Case (95th %ile)", f"EUR {final_vals.quantile(0.95):,.0f}"),
        ("Worst Case (5th %ile)", f"EUR {final_vals.quantile(0.05):,.0f}"),
    ])
    pdf.add_chart(viz.plot_monte_carlo(simulation_df, initial), h=85)

    # ── Section 6: Efficient Frontier (if available) ──────────────────────────────
    if frontier_df is not None:
        pdf.add_page()
        pdf.section_title("6. Efficient Frontier")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*GRAY)
        pdf.multi_cell(0, 5,
            "Each point represents a possible portfolio allocation. The red star marks the "
            "portfolio with the highest Sharpe Ratio (best risk-adjusted return).")
        pdf.ln(3)
        pdf.set_text_color(*BLACK)
        pdf.add_chart(viz.plot_efficient_frontier(frontier_df, tickers), h=90)

    # ── Section 7: Dividend Analysis ─────────────────────────────────────────────
    pdf.add_page()
    div_section = "7." if frontier_df is not None else "6."
    pdf.section_title(f"{div_section} Dividend Analysis")
    pdf.metric_boxes([
        ("Portfolio Yield", f"{portfolio_yield:.2%}"),
        ("Est. Annual Income", f"EUR {total_income:,.2f}"),
        ("Est. Monthly Income", f"EUR {total_income / 12:,.2f}"),
    ])
    if total_income > 0:
        pdf.add_chart(viz.plot_dividend_income(dividend_df), h=70)
    else:
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(*GRAY)
        pdf.cell(0, 8, "None of the selected stocks currently pay dividends.", align="C",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*BLACK)

    # ── Disclaimer ────────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.section_title("Disclaimer")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*GRAY)
    pdf.multi_cell(0, 5,
        "This report is generated by Portfolio Analyzer for informational and educational "
        "purposes only. It does not constitute financial advice, investment recommendations, "
        "or a solicitation to buy or sell any securities. Past performance is not indicative "
        "of future results. All investments involve risk, including the possible loss of "
        "principal. The projections and simulations presented (including Monte Carlo analysis) "
        "are based on historical data and statistical models, and do not guarantee future "
        "performance. Dividend income estimates are based on current yields and may change. "
        "Please consult a qualified financial advisor before making any investment decisions. "
        "Market data is sourced from Yahoo Finance via yfinance and may be subject to delays "
        "or inaccuracies.")

    return bytes(pdf.output())
