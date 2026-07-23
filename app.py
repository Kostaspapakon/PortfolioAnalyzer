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
from datetime import datetime as _dt


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


_BADGE_COLORS = ["#4F8EF7", "#FF9800", "#2ECC71", "#E74C3C", "#9B59B6", "#1ABC9C"]

_EARNINGS_MAJORS = (
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
    "JPM", "V", "MA", "UNH", "HD", "JNJ", "XOM", "BAC",
    "WMT", "AVGO", "LLY", "CVX", "COST", "MRK", "ABBV",
    "NFLX", "AMD", "ORCL", "CRM", "ADBE", "QCOM", "GS",
    "MS", "BA", "CAT", "GE", "IBM", "NOW", "INTU", "PG",
    "KO", "PEP", "NKE", "SBUX", "DIS", "PYPL", "INTC",
)


@st.cache_data(ttl=900)
def fetch_portfolio_news(tickers: tuple, n_per_ticker: int = 6) -> list:
    all_articles = []
    seen = set()

    for ticker in tickers:
        try:
            raw_news = yf.Ticker(ticker).news or []
            for item in raw_news[:n_per_ticker]:
                content = item.get("content", item)
                title = content.get("title") or item.get("title", "")
                if not title or title in seen:
                    continue
                seen.add(title)

                link = (
                    content.get("clickThroughUrl", {}).get("url")
                    or content.get("canonicalUrl", {}).get("url")
                    or item.get("link", "#")
                )
                publisher = (
                    content.get("provider", {}).get("displayName")
                    or item.get("publisher", "Unknown")
                )
                pub_date = content.get("pubDate")
                if not pub_date:
                    ts = item.get("providerPublishTime")
                    if ts:
                        pub_date = _dt.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")

                all_articles.append({
                    "ticker":    ticker,
                    "title":     title,
                    "link":      link,
                    "publisher": publisher,
                    "date":      pub_date or "",
                })
        except Exception:
            continue

    all_articles.sort(key=lambda x: x["date"], reverse=True)
    return all_articles


@st.cache_data(ttl=60)
def fetch_market_data() -> list:
    symbols = [
        ("S&P 500",   "^GSPC"),
        ("NASDAQ",    "^IXIC"),
        ("Dow Jones", "^DJI"),
        ("DAX",       "^GDAXI"),
        ("FTSE 100",  "^FTSE"),
        ("Apple",     "AAPL"),
        ("NVIDIA",    "NVDA"),
        ("Microsoft", "MSFT"),
        ("Amazon",    "AMZN"),
        ("Alphabet",  "GOOGL"),
        ("Tesla",     "TSLA"),
        ("Meta",      "META"),
        ("Gold",      "GC=F"),
        ("Oil (WTI)", "CL=F"),
        ("Bitcoin",   "BTC-USD"),
        ("EUR/USD",   "EURUSD=X"),
    ]
    items = []
    for name, symbol in symbols:
        try:
            fi = yf.Ticker(symbol).fast_info
            price = getattr(fi, "last_price", None)
            prev  = getattr(fi, "previous_close", None)
            if not price or not prev:
                continue
            chg = price - prev
            pct = chg / prev
            items.append({"name": name, "price": price, "chg": chg, "pct": pct})
        except Exception:
            continue
    return items


@st.cache_data(ttl=600)
def fetch_market_news() -> list:
    source_tickers = ("SPY", "QQQ", "AAPL", "MSFT", "NVDA", "TSLA", "META", "AMZN")
    all_articles = []
    seen: set = set()
    for ticker in source_tickers:
        try:
            raw = yf.Ticker(ticker).news or []
            for item in raw[:5]:
                content = item.get("content", item)
                title = content.get("title") or item.get("title", "")
                if not title or title in seen:
                    continue
                seen.add(title)
                link = (
                    content.get("clickThroughUrl", {}).get("url")
                    or content.get("canonicalUrl", {}).get("url")
                    or item.get("link", "#")
                )
                publisher = (
                    content.get("provider", {}).get("displayName")
                    or item.get("publisher", "Unknown")
                )
                pub_date = content.get("pubDate") or ""
                if not pub_date:
                    ts = item.get("providerPublishTime")
                    if ts:
                        pub_date = _dt.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")

                # Extract best-resolution thumbnail
                image_url = None
                thumb = content.get("thumbnail") or item.get("thumbnail") or {}
                if isinstance(thumb, dict):
                    resolutions = thumb.get("resolutions", [])
                    for res in sorted(resolutions, key=lambda r: r.get("width", 0)):
                        if res.get("width", 0) >= 200:
                            image_url = res.get("url")
                            break
                    if not image_url and resolutions:
                        image_url = resolutions[-1].get("url")
                    if not image_url:
                        image_url = thumb.get("originalUrl")

                all_articles.append({
                    "title":     title,
                    "link":      link,
                    "publisher": publisher,
                    "date":      pub_date,
                    "image":     image_url,
                })
        except Exception:
            continue
    all_articles.sort(key=lambda x: x["date"], reverse=True)
    return all_articles[:25]


@st.cache_data(ttl=300)
def fetch_watchlist_prices(tickers: tuple) -> dict:
    result = {}
    for ticker in tickers:
        try:
            fi = yf.Ticker(ticker).fast_info
            price = getattr(fi, "last_price", None)
            prev  = getattr(fi, "previous_close", None)
            result[ticker] = {
                "price":     price,
                "prev":      prev,
                "day_chg":   (price - prev) if (price and prev) else None,
                "day_chg_pct": ((price - prev) / prev) if (price and prev) else None,
                "year_high": getattr(fi, "year_high", None),
                "year_low":  getattr(fi, "year_low", None),
            }
        except Exception:
            result[ticker] = {}
    return result


@st.cache_data(ttl=3600)
def fetch_earnings_calendar(tickers: tuple) -> list:
    today_d = date.today()
    cutoff  = today_d + timedelta(days=90)
    results = []
    for ticker in tickers:
        try:
            cal = yf.Ticker(ticker).calendar
            if not cal:
                continue
            if hasattr(cal, "to_dict"):
                cal = {k: (list(v.values())[0] if hasattr(v, "values") else v)
                       for k, v in cal.to_dict().items()}
            raw = cal.get("Earnings Date", [])
            if not raw:
                continue
            earn_date = raw[0] if isinstance(raw, (list, tuple)) else raw
            if hasattr(earn_date, "date"):
                earn_date = earn_date.date()
            if not isinstance(earn_date, type(today_d)):
                continue
            if earn_date < today_d or earn_date > cutoff:
                continue
            results.append({
                "ticker":   ticker,
                "date":     earn_date,
                "eps_est":  cal.get("Earnings Average"),
                "rev_est":  cal.get("Revenue Average"),
            })
        except Exception:
            continue
    results.sort(key=lambda x: x["date"])
    return results


def _render_earnings(earnings: list, name_map: dict):
    if not earnings:
        st.info("No upcoming earnings found in the next 90 days.")
        return

    today_d          = date.today()
    this_week_start  = today_d - timedelta(days=today_d.weekday())
    next_week_start  = this_week_start + timedelta(weeks=1)

    from collections import defaultdict
    weeks: dict = defaultdict(list)
    for ev in earnings:
        wk = ev["date"] - timedelta(days=ev["date"].weekday())
        weeks[wk].append(ev)

    for week_start in sorted(weeks.keys()):
        week_end = week_start + timedelta(days=4)
        if week_start == this_week_start:
            label = f"This Week · {week_start.strftime('%b %d')} – {week_end.strftime('%b %d')}"
            label_color = "#4F8EF7"
        elif week_start == next_week_start:
            label = f"Next Week · {week_start.strftime('%b %d')} – {week_end.strftime('%b %d')}"
            label_color = "#2ECC71"
        else:
            label = f"{week_start.strftime('%b %d')} – {week_end.strftime('%b %d, %Y')}"
            label_color = "#8b949e"

        st.markdown(
            f"<div style='font-size:12px;font-weight:700;color:{label_color};"
            f"text-transform:uppercase;letter-spacing:.6px;margin:22px 0 8px;'>"
            f"{label}</div>",
            unsafe_allow_html=True,
        )

        rows_html = ""
        for j, ev in enumerate(weeks[week_start]):
            badge_color = _BADGE_COLORS[j % len(_BADGE_COLORS)]
            is_today    = ev["date"] == today_d
            bg          = "rgba(255,152,0,.09)" if is_today else "rgba(255,255,255,.025)"
            border      = "#FF9800"             if is_today else "rgba(255,255,255,.07)"
            today_tag   = (
                ' <span style="font-size:10px;background:#FF9800;color:#fff;'
                'padding:1px 6px;border-radius:4px;font-weight:700;margin-left:6px;">TODAY</span>'
                if is_today else ""
            )
            name = name_map.get(ev["ticker"], ev["ticker"])

            eps_str = f'${ev["eps_est"]:.2f}' if ev.get("eps_est") is not None else "—"
            rev = ev.get("rev_est")
            if rev:
                if rev >= 1e12:   rev_str = f"${rev/1e12:.1f}T"
                elif rev >= 1e9:  rev_str = f"${rev/1e9:.1f}B"
                elif rev >= 1e6:  rev_str = f"${rev/1e6:.1f}M"
                else:              rev_str = f"${rev:.0f}"
            else:
                rev_str = "—"

            rows_html += f"""
<div style="display:flex;align-items:center;gap:14px;padding:11px 16px;
            margin-bottom:6px;border-radius:9px;background:{bg};
            border:1px solid {border};">
  <span style="color:#8b949e;font-size:12px;min-width:90px;flex-shrink:0;">
    {ev["date"].strftime("%a, %b %d")}{today_tag}
  </span>
  <span style="background:{badge_color};color:#fff;padding:3px 10px;border-radius:6px;
               font-weight:700;font-size:12px;min-width:62px;text-align:center;
               flex-shrink:0;">{ev["ticker"]}</span>
  <span style="flex:1;font-weight:600;color:#f0f6fc;font-size:13px;">{name}</span>
  <span style="font-size:12px;color:#8b949e;min-width:110px;text-align:right;flex-shrink:0;">
    EPS est &nbsp;<strong style="color:#3fb950;">{eps_str}</strong>
  </span>
  <span style="font-size:12px;color:#8b949e;min-width:120px;text-align:right;flex-shrink:0;">
    Rev est &nbsp;<strong style="color:#4F8EF7;">{rev_str}</strong>
  </span>
</div>"""

        st.markdown(rows_html, unsafe_allow_html=True)
    st.caption(f"{len(earnings)} upcoming earnings event(s) · next 90 days")


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

# ── Shared stock list ──────────────────────────────────────────────────────────
db = Database()
all_stocks = db.get_all_stocks()
db.close()
stock_display = sorted([f"{n} ({t})" for t, n, _ in all_stocks])

