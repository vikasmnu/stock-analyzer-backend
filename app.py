from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
import os

app = Flask(__name__)
CORS(app)

# Root route to confirm server is running
@app.route('/')
def home():
    return "✅ Stock Analyzer API is running!"

# Stock analysis route
@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    symbol = data.get('symbol')

    if not symbol:
        return jsonify({'error': 'Symbol not provided'}), 400

    try:
        stock = yf.Ticker(symbol)
        info = stock.info

        # Extract fundamentals
        price = info.get("currentPrice", 0)
        pe = info.get("trailingPE", 0)
        pb = info.get("priceToBook", 0)
        roe = info.get("returnOnEquity", 0)
        dte = info.get("debtToEquity", 0)

        # Entry & Target logic
        entry = round(price * 0.97, 2)
        target = round(price * 1.15, 2)
        suggestion = "Good Entry Opportunity" if pe < 25 and pb < 5 and dte < 1 and roe and roe > 0.15 else "Avoid or Wait"

        # 6-month price history
        hist_6mo = stock.history(period="6mo")
        chart_data_6mo = {
            "dates": hist_6mo.index.strftime('%Y-%m-%d').tolist(),
            "prices": hist_6mo["Close"].round(2).fillna(0).tolist()
        }

        # 1-day intraday chart (5-minute)
        hist_daily = stock.history(period="1d", interval="5m")
        chart_data_daily = {
            "timestamps": hist_daily.index.strftime('%H:%M').tolist(),
            "prices": hist_daily["Close"].round(2).fillna(0).tolist(),
            "volume": hist_daily["Volume"].fillna(0).astype(int).tolist()
        }

        return jsonify({
            "name": info.get("longName"),
            "sector": info.get("sector"),
            "price": price,
            "pe": pe,
            "pb": pb,
            "roe": roe,
            "debtToEquity": dte,
            "entry": entry,
            "target": target,
            "suggestion": suggestion,
            "chart_6mo": chart_data_6mo,
            "chart_daily": chart_data_daily
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Dynamic port binding for Render
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)