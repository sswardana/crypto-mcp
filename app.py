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


def calc_rsi(values, period=14):

    if len(values) <= period:
        return 50

    gains = 0
    losses = 0

    for i in range(1, period+1):

        diff = values[-i] - values[-i-1]

        if diff > 0:
            gains += diff
        else:
            losses += abs(diff)

    if losses == 0:
        return 100

    rs = gains/losses

    return round(
        100-(100/(1+rs)),
        2
    )


def trade_levels(price, side):

    if side == "LONG":
        return {
            "entry":price,
            "tp1":round(price*1.015,6),
            "tp2":round(price*1.03,6),
            "sl":round(price*0.985,6)
        }

    return {
        "entry":price,
        "tp1":round(price*0.985,6),
        "tp2":round(price*0.97,6),
        "sl":round(price*1.015,6)
    }


def btc_market():

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


    close=[
        float(x[4])
        for x in candles
    ]

    e9=ema(close,9)
    e21=ema(close,21)


    if e9 > e21:
        return "BULLISH"

    return "BEARISH"


@app.route("/")
def home():
    return "crypto mcp is running"


@app.route("/ssw15m")
def scanner():

    btc_trend = btc_market()


    ticker=get_json(
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


    top30=sorted(
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

        rsi=calc_rsi(close)

        vol_ratio=round(
            volume[-1] /
            (sum(volume[-20:])/20),
            2
        )


        candle_up = close[-1] > close[-2]


        long_score=0
        short_score=0

        long_reason=[]
        short_reason=[]


        if e9 > e21:
            long_score+=35
            long_reason.append("EMA bullish")
        else:
            short_score+=35
            short_reason.append("EMA bearish")


        if rsi > 50:
            long_score+=25
            long_reason.append("RSI strength")

        if rsi <45:
            short_score+=25
            short_reason.append("RSI weakness")


        if vol_ratio > 1:
            long_score+=25
            short_score+=25

            long_reason.append("Volume")
            short_reason.append("Volume")


        if candle_up:
            long_score+=15
            long_reason.append("Green candle")
        else:
            short_score+=15
            short_reason.append("Red candle")


        # BTC filter
        if btc_trend=="BEARISH":
            long_score-=15


        if (
            long_score >=70
            and btc_trend != "BEARISH"
        ):

            item={
                "symbol":symbol,
                "signal":"LONG",
                "confidence":long_score,
                "rsi":rsi,
                "volume_ratio":vol_ratio,
                "reason":long_reason
            }

            item.update(
                trade_levels(price,"LONG")
            )

            long.append(item)


        elif (
            short_score >=70
            and rsi >30
        ):

            item={
                "symbol":symbol,
                "signal":"SHORT",
                "confidence":short_score,
                "rsi":rsi,
                "volume_ratio":vol_ratio,
                "reason":short_reason
            }

            item.update(
                trade_levels(price,"SHORT")
            )

            short.append(item)


        elif max(long_score,short_score) >=50:

            watch.append({

                "symbol":symbol,
                "confidence":max(long_score,short_score),
                "rsi":rsi,
                "volume_ratio":vol_ratio

            })


    return jsonify({

        "scanner":"SSW v5.2 Calibration",
        "timeframe":"15m",

        "market":{
            "BTC":btc_trend
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
