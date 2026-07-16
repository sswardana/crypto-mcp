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

    return round(100-(100/(1+rs)),2)


def levels(price, side):

    if side == "LONG":
        return {
            "entry": price,
            "tp1": round(price*1.015,8),
            "tp2": round(price*1.03,8),
            "sl": round(price*0.985,8)
        }

    return {
        "entry": price,
        "tp1": round(price*0.985,8),
        "tp2": round(price*0.97,8),
        "sl": round(price*1.015,8)
    }


def check_risk(signal, btc, rsi_value):

    if signal == "LONG" and btc == "BEARISH":
        return "HIGH"

    if signal == "SHORT" and rsi_value < 30:
        return "HIGH"

    if btc == "BULLISH":
        return "LOW"

    return "MEDIUM"


def entry_quality(confidence, risk):

    if confidence >= 80 and risk == "LOW":
        return "GOOD"

    if confidence >= 70:
        return "CAUTION"

    return "AVOID"


def btc_trend():

    candles = get_json(
        f"{BINANCE}/api/v3/klines",
        {
            "symbol":"BTCUSDT",
            "interval":"15m",
            "limit":50
        }
    )

    if not candles:
        return "UNKNOWN"

    close = [
        float(x[4])
        for x in candles
    ]

    if ema(close,9) > ema(close,21):
        return "BULLISH"

    return "BEARISH"


@app.route("/")
def home():
    return "crypto mcp is running"


@app.route("/ssw15m")
def scanner():

    btc = btc_trend()

    ticker = get_json(
        f"{BINANCE}/api/v3/ticker/24hr"
    )

    if not ticker:
        return jsonify({
            "error":"binance error"
        })


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
    short=[]
    watch=[]


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


        close=[
            float(x[4])
            for x in candles
        ]

        volume=[
            float(x[5])
            for x in candles
        ]


        price=close[-1]

        e9=ema(close,9)
        e21=ema(close,21)

        rsi_value=rsi(close)

        vol=round(
            volume[-1] /
            (sum(volume[-20:])/20),
            2
        )


        green = close[-1] > close[-2]


        long_score=0
        short_score=0

        long_reason=[]
        short_reason=[]


        if e9 > e21:
            long_score+=30
            long_reason.append("EMA bullish")
        else:
            short_score+=30
            short_reason.append("EMA bearish")


        if rsi_value > 50:
            long_score+=25
            long_reason.append("RSI strength")

        if 30 < rsi_value < 45:
            short_score+=20
            short_reason.append("RSI weakness")

        if rsi_value <= 30:
            short_score-=15
            short_reason.append("Oversold risk")


        if vol > 1:
            long_score+=20
            short_score+=20
            long_reason.append("Volume")
            short_reason.append("Volume")


        if green:
            long_score+=15
            long_reason.append("Green candle")
        else:
            short_score+=15
            short_reason.append("Red candle")


        if btc=="BEARISH":
            long_score-=15


        if long_score >= 80:

            confidence=min(long_score,90)

            risk=check_risk(
                "LONG",
                btc,
                rsi_value
            )

            data={
                "symbol":symbol,
                "signal":"LONG",
                "grade":"STRONG LONG" if confidence>=80 else "NORMAL LONG",
                "confidence":confidence,
                "risk":risk,
                "entry_quality":entry_quality(confidence,risk),
                "rsi":rsi_value,
                "volume_ratio":vol,
                "reason":long_reason
            }

            data.update(
                levels(price,"LONG")
            )

            long.append(data)


        elif short_score >= 80:

            confidence=min(short_score,90)

            risk=check_risk(
                "SHORT",
                btc,
                rsi_value
            )

            data={
                "symbol":symbol,
                "signal":"SHORT",
                "grade":"STRONG SHORT" if confidence>=80 else "NORMAL SHORT",
                "confidence":confidence,
                "risk":risk,
                "entry_quality":entry_quality(confidence,risk),
                "rsi":rsi_value,
                "volume_ratio":vol,
                "reason":short_reason
            }

            data.update(
                levels(price,"SHORT")
            )

            short.append(data)


        elif max(long_score,short_score)>=50:

            watch.append({
                "symbol":symbol,
                "confidence":max(long_score,short_score),
                "rsi":rsi_value,
                "volume_ratio":vol
            })


    return jsonify({

        "scanner":"SSW v5.4 Simple Risk",
        "timeframe":"15m",

        "market":{
            "BTC":btc
        },

        "long":sorted(
            long,
            key=lambda x:x["confidence"],
            reverse=True
        )[:5],

        "short":sorted(
            short,
            key=lambda x:x["confidence"],
            reverse=True
        )[:5],

        "watchlist":sorted(
            watch,
            key=lambda x:x["confidence"],
            reverse=True
        )[:10]

    })


if __name__=="__main__":
    app.run(
        host="0.0.0.0",
        port=8080
    )
