
import os
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Alpha Vantage API key is read from environment variable for safety
ALPHAVANTAGE_KEY = os.environ.get("ALPHAVANTAGE_KEY", "")


def fetch_alpha_vantage_data(ticker: str):
    """
    Fetch EPS and current price from Alpha Vantage.
    Uses:
      - OVERVIEW (for EPS)
      - GLOBAL_QUOTE (for current price)
    """
    if not ALPHAVANTAGE_KEY:
        raise RuntimeError("ALPHAVANTAGE_KEY environment variable is not set.")

    overview_url = (
        "https://www.alphavantage.co/query"
        f"?function=OVERVIEW&symbol={ticker}&apikey={ALPHAVANTAGE_KEY}"
    )
    quote_url = (
        "https://www.alphavantage.co/query"
        f"?function=GLOBAL_QUOTE&symbol={ticker}&apikey={ALPHAVANTAGE_KEY}"
    )

    overview_res = requests.get(overview_url, timeout=10)
    quote_res = requests.get(quote_url, timeout=10)

    overview = overview_res.json()
    quote = quote_res.json()

    if "EPS" not in overview or "Global Quote" not in quote:
        raise ValueError("Could not get EPS or quote for this ticker.")

    try:
        eps = float(overview.get("EPS", 0.0))
    except Exception:
        eps = 0.0

    price_str = quote["Global Quote"].get("05. price", "0")
    try:
        price = float(price_str)
    except Exception:
        price = 0.0

    if eps <= 0 or price <= 0:
        raise ValueError("Invalid EPS or price returned from API.")

    return eps, price


def rule1_valuations(eps: float, price: float):
    """
    Simplified Phil Town style valuations:
      - Sticker price
      - Margin of safety (50%)
      - 10-cap
      - 8-year payback price
    """
    growth = 0.10            # 10% assumed growth
    future_pe = growth * 200 # 2 x growth rate (e.g. 10% -> PE 20)
    discount = 0.15          # 15% required return
    years = 10

    future_eps = eps * (1 + growth) ** years
    future_value = future_eps * future_pe

    sticker = future_value / ((1 + discount) ** years)
    mos = sticker / 2.0

    ten_cap_value = eps / 0.10 if eps > 0 else 0.0

    payback_years = 8
    cumulative = 0.0
    for t in range(1, payback_years + 1):
        cumulative += eps * ((1 + growth) ** t)

    payback_price = cumulative

    return {
        "price": price,
        "eps": eps,
        "growth": growth,
        "future_pe": future_pe,
        "future_eps": future_eps,
        "future_value": future_value,
        "discount": discount,
        "sticker": sticker,
        "mos": mos,
        "ten_cap": ten_cap_value,
        "payback_price": payback_price,
        "payback_years": payback_years,
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/value", methods=["GET"])
def api_value():
    ticker = request.args.get("ticker", "").upper().strip()
    if not ticker:
        return jsonify({"error": "Missing ticker"}), 400

    try:
        eps, price = fetch_alpha_vantage_data(ticker)
        vals = rule1_valuations(eps, price)
        vals["ticker"] = ticker
        return jsonify(vals)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    # When running locally
    app.run(host="0.0.0.0", port=5000, debug=True)
