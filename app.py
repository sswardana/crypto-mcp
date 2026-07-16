from flask import Flask, jsonify
import requests

app = Flask(__name__)

BINANCE = "https://api.binance.com"

BLOCKLIST = [
    "USDC","FDUSD","BUSD",
    "TUSD","USDP","USD1",
    "XAUT","PAXG"
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

    for price in values[period:]:
        result = price*k + result*(1-k)

    return result


def rsi(values, period=14):

    if len(values) <= period:
        return 50

    gain = []
    loss = []

    for i in range(1,len(values)):
        diff = values[i]-values[i-1]

        if diff >= 0:
            gain.append(diff)
            loss.append(0)
        else:
            gain.append(0)
            loss.append(abs(diff))

    avg_gain = sum(gain[-period:])/period
    avg_loss = sum(loss[-period:])/period

    if avg_loss == 0:
        return 100

    rs = avg_gain/avg_loss

    return round(
        100-(100/(1+rs)),
        2
    )


@app.route("/")
def home():
    return "crypto mcp is running"


@app.route("/ssw15m")
def scanner():

    ticker = get_json(
        f"{BINANCE}/api/v3/ticker/24hr"
    )

    if not ticker:
        return jsonify({"error":"binance error"})


    coins=[]

    for x in ticker:

        symbol=x["symbol"]

        if not symbol.endswith("USDT"):
            continue

        if any(b in symbol for b in BLOCKLIST):
            continue

        coins.append(x)


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


        close=[
            float(x[4])
            for x in candles
        ]

        volume=[
            float(x[5])
            for x in candles
        ]


        current=close[-1]

        rsi_value=rsi(close)

        ema9=ema(close,9)
        ema21=ema(close,21)


        avg_vol=sum(volume[-20:])/20

        volume_ratio=round(
            volume[-1]/avg_vol,
            2
        )


        score=0
        reason=[]


        if ema9 > ema21:
            score+=30
            reason.append("EMA bullish")
        else:
            score-=20
            reason.append("EMA bearish")


        if 50 < rsi_value < 70:
            score+=20
            reason.append("RSI momentum")

        elif rsi_value < 35:
            score-=10
            reason.append("RSI weak")


        if volume_ratio > 1.2:
            score+=30
            reason.append("Volume spike")

        elif volume_ratio < 0.7:
            score-=10


        if current > close[-2]:
            score+=20
            reason.append("Price naik")


        if score >=70:
            signal="LONG"

        elif score <=20:
            signal="SHORT"

        else:
            signal="WATCH"


        entry=current

        if signal=="LONG":

            sl=round(
                entry*0.985,
                6
            )

            tp=round(
                entry*1.03,
                6
            )

        elif signal=="SHORT":

            sl=round(
                entry*1.015,
                6
            )

            tp=round(
                entry*0.97,
                6
            )

        else:

            sl=None
            tp=None


        signals.append({

            "symbol":symbol,
            "signal":signal,
            "score":score,
            "entry":entry,
            "stop_loss":sl,
            "take_profit":tp,
            "rsi":rsi_value,
            "volume_ratio":volume_ratio,
            "reason":reason

        })


    signals=sorted(
        signals,
        key=lambda x:x["score"],
        reverse=True
    )


    return jsonify({

        "scanner":"SSW Scalping v4",
        "timeframe":"15m",
        "signals":signals[:20]

    })


if __name__=="__main__":
    app.run(
        host="0.0.0.0",
        port=8080
    )
