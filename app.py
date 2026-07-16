from flask import Flask, jsonify
import requests

app = Flask(__name__)

BINANCE = "https://api.binance.com"


# filter coin yang tidak cocok untuk scalping
BLOCKLIST = [
    "USDC", "FDUSD", "USDT", "BUSD",
    "TUSD", "USDP", "USD1",
    "XAUT", "PAXG"
]


def ema(values, period):
    k = 2 / (period + 1)
    ema_value = values[0]

    for price in values[1:]:
        ema_value = price * k + ema_value * (1-k)

    return ema_value


def rsi(values, period=14):
    gains = []
    losses = []

    for i in range(1, len(values)):
        change = values[i] - values[i-1]

        if change >= 0:
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

    return round(100 - (100/(1+rs)), 2)


@app.route("/")
def home():
    return "crypto mcp is running"


@app.route("/ssw15m")
def ssw15m():

    ticker = requests.get(
        f"{BINANCE}/api/v3/ticker/24hr"
    ).json()


    pairs = []

    for x in ticker:

        symbol = x["symbol"]

        if not symbol.endswith("USDT"):
            continue

        if any(block in symbol for block in BLOCKLIST):
            continue

        pairs.append(x)


    top50 = sorted(
        pairs,
        key=lambda x: float(x["quoteVolume"]),
        reverse=True
    )[:50]


    signals = []


    for coin in top50:

        symbol = coin["symbol"]

        try:

            candles = requests.get(
                f"{BINANCE}/api/v3/klines",
                params={
                    "symbol": symbol,
                    "interval":"15m",
                    "limit":50
                }
            ).json()


            closes = [
                float(c[4])
                for c in candles
            ]

            volumes = [
                float(c[5])
                for c in candles
            ]


            last_price = closes[-1]

            rsi_value = rsi(closes)

            ema9 = ema(
                closes[-30:],
                9
            )

            ema21 = ema(
                closes[-30:],
                21
            )


            avg_volume = sum(volumes[-20:])/20

            volume_spike = round(
                volumes[-1]/avg_volume,
                2
            )


            score = 0
            reason = []


            if ema9 > ema21:
                score += 30
                reason.append("EMA bullish")


            if 50 < rsi_value < 70:
                score += 20
                reason.append("RSI momentum")


            if volume_spike > 1.5:
                score += 30
                reason.append("Volume spike")


            if closes[-1] > closes[-2]:
                score += 20
                reason.append("Price naik")


            signal = "NEUTRAL"

            if score >= 70:
                signal = "BULLISH"

            elif score <=30:
                signal = "BEARISH"


            signals.append({
                "symbol":symbol,
                "price":last_price,
                "score":score,
                "signal":signal,
                "rsi":rsi_value,
                "volume_spike":volume_spike,
                "reason":reason
            })


        except:
            pass


    signals = sorted(
        signals,
        key=lambda x:x["score"],
        reverse=True
    )


    return jsonify({
        "scanner":"SSW Scalping v3",
        "timeframe":"15m",
        "signals":signals[:20]
    })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8080
    )
