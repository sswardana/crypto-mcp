from flask import Flask, jsonify
import requests

app = Flask(__name__)

@app.route("/")
def home():
    return "crypto mcp is running"

@app.route("/price/<symbol>")
def price(symbol):
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol.upper()}USDT"
    
    data = requests.get(url).json()

    return jsonify({
        "symbol": data.get("symbol"),
        "price": data.get("lastPrice"),
        "change_24h": data.get("priceChangePercent"),
        "volume": data.get("volume")
    })

@app.route("/ssw")
def ssw():
    coins = ["BTC", "ETH", "SOL", "DEXE"]

    result = []

    for coin in coins:
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={coin}USDT"
        data = requests.get(url).json()

        result.append({
            "symbol": coin,
            "price": data.get("lastPrice"),
            "change_24h": data.get("priceChangePercent"),
            "volume": data.get("volume")
        })

    return jsonify({
        "status": "SSW active",
        "data": result
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
