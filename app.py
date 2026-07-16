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
        r = requests.get(
            url,
            params=params,
            timeout=5
        )
        return r.json()
    except:
        return None


def ema(values, period):
    if len(values) < period:
        return 0

    k = 2/(period+1)
    result = sum(values[:period])/period

    for x in values[period:]:
        result = x*k + result*(1-k)

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

    return round(
        100-(100/(1+rs)),
        2
    )


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


    top30=sorted(
        coins,
        key=lambda x:float(x["quoteVolume"]),
        reverse=True
    )[:30]


    signals=[]


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

        rsi_value=rsi(closes)

        ema9=ema(closes,9)
        ema21=ema(closes,21)


        volume_ratio=round(
            volumes[-1] /
            (sum(volumes[-20:])/20),
            2
        )


        candle_green = closes[-1] > closes[-2]


        confidence=0
        reason=[]


        if ema9 > ema21:
            confidence +=30
            reason.append("EMA bullish")
        else:
            confidence -=20
            reason.append("EMA bearish")


        if 55 <= rsi_value <=70:
            confidence +=25
            reason.append("RSI strong")


        if rsi_value <40:
            confidence +=20
            reason.append("RSI weak")


        if volume_ratio >=1.2:
            confidence +=30
            reason.append("Volume confirmed")


        if candle_green:
            confidence +=15
            reason.append("Candle bullish")


        signal="AVOID"


        if (
            ema9 > ema21
            and 55 <= rsi_value <=70
            and volume_ratio >=1.2
            and candle_green
        ):
            signal="LONG"


        elif (
            ema9 < ema21
            and rsi_value <40
            and volume_ratio >=1.2
            and not candle_green
        ):
            signal="SHORT"


        if signal!="AVOID":

            if signal=="LONG":

                sl=round(price*0.985,6)
                tp1=round(price*1.015,6)
                tp2=round(price*1.03,6)

            else:

                sl=round(price*1.015,6)
                tp1=round(price*0.985,6)
                tp2=round(price*0.97,6)


            signals.append({

                "symbol":symbol,
                "signal":signal,
                "confidence":confidence,
                "entry":price,
                "tp1":tp1,
                "tp2":tp2,
                "sl":sl,
                "rsi":rsi_value,
                "volume_ratio":volume_ratio,
                "reason":reason

            })


    signals=sorted(
        signals,
        key=lambda x:x["confidence"],
        reverse=True
    )


    return jsonify({

        "scanner":"SSW v5 Sniper",
        "timeframe":"15m",
        "signals":signals[:10]

    })


if __name__=="__main__":
    app.run(
        host="0.0.0.0",
        port=8080
    )
