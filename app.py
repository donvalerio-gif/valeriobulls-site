from flask import Flask, render_template, request, jsonify
import requests
import os

app = Flask(__name__)

FMP_KEY = os.environ.get("FMP_KEY")

# ---------- Helper Functions ---------- #

def get_fmp_json(url):
    """Helper function to fetch JSON from FMP."""
    response = requests.get(url)
    if response.status_code != 200:
        return None
    try:
        return response.json()
    except:
        return None

def get_price(ticker):
    url = f"https://financialmodelingprep.com/api/v3/quote/{ticker}?apikey={FMP_KEY}"
    data = get_fmp_json(url)
    if not data or len(data) == 0:
        return None
    return data[0]["price"]

def get_eps(ticker):
    url = f"https://financialmodelingprep.com/api/v3/income-statement/{ticker}?limit=5&apikey={FMP_KEY}"
    data = get_fmp_json(url)
    if not data or len(data) == 0:
        return None
    
    # EPS diluted
    eps = data[0].get("epsdiluted")
    return eps

def get_growth_rate(ticker):
    url = f"https://financialmodelingprep.com/api/v3/income-statement/{ticker}?limit=5&apikey={FMP_KEY}"
    data = get_fmp_json(url)
    if not data or len(data) < 3:
        return None

    eps_list = [item.get("epsdiluted") for item in data if item.get("epsdiluted") is not None]

    if len(eps_list) < 3:
        return None

    # Use CAGR over last 3 years
    try:
        start = eps_list[-1]
        end = eps_list[0]
        years = 3
        cagr = ((end / start) ** (1 / years)) - 1
        return cagr
    except:
        return None

# --------------------------------------- #

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/value", methods=["POST"])
def value():
    ticker = request.json.get("ticker", "").upper()

    current_price = get_price(ticker)
    eps = get_eps(ticker)
    growth = get_growth_rate(ticker)

    if not current_price or not eps or not growth:
        return jsonify({"error": "Could not fetch enough data to calculate valuation."})

    # Phil Town Sticker Price formula:
    future_eps = eps * ((1 + growth) ** 10)
    future_price = future_eps * 15
    sticker_price = future_price / ((1 + 0.15) ** 10)
    mos_price = sticker_price / 2

    return jsonify({
        "ticker": ticker,
        "price": round(current_price, 2),
        "eps": round(eps, 2),
        "growth_rate": round(growth * 100, 2),
        "sticker_price": round(sticker_price, 2),
        "mos_price": round(mos_price, 2)
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
