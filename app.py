from flask import Flask, jsonify
import requests

app = Flask(__name__)

BINANCE = "https://api.binance.com"

BLOCKLIST = [
    "USDC","FDUSD","BUSD",
    "TUSD","USDP","USD1",
    "RLUSD","XAUT","PAXG",
    "EUR"
]


def get_json(url, params=None):
    try:
        r = requests.get(url, params=params, timeout=5)
        return r.json()
    except:
        return None


def ema(values, period):
    if len(values) < period:
        return 0

    k = 2/(period+1)
    result = sum(values[:period])/period

    for price in values[period:]:
        result = price*k + result*(1-k)

    return result


def rsi(values, period=14):

    if len(values) <= period:
        return 50

    gain = 0
    loss = 0

    for i in range(1, period+1):
        diff = values[-i] - values[-i-1]

        if diff > 0:
            gain += diff
        else:
            loss += abs(diff)

    if loss == 0:
        return 100

    rs = gain/loss

    return round(100-(100/(1+rs)),2)


def make_trade(price, side):

    if side == "LONG":
        return {
            "entry": price,
            "tp1": round(price*1.015,6),
            "tp2": round(price*1.03,6),
            "sl": round(price*0.985,6)
        }

    if side == "SHORT":
        return {
            "entry": price,
            "tp1": round(price*0.985,6),
            "tp2": round(price*0.97,6),
            "sl": round(price*1.015,6)
        }


@app.route("/")
def home():
    return "crypto mcp is running"


@app.route("/ssw15m")
def ssw():

    ticker = get_json(
        f"{BINANCE}/api/v3/ticker/24hr"
    )

    if not ticker:
        return jsonify({"error":"binance error"})


    coins=[]

    for c in ticker:

        symbol=c["symbol"]

        if not symbol.endswith("USDT"):
            continue

        if any(x in symbol for x in BLOCKLIST):
            continue

        coins.append(c)


    top30 = sorted(
        coins,
        key=lambda x:float(x["quoteVolume"]),
        reverse=True
    )[:30]


    long=[]
    watch=[]
    short=[]


    for coin in top30:

        symbol=coin["symbol"]

        candles=get_json(
            f"{BINANCE}/api/v3/klines",
            {
                "symbol":symbol,
                "interval":"15m",
                "limit":50
            }
        )

        if not candles:
            continue


        closes=[
            float(x[4])
            for x in candles
        ]

        volumes=[
            float(x[5])
            for x in candles
        ]


        price=closes[-1]

        ema9=ema(closes,9)
        ema21=ema(closes,21)

        rsi_value=rsi(closes)

        volume_ratio=round(
            volumes[-1] /
            (sum(volumes[-20:])/20),
            2
        )


        confidence=0
        reason=[]


        if ema9 > ema21:
            confidence+=30
            reason.append("EMA bullish")
        else:
            confidence-=20
            reason.append("EMA bearish")


        if rsi_value > 50:
            confidence+=25
            reason.append("RSI naik")

        elif rsi_value <45:
            confidence+=20
            reason.append("RSI lemah")


        if volume_ratio > 1:
            confidence+=25
            reason.append("Volume masuk")


        if closes[-1] > closes[-2]:
            confidence+=10
            reason.append("Candle hijau")


        item={
            "symbol":symbol,
            "confidence":confidence,
            "rsi":rsi_value,
            "volume_ratio":volume_ratio,
            "reason":reason
        }


        if (
            ema9 > ema21
            and rsi_value >50
            and volume_ratio >1
        ):

            item.update(
                make_trade(price,"LONG")
            )

            item["signal"]="LONG"
            long.append(item)


        elif (
            ema9 < ema21
            and rsi_value <45
            and volume_ratio >1
        ):

            item.update(
                make_trade(price,"SHORT")
            )

            item["signal"]="SHORT"
            short.append(item)


        elif