# ── Sidebar navigation ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Portfolio Analyzer")
    st.divider()
    nav = st.radio("nav", ["Home", "My Portfolio", "Watchlist", "Earnings", "Stock Analysis"], label_visibility="collapsed")
    if nav == "My Portfolio" and "res" in st.session_state:
        st.divider()
        if st.button("← Edit Portfolio", use_container_width=True):
            st.session_state["page"] = "setup"
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# HOME
# ══════════════════════════════════════════════════════════════════════════════
if nav == "Home":
    # ── Live scrolling ticker ───────────────────────────────────────────────────
    with st.spinner("Loading market data..."):
        market_data = fetch_market_data()

    if market_data:
        def _ticker_item(d):
            sign = "+" if d["chg"] >= 0 else ""
            cls  = "t-up" if d["chg"] >= 0 else "t-down"
            arrow = "▲" if d["chg"] >= 0 else "▼"
            price_str = f"{d['price']:,.2f}"
            chg_str   = f"{sign}{d['chg']:,.2f} ({sign}{d['pct']:.2%})"
            return (
                f'<span class="t-item">'
                f'<span class="t-name">{d["name"]}</span>'
                f'<span class="t-price">{price_str}</span>'
                f'<span class="{cls}">{arrow} {chg_str}</span>'
                f'</span>'
                f'<span class="t-sep">|</span>'
            )

        items_html = "".join(_ticker_item(d) for d in market_data)
        duration = max(30, len(market_data) * 4)

        st.markdown(f"""
<style>
.ticker-wrapper {{
    width:100%; overflow:hidden;
    background:linear-gradient(90deg,#0d1117,#161b22,#0d1117);
    padding:13px 0; border-radius:10px;
    border:1px solid rgba(255,255,255,0.07);
    margin-bottom:28px;
}}
.ticker-track {{
    display:inline-flex; width:max-content;
    animation:ticker-move {duration}s linear infinite;
}}
.ticker-track:hover {{ animation-play-state:paused; cursor:default; }}
@keyframes ticker-move {{
    0%   {{ transform:translateX(0); }}
    100% {{ transform:translateX(-50%); }}
}}
.t-item {{
    display:inline-flex; align-items:center;
    padding:0 22px; white-space:nowrap;
    font-family:'Inter',system-ui,sans-serif; font-size:13px;
}}
.t-name  {{ color:#8b949e; font-weight:500; margin-right:8px; }}
.t-price {{ color:#e6edf3; font-weight:700; margin-right:7px; font-variant-numeric:tabular-nums; }}
.t-up    {{ color:#3fb950; font-weight:600; }}
.t-down  {{ color:#f85149; font-weight:600; }}
.t-sep   {{ color:#30363d; padding:0 2px; }}
</style>
<div class="ticker-wrapper">
  <div class="ticker-track">
    {items_html}{items_html}
  </div>
</div>
""", unsafe_allow_html=True)
    else:
        st.info("Could not load market data. Check your connection.")

    # ── Market news ─────────────────────────────────────────────────────────────
    st.subheader("Market News")
    st.caption("Latest financial headlines · refreshed every 10 minutes")

    with st.spinner("Loading news..."):
        market_news = fetch_market_news()

    if market_news:
        hero = market_news[0]
        rest = market_news[1:22]

        def _esc(s):
            return (s or "").replace("&", "&amp;").replace('"', "&quot;")     \
                            .replace("'", "&#39;").replace("<", "&lt;")        \
                            .replace(">", "&gt;")

        def _img_tag(url, h):
            ph = f'<div style="height:{h}px;display:flex;align-items:center;justify-content:center;font-size:36px;background:linear-gradient(135deg,#161b22,#0d1117);color:#30363d;">📰</div>'
            if url:
                return (
                    f'<img src="{url}" alt="" loading="lazy"'
                    f' style="width:100%;height:{h}px;object-fit:cover;display:block;"'
                    f' onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\'">'
                    + ph.replace("display:flex", "display:none")
                )
            return ph

        # ── hero card ──────────────────────────────────────────────────────────
        hero_html = f"""
<div style="display:grid;grid-template-columns:1fr 1fr;border-radius:14px;
            overflow:hidden;border:1px solid rgba(255,255,255,.09);
            margin-bottom:28px;position:relative;">
  <a href="{hero['link']}" target="_blank" rel="noopener noreferrer"
     style="position:absolute;inset:0;z-index:1;"></a>
  <div style="overflow:hidden;min-height:260px;">
    {_img_tag(hero["image"], 260)}
  </div>
  <div style="display:flex;flex-direction:column;gap:14px;padding:28px;
              background:rgba(255,255,255,.025);">
    <span style="display:inline-block;font-size:10px;font-weight:700;
                 text-transform:uppercase;letter-spacing:.7px;
                 background:rgba(79,142,247,.18);color:#4F8EF7;
                 border-radius:4px;padding:2px 8px;width:fit-content;">
      {_esc(hero["publisher"])}
    </span>
    <span style="font-size:19px;font-weight:700;color:#f0f6fc;line-height:1.4;">
      {_esc(hero["title"])}
    </span>
    <span style="font-size:11px;color:#8b949e;margin-top:auto;">
      {_esc(hero["date"])}
    </span>
  </div>
</div>"""

        # ── grid cards ────────────────────────────────────────────────────────
        cards_html = ""
        for a in rest:
            cards_html += f"""
<div style="display:flex;flex-direction:column;border-radius:12px;
            overflow:hidden;border:1px solid rgba(255,255,255,.07);
            background:#0d1117;position:relative;
            transition:transform .2s,border-color .2s,box-shadow .2s;">
  <a href="{a['link']}" target="_blank" rel="noopener noreferrer"
     style="position:absolute;inset:0;z-index:1;"></a>
  <div style="overflow:hidden;height:160px;flex-shrink:0;">
    {_img_tag(a["image"], 160)}
  </div>
  <div style="display:flex;flex-direction:column;gap:8px;
              padding:14px 16px 16px;flex:1;">
    <span style="display:inline-block;font-size:10px;font-weight:700;
                 text-transform:uppercase;letter-spacing:.7px;
                 background:rgba(79,142,247,.18);color:#4F8EF7;
                 border-radius:4px;padding:2px 7px;width:fit-content;">
      {_esc(a["publisher"])}
    </span>
    <span style="font-size:13px;font-weight:600;color:#f0f6fc;
                 line-height:1.45;overflow:hidden;
                 display:-webkit-box;-webkit-line-clamp:3;
                 -webkit-box-orient:vertical;">
      {_esc(a["title"])}
    </span>
    <span style="font-size:11px;color:#8b949e;margin-top:auto;">
      {_esc(a["date"])}
    </span>
  </div>
</div>"""

        st.markdown(f"""
<style>
</style>
{hero_html}
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:18px;">
  {cards_html}
</div>
""", unsafe_allow_html=True)
    else:
        st.info("No news available at this time.")

