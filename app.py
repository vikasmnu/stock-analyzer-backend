from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)
CORS(app)

# Root check route
@app.route('/')
def home():
    return "✅ Stock Analyzer API is running!"

# Analyze a single stock
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

        # Entry & target calculation
        entry = round(price * 0.97, 2)
        target = round(price * 1.15, 2)

        suggestion = "Good Entry Opportunity" if pe < 25 and pb < 5 and dte < 1 and roe and roe > 0.15 else "Avoid or Wait"

        # 6-month price history
        hist_6mo = stock.history(period="6mo")
        chart_data_6mo = {
            "dates": hist_6mo.index.strftime('%Y-%m-%d').tolist(),
            "prices": hist_6mo["Close"].round(2).fillna(0).tolist()
        }

        # 1-day intraday chart (5-minute interval)
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

# Suggested stock list using Google Sheets
@app.route('/suggested-stocks', methods=['GET'])
def suggested_stocks():
    try:
        # Google Sheets setup
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            'stock-scanner-465109-32b379c1d519.json', scope)
        client = gspread.authorize(creds)

        # Open your Google Sheet and specific worksheet
        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1ghWvOiGGcFWRu1mEdNSjpk7r0CMOW_JFeJznWs0gFOw/edit")
        worksheet = sheet.worksheet("OLD")

        tickers = worksheet.col_values(1)  # assuming tickers are in column A
        good_entries = []

        for symbol in tickers:
            if not symbol.strip():
                continue
            symbol = symbol.strip().upper()
            if not symbol.endswith(".NS"):
                symbol += ".NS"

            try:
                stock = yf.Ticker(symbol)
                info = stock.info

                pe = info.get("trailingPE", 0)
                pb = info.get("priceToBook", 0)
                roe = info.get("returnOnEquity", 0)
                dte = info.get("debtToEquity", 0)

                if pe < 25 and pb < 5 and dte < 1 and roe and roe > 0.15:
                    good_entries.append({
                        "symbol": symbol,
                        "name": info.get("longName")
                    })

            except Exception as e:
                print(f"Error with {symbol}: {e}")

        return jsonify(good_entries)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# For Render deployment
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)