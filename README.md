## 📌 Περιγραφή
Ο **Portfolio Analyzer** είναι μια web εφαρμογή σε Python που επιτρέπει στους χρήστες να αναλύουν, να οπτικοποιούν και να διαχειρίζονται επενδυτικά χαρτοφυλάκια μετοχών. Υπολογίζει metrics κινδύνου και απόδοσης, εκτελεί προχωρημένες χρηματοοικονομικές αναλύσεις και παρέχει θεμελιώδη ανάλυση εταιρειών.

## 🚀 Χαρακτηριστικά

### Portfolio Analysis
* **Σύγκριση με S&P 500** — Portfolio vs Benchmark γράφημα
* **Risk Metrics** — Sharpe Ratio, Max Drawdown, Volatility, Beta
* **Annual Returns** — Ετήσια απόδοση ανά χρόνο
* **Sector Allocation** — Κατανομή ανά κλάδο
* **Risk Warnings** — Αυτόματες ειδοποιήσεις βάσει metrics

### Advanced Finance
* **Monte Carlo Simulation** — 1000 σενάρια για το μελλοντικό portfolio
* **Efficient Frontier** — Βέλτιστη κατανομή risk/return
* **Markowitz Optimization** — Μαθηματική βελτιστοποίηση weights
* **Correlation Matrix** — Συσχέτιση μεταξύ μετοχών

### Stock Analysis
* **Fundamental Analysis** — Ανάλυση ισολογισμών εταιρείας
* **Asset Assessment** — Radar chart με score 0-10 ανά metric
* **Financial Checklist** — ✅/❌ έλεγχος 8 χρηματοοικονομικών δεικτών

### Άλλα
* **Αναζήτηση μετοχών** — Βάση δεδομένων 100 γνωστών μετοχών
* **Date Range Selector** — 1Y / 3Y / 5Y / 10Y / Custom
* **Export to CSV** — Εξαγωγή αποτελεσμάτων

## 🛠️ Τεχνολογίες
* **Python 3.x**
* **Pandas / NumPy** — Ανάλυση δεδομένων και returns
* **Plotly** — Interactive γραφήματα
* **Streamlit** — Web UI
* **yfinance** — Live τιμές και οικονομικά στοιχεία μετοχών
* **SciPy** — Portfolio optimization (SLSQP)
* **SQLite** — Βάση δεδομένων μετοχών

## 🚀 Εκκίνηση

```bash
pip install -r requirements.txt
python init_db.py
streamlit run app.py
```

## 🗂️ Δομή Project

```
PortfolioAnalyzer/
├── app.py              # Streamlit UI
├── main.py             # CLI entry point
├── init_db.py          # Αρχικοποίηση βάσης δεδομένων
├── requirements.txt
└── src/
    ├── stock.py         # Stock class
    ├── portfolio.py     # Portfolio class
    ├── metrics.py       # Metrics class
    ├── visualizer.py    # Visualizer class
    ├── fundamentals.py  # FundamentalAnalysis class
    └── database.py      # Database class
```

## 📊 UML Διάγραμμα

```mermaid
classDiagram
    direction TB

    class Stock {
        +String ticker
        +Series prices
        +Series returns
        +load_data(start, end)
        +calculate_returns()
        +get_latest_price()
    }

    class Portfolio {
        +List stocks
        +List weights
        +Series portfolio_returns
        +Metrics metrics
        +validate_weights()
        +load_all_data(start, end)
        +calculate_portfolio_returns()
        +calculate_volatility()
        +calculate_portfolio_value(initial)
        +load_benchmark(ticker, start, end)
        +calculate_sharpe_ratio()
        +calculate_max_drawdown(value)
        +calculate_beta(benchmark)
        +calculate_annual_returns()
        +calculate_correlation()
        +calculate_individual_values(initial)
        +simulate_monte_carlo(initial)
        +calculate_efficient_frontier()
        +optimize_portfolio()
        +export_to_csv(...)
    }

    class Metrics {
        +Float risk_free_rate
        +sharpe_ratio(returns)
        +max_drawdown(value)
    }

    class Visualizer {
        +plot_comparison(portfolio, benchmark)
        +plot_monte_carlo(simulation, initial)
        +plot_efficient_frontier(frontier, tickers)
        +plot_correlation(corr_matrix)
        +plot_individual_stocks(values)
        +plot_sector_allocation(weights)
        +plot_annual_returns(returns)
        +plot_asset_assessment(scores)
    }

    class Database {
        +String DB_PATH
        +insert_stock(ticker, name, sector)
        +get_all_stocks()
        +get_sectors(tickers)
        +search_stocks(query)
        +close()
    }

    class FundamentalAnalysis {
        +String ticker
        +current_ratio()
        +debt_to_equity()
        +profit_margin()
        +revenue_growth()
        +eps()
        +pe_ratio()
        +pb_ratio()
        +free_cash_flow()
    }

    Portfolio --> Stock : contains
    Portfolio --> Metrics : uses
```
