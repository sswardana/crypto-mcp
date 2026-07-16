from flask import Flask, jsonify
import requests

app = Flask(__name__)

BINANCE = "https://api.binance.com"


@app.route("/")
def home():
    return "crypto mcp is running"


# Ambil top 50 pair USDT berdasarkan volume
@app.route("/ssw15m")
def ssw15m():

    ticker = requests.get(
        f"{BINANCE}/api/v3/ticker/24hr"
    ).json()

    usdt_pairs = [
        x for x in ticker
        if x["symbol"].endswith("USDT")
        and not any(c in x["symbol"] for c in ["UP","DOWN","BULL","BEAR"])
    ]

    top50 = sorted(
        usdt_pairs,
        key=lambda x: float(x["quoteVolume"]),
        reverse=True
    )[:50]


    result = []

    for coin in top50:

        symbol = coin["symbol"]

        candles = requests.get(
            f"{BINANCE}/api/v3/klines",
            params={
                "symbol": symbol,
                "interval": "15m",
                "limit": 50
            }
        ).json()


        if isinstance(candles, list):

            last = candles[-1]

            price_change = (
                (float(last[4])-float(last[1]))
                / float(last[1])
            ) * 100


            result.append({
                "symbol": symbol,
                "price": last[4],
                "change_15m": round(price_change,2),
                "volume": last[5],
                "volume24h": coin["quoteVolume"]
            })


    return jsonify({
        "scanner": "SSW Scalping",
        "timeframe": "15m",
        "coins_scanned": len(result),
        "data": result
    })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8080
    )