# ══════════════════════════════════════════════════════════════════════════════
# MY PORTFOLIO
# ══════════════════════════════════════════════════════════════════════════════
elif nav == "My Portfolio":
    page = st.session_state.get("page", "setup")

    # ── Setup / Input Screen ────────────────────────────────────────────────────
    if page == "setup":
        st.title("My Portfolio")
        st.markdown(
            "Add each stock or ETF purchase below. You can enter multiple transactions, "
            "including the same asset bought at different dates."
        )
        st.divider()

        default_tx = st.session_state.get(
            "input_transactions",
            pd.DataFrame({
                "Stock": ["Apple (AAPL)", "NVIDIA (NVDA)"],
                "Purchase Date": [
                    date.today() - timedelta(days=365),
                    date.today() - timedelta(days=730),
                ],
                "Amount (EUR)": [1000.0, 500.0],
            }),
        )

        transactions = st.data_editor(
            default_tx,
            num_rows="dynamic",
            column_config={
                "Stock": st.column_config.SelectboxColumn(
                    "Stock / ETF", options=stock_display, required=True,
                ),
                "Purchase Date": st.column_config.DateColumn(
                    "Purchase Date", required=True,
                ),
                "Amount (EUR)": st.column_config.NumberColumn(
                    "Amount (EUR)", min_value=1.0, step=100.0, format="€%.2f",
                ),
            },
            use_container_width=True,
            height=min(450, max(200, 55 + 35 * (len(default_tx) + 2))),
        )

        st.divider()
        _, cta_col, _ = st.columns([1, 2, 1])
        analyze = cta_col.button(
            "Analyze Portfolio →", use_container_width=True, type="primary"
        )

        if analyze:
            st.session_state["input_transactions"] = transactions
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

                ticker_amounts = results_df.groupby("Ticker")["Invested (EUR)"].sum()
                tickers = list(ticker_amounts.index)
                weights = [float(ticker_amounts[t] / ticker_amounts.sum()) for t in tickers]
                min_date = str(pd.to_datetime(valid_tx["Purchase Date"]).min().date())

                stocks = [Stock(t) for t in tickers]
                portfolio = Portfolio(stocks=stocks, weights=weights)
                portfolio.load_all_data(start=min_date, end=date.today().strftime("%Y-%m-%d"))
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
            st.session_state["page"] = "analysis"
            st.session_state.pop("dca_res", None)
            st.session_state.pop("markowitz_res", None)
            st.session_state.pop("pdf_bytes", None)
            st.session_state.pop("portfolio_news", None)
            st.rerun()

    # ── Analysis Screen ─────────────────────────────────────────────────────────
    else:
        tab_portfolio, tab_markowitz = st.tabs(["Portfolio Analysis", "Markowitz Optimization"])

        # ── Portfolio Analysis Tab ──────────────────────────────────────────────
        with tab_portfolio:
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

            # ── Holdings Breakdown ──────────────────────────────────────────────
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

            # ── Portfolio Score ─────────────────────────────────────────────────
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

            # ── Chart ───────────────────────────────────────────────────────────
            fig = visualizer.plot_comparison(portfolio_value, benchmark_value)
            st.plotly_chart(fig, use_container_width=True)

            # ── Metrics ─────────────────────────────────────────────────────────
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

            # ── Sector Allocation ────────────────────────────────────────────────
            st.subheader("Sector Allocation")
            sector_fig = visualizer.plot_sector_allocation(sector_weights)
            st.plotly_chart(sector_fig, use_container_width=True)

            # ── Dividend Analysis ────────────────────────────────────────────────
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

            # ── Diversification Analysis ─────────────────────────────────────────
            st.subheader("Diversification Analysis")
            show_diversification_warnings(sector_weights, corr_matrix, tickers, weights)

            # ── Individual Stock Performance ─────────────────────────────────────
            if individual_values is not None:
                st.subheader("Individual Stock Performance")
                individual_fig = visualizer.plot_individual_stocks(individual_values)
                st.plotly_chart(individual_fig, use_container_width=True)

            # ── Annual Returns ───────────────────────────────────────────────────
            st.subheader("Annual Returns")
            annual_fig = visualizer.plot_annual_returns(annual_returns)
            st.plotly_chart(annual_fig, use_container_width=True)

            # ── Risk Warnings ────────────────────────────────────────────────────
            show_risk_warnings(max_drawdown, sharpe, outperformance, beta)

            # ── Monte Carlo Simulation ───────────────────────────────────────────
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

            # ── Efficient Frontier ───────────────────────────────────────────────
            if frontier_df is not None:
                st.subheader("Efficient Frontier")
                frontier_fig = visualizer.plot_efficient_frontier(frontier_df, tickers)
                st.plotly_chart(frontier_fig, use_container_width=True)

            # ── Correlation Matrix ───────────────────────────────────────────────
            if corr_matrix is not None:
                st.subheader("Correlation Matrix")
                corr_fig = visualizer.plot_correlation(corr_matrix)
                st.plotly_chart(corr_fig, use_container_width=True)

            # ── DCA Simulator ────────────────────────────────────────────────────
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

            # ── Portfolio News Feed ──────────────────────────────────────────────
            st.subheader("Portfolio News")

            if st.button("Load Latest News", use_container_width=True):
                with st.spinner("Fetching news for all holdings..."):
                    st.session_state["portfolio_news"] = fetch_portfolio_news(tuple(tickers))

            if "portfolio_news" in st.session_state:
                articles = st.session_state["portfolio_news"]
                if articles:
                    ticker_color = {
                        t: _BADGE_COLORS[i % len(_BADGE_COLORS)]
                        for i, t in enumerate(tickers)
                    }
                    for article in articles:
                        color = ticker_color.get(article["ticker"], _BADGE_COLORS[0])
                        badge = (
                            f"<span style='background:{color};color:white;"
                            f"padding:2px 10px;border-radius:12px;"
                            f"font-size:11px;font-weight:700;letter-spacing:0.5px'>"
                            f"{article['ticker']}</span>"
                        )
                        st.markdown(
                            f"{badge}&nbsp;&nbsp;**[{article['title']}]({article['link']})**",
                            unsafe_allow_html=True,
                        )
                        st.caption(f"{article['publisher']} · {article['date']}")
                        st.divider()
                else:
                    st.info("No news found for the current holdings.")

            # ── Export ───────────────────────────────────────────────────────────
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

        # ── Markowitz Optimization Tab ──────────────────────────────────────────
        with tab_markowitz:
            st.subheader("Markowitz Portfolio Optimization")

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

# ══════════════════════════════════════════════════════════════════════════════
# WATCHLIST
# ══════════════════════════════════════════════════════════════════════════════
elif nav == "Watchlist":
    st.title("Watchlist")
    st.markdown("Track stocks and ETFs you're considering buying.")
    st.divider()

    db_wl = Database()
    watchlist_items = db_wl.get_watchlist()

    # ── Add to watchlist ────────────────────────────────────────────────────────
    with st.expander("+ Add to Watchlist", expanded=len(watchlist_items) == 0):
        wl_col1, wl_col2, wl_col3 = st.columns([3, 1, 1])
        wl_stock = wl_col1.selectbox(
            "Stock / ETF", options=stock_display, key="wl_select"
        )
        wl_target = wl_col2.number_input(
            "Target Price ($)", min_value=0.0, value=0.0, step=1.0, key="wl_target"
        )
        wl_notes = wl_col3.text_input("Notes (optional)", key="wl_notes")

        if st.button("Add to Watchlist", use_container_width=True, type="primary"):
            wl_ticker = wl_stock.split("(")[-1].rstrip(")").strip().upper()
            wl_name   = wl_stock.split(" (")[0].strip()
            existing  = [row[0] for row in watchlist_items]
            if wl_ticker in existing:
                st.warning(f"**{wl_ticker}** is already in your watchlist.")
            else:
                target = wl_target if wl_target > 0 else None
                db_wl.add_to_watchlist(wl_ticker, wl_name, target, wl_notes or None)
                db_wl.close()
                st.rerun()

    db_wl.close()

    # ── Watchlist table ─────────────────────────────────────────────────────────
    db_wl2 = Database()
    watchlist_items = db_wl2.get_watchlist()
    db_wl2.close()

    if not watchlist_items:
        st.info("Your watchlist is empty. Add stocks or ETFs above to start tracking them.")
    else:
        tickers_wl = tuple(row[0] for row in watchlist_items)
        with st.spinner("Fetching live prices..."):
            prices_wl = fetch_watchlist_prices(tickers_wl)

        rows_wl = []
        for ticker, name, target_price, notes, added_date in watchlist_items:
            p = prices_wl.get(ticker, {})
            price     = p.get("price")
            day_chg   = p.get("day_chg")
            day_pct   = p.get("day_chg_pct")
            yr_high   = p.get("year_high")
            yr_low    = p.get("year_low")
            to_target = ((target_price - price) / price) if (target_price and price) else None
            rows_wl.append({
                "Ticker":       ticker,
                "Company":      name,
                "Price ($)":    price,
                "Day ($)":      day_chg,
                "Day (%)":      day_pct,
                "52W Low":      yr_low,
                "52W High":     yr_high,
                "Target ($)":   target_price,
                "To Target":    to_target,
                "Added":        added_date,
                "Notes":        notes or "",
            })

        wl_df = pd.DataFrame(rows_wl)

        def _fmt(v, fmt):
            return fmt.format(v) if v is not None else "—"

        styled_wl = (
            wl_df.style
            .format({
                "Price ($)":  lambda v: _fmt(v, "${:.2f}"),
                "Day ($)":    lambda v: (f"+${v:.2f}" if v >= 0 else f"-${abs(v):.2f}") if v is not None else "—",
                "Day (%)":    lambda v: _fmt(v, "{:+.2%}"),
                "52W Low":    lambda v: _fmt(v, "${:.2f}"),
                "52W High":   lambda v: _fmt(v, "${:.2f}"),
                "Target ($)": lambda v: _fmt(v, "${:.2f}"),
                "To Target":  lambda v: _fmt(v, "{:+.2%}"),
            })
            .map(
                lambda v: "color: #2ECC71; font-weight: 600" if isinstance(v, float) and v > 0
                          else ("color: #E74C3C; font-weight: 600" if isinstance(v, float) and v < 0 else ""),
                subset=["Day ($)", "Day (%)", "To Target"],
            )
        )
        st.dataframe(styled_wl, use_container_width=True, hide_index=True)

        st.caption(f"Prices cached for 5 minutes · {len(watchlist_items)} item(s) tracked")

        # ── Remove ──────────────────────────────────────────────────────────────
        st.divider()
        rm_col1, rm_col2 = st.columns([3, 1])
        remove_choice = rm_col1.selectbox(
            "Remove from watchlist",
            options=[f"{row[1]} ({row[0]})" for row in watchlist_items],
            label_visibility="collapsed",
        )
        if rm_col2.button("Remove", use_container_width=True):
            rm_ticker = remove_choice.split("(")[-1].rstrip(")").strip()
            db_rm = Database()
            db_rm.remove_from_watchlist(rm_ticker)
            db_rm.close()
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# EARNINGS CALENDAR
# ══════════════════════════════════════════════════════════════════════════════
elif nav == "Earnings":
    st.title("Earnings Calendar")
    st.caption("Upcoming earnings reports for the next 90 days · dates from Yahoo Finance")
    st.divider()

    db_earn = Database()
    name_map = {t: n for t, n, _ in db_earn.get_all_stocks()}
    db_earn.close()

    tab_port, tab_market = st.tabs(["My Portfolio Holdings", "Major Companies"])

    with tab_port:
        if "res" not in st.session_state:
            st.info(
                "Analyze your portfolio first in **My Portfolio** to see upcoming "
                "earnings for your holdings."
            )
        else:
            port_tickers = tuple(st.session_state["res"]["tickers"])
            st.caption(f"Tracking {len(port_tickers)} holding(s): {', '.join(port_tickers)}")

            if st.button("Refresh", key="refresh_port_earn"):
                st.cache_data.clear()

            with st.spinner("Fetching earnings dates for your holdings..."):
                port_earnings = fetch_earnings_calendar(port_tickers)

            _render_earnings(port_earnings, name_map)

    with tab_market:
        st.caption(f"Tracking {len(_EARNINGS_MAJORS)} major companies")

        if st.button("Refresh", key="refresh_market_earn"):
            st.cache_data.clear()

        with st.spinner(f"Fetching earnings for {len(_EARNINGS_MAJORS)} companies — this may take a moment..."):
            market_earnings = fetch_earnings_calendar(_EARNINGS_MAJORS)

        _render_earnings(market_earnings, name_map)

# ══════════════════════════════════════════════════════════════════════════════
# STOCK ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
else:
    st.title("Stock Analysis")

    db_sa = Database()
    all_stocks_sa = db_sa.get_all_stocks()
    db_sa.close()

    stock_options_sa = [f"{name} ({ticker})" for ticker, name, _ in all_stocks_sa]
    selected_stock = st.selectbox("Select a Stock or ETF", options=stock_options_sa)
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
        prices       = sr["prices"]
        tech_signals = sr["tech_signals"]
        sma50        = sr["sma50"]
        sma200       = sr["sma200"]
        bb_upper     = sr["bb_upper"]
        bb_lower     = sr["bb_lower"]
        rsi_series   = sr["rsi_series"]

        visualizer_sa = Visualizer()

        # ── ETF Analysis ────────────────────────────────────────────────────────
        if sr["is_etf"]:
            etf = sr["etf"]
            st.subheader(etf.fund_name())
            st.caption(f"{etf.fund_family()}  ·  {etf.category()}  ·  {sr['sector']}")

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

            ytd = etf.ytd_return()
            ret3 = etf.three_year_return()
            ret5 = etf.five_year_return()

            p1, p2, p3 = st.columns(3)
            p1.metric("YTD Return",    f"{ytd:.2%}"  if ytd  else "N/A")
            p2.metric("3Y Avg Return", f"{ret3:.2%}" if ret3 else "N/A")
            p3.metric("5Y Avg Return", f"{ret5:.2%}" if ret5 else "N/A")

            returns_chart = {"YTD": ytd, "3Y Avg": ret3, "5Y Avg": ret5}
            if any(v is not None for v in returns_chart.values()):
                etf_ret_fig = visualizer_sa.plot_etf_returns(returns_chart)
                st.plotly_chart(etf_ret_fig, use_container_width=True)

            st.divider()

            hi = etf.fifty_two_week_high()
            lo = etf.fifty_two_week_low()
            nav_price = etf.nav()
            r1, r2, r3 = st.columns(3)
            r1.metric("NAV / Price",  f"${nav_price:.2f}" if nav_price else "N/A")
            r2.metric("52-Week High", f"${hi:.2f}" if hi else "N/A")
            r3.metric("52-Week Low",  f"${lo:.2f}" if lo else "N/A")

            st.divider()

            desc = etf.description()
            if desc and desc != "No description available.":
                with st.expander("Fund Description"):
                    st.write(desc)

            st.subheader("Dividend History")
            dividends = etf.dividend_history()
            if not dividends.empty:
                div_hist_fig = visualizer_sa.plot_dividend_history(dividends)
                st.plotly_chart(div_hist_fig, use_container_width=True)
            else:
                st.info("This ETF does not pay dividends.")

        # ── Stock Fundamental Analysis ───────────────────────────────────────────
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
                dh_col1.metric("Dividend Yield",       f"{div_yield:.2%}" if div_yield else "N/A")
                dh_col2.metric("Annual Dividend Rate",  f"${div_rate:.2f}" if div_rate else "N/A")
                dh_col3.metric("Payout Ratio",          f"{payout:.2%}" if payout else "N/A")
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

        # ── Technical Analysis (stocks and ETFs) ────────────────────────────────
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
