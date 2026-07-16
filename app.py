from flask import Flask, jsonify
import requests

app = Flask(__name__)

BINANCE = "https://api.binance.com"

BLOCKLIST = [
    "USDC", "FDUSD", "BUSD",
    "TUSD", "USDP", "USD1",
    "XAUT", "PAXG"
]


def get_json(url, params=None):
    try:
        r = requests.get(
            url,
            params=params,
            timeout=5
        )
        return r.json()
    except:
        return None


def calculate_ema(data, period):
    if len(data) < period:
        return 0

    multiplier = 2 / (period + 1)
    ema_value = sum(data[:period]) / period

    for price in data[period:]:
        ema_value = (
            price - ema_value
        ) * multiplier + ema_value

    return ema_value


def calculate_rsi(prices, period=14):

    if len(prices) <= period:
        return 50

    gains = []
    losses = []

    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]

        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss

    return round(
        100 - (100/(1+rs)),
        2
    )


@app.route("/")
def home():
    return "crypto mcp is running"


@app.route("/ssw15m")
def ssw15m():

    ticker = get_json(
        f"{BINANCE}/api/v3/ticker/24hr"
    )

    if not ticker:
        return jsonify({
            "error":"Binance unavailable"
        })


    coins = []

    for x in ticker:

        symbol = x["symbol"]

        if not symbol.endswith("USDT"):
            continue

        if any(
            block in symbol
            for block in BLOCKLIST
        ):
            continue

        coins.append(x)


    top10 = sorted(
        coins,
        key=lambda x: float(x["quoteVolume"]),
        reverse=True
    )[:10]


    results = []


    for coin in top10:

        symbol = coin["symbol"]


        candles = get_json(
            f"{BINANCE}/api/v3/klines",
            {
                "symbol":symbol,
                "interval":"15m",
                "limit":50
            }
        )


        if not candles:
            continue


        closes = [
            float(c[4])
            for c in candles
        ]


        volumes = [
            float(c[5])
            for c in candles
        ]


        rsi = calculate_rsi(
            closes
        )

        ema9 = calculate_ema(
            closes,
            9
        )

        ema21 = calculate_ema(
            closes,
            21
        )


        avg_volume = (
            sum(volumes[-20:])
            /
            20
        )

        volume_ratio = round(
            volumes[-1]/avg_volume,
            2
        )


        score = 0
        reason = []


        if ema9 > ema21:
            score += 30
            reason.append(
                "EMA bullish"
            )


        if 50 < rsi < 70:
            score += 20
            reason.append(
                "RSI momentum"
            )


        if volume_ratio > 1.5:
            score += 30
            reason.append(
                "Volume spike"
            )


        if closes[-1] > closes[-2]:
            score += 20
            reason.append(
                "Price naik"
            )


        signal = "NEUTRAL"

        if score >= 70:
            signal = "BULLISH"

        elif score <=30:
            signal = "BEARISH"


        results.append({

            "symbol":symbol,
            "price":closes[-1],
            "score":score,
            "signal":signal,
            "rsi":rsi,
            "volume_ratio":volume_ratio,
            "reason":reason

        })


    results = sorted(
        results,
        key=lambda x:x["score"],
        reverse=True
    )


    return jsonify({

        "scanner":"SSW Scalping v3.1 Lite",
        "timeframe":"15m",
        "scanned":len(results),
        "signals":results

    })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8080
    )
