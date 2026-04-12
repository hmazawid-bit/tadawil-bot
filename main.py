import os, json, time, schedule
import yfinance as yf
import pandas_ta as ta
import google.generativeai as genai
import requests

GEMINI_KEY   = os.environ["GEMINI_API_KEY"]
BOT_TOKEN    = os.environ["TELEGRAM_TOKEN"]
CHAT_ID      = os.environ["TELEGRAM_CHAT_ID"]

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

STOCKS = [
    {"symbol": "2222.SR", "name": "أرامكو"},
    {"symbol": "1120.SR", "name": "الراجحي"},
    {"symbol": "1180.SR", "name": "الأهلي"},
    {"symbol": "2010.SR", "name": "سابك"},
    {"symbol": "7010.SR", "name": "STC"},
    {"symbol": "6001.SR", "name": "المراعي"},
    {"symbol": "1050.SR", "name": "بنك الرياض"},
    {"symbol": "4200.SR", "name": "تداول"},
]

def send(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})

def get_data(symbol):
    try:
        df = yf.download(symbol, period="3mo", interval="1d", auto_adjust=True, progress=False)
        if df.empty or len(df) < 30:
            return None
        close = df["Close"].squeeze()
        rsi  = ta.rsi(close, length=14)
        macd = ta.macd(close)
        bb   = ta.bbands(close)
        last = df.iloc[-1]
        prev = df.iloc[-2]
        return {
            "price":   round(float(last["Close"]), 2),
            "change":  round(float((last["Close"]-prev["Close"])/prev["Close"]*100), 2),
            "volume":  int(last["Volume"]),
            "rsi":     round(float(rsi.iloc[-1]), 1),
            "macd":    round(float(macd["MACD_12_26_9"].iloc[-1]), 3),
            "ma20":    round(float(close.rolling(20).mean().iloc[-1]), 2),
            "ma50":    round(float(close.rolling(50).mean().iloc[-1]), 2),
            "bb_up":   round(float(bb["BBU_5_2.0"].iloc[-1]), 2),
            "bb_low":  round(float(bb["BBL_5_2.0"].iloc[-1]), 2),
        }
    except Exception as e:
        print(f"خطأ في {symbol}: {e}")
        return None

def get_signal(name, d):
    prompt = f"""
أنت محلل مالي كمي متخصص في سوق تداول السعودي.
السهم: {name}
السعر: {d['price']} ﷼  |  التغير: {d['change']}%
RSI: {d['rsi']}  |  MACD: {d['macd']}
MA20: {d['ma20']}  |  MA50: {d['ma50']}
بولنجر: أعلى {d['bb_up']} / أدنى {d['bb_low']}
حجم التداول: {d['volume']:,}

أجب بـ JSON فقط:
{{
  "signal": "شراء قوي" أو "شراء" أو "انتظار" أو "بيع",
  "confidence": رقم 0-100,
  "entry": رقم,
  "sl": رقم,
  "tp1": رقم,
  "tp2": رقم,
  "reason": "سبب موجز"
}}"""
    try:
        resp = model.generate_content(prompt)
        text = resp.text.replace("```json","").replace("```","").strip()
        return json.loads(text)
    except Exception as e:
        print(f"خطأ AI {name}: {e}")
        return None

def run_scan():
    print("🔍 بدء المسح...")
    send("🔍 <b>بدء مسح السوق السعودي...</b>")
    buys = []
    for stock in STOCKS:
        data = get_data(stock["symbol"])
        if not data:
            continue
        sig = get_signal(stock["name"], data)
        if not sig:
            continue
        print(f"{stock['name']}: {sig['signal']} ({sig['confidence']}%)")
        if "شراء" in sig["signal"]:
            buys.append({**stock, **data, **sig})
        time.sleep(2)
    if buys:
        buys.sort(key=lambda x: -x["confidence"])
        msg = "🟢 <b>فرص الشراء اليوم</b>\n"
        msg += f"📅 {time.strftime('%Y-%m-%d %H:%M')}\n\n"
        for b in buys:
            msg += f"━━━━━━━━━━━━━━━\n"
            msg += f"<b>{b['name']}</b> — {b['signal']} ✨{b['confidence']}%\n"
            msg += f"💰 السعر: {b['price']} ﷼ ({b['change']:+}%)\n"
            msg += f"📍 دخول: <b>{b['entry']} ﷼</b>\n"
            msg += f"🛑 وقف: <b>{b['sl']} ﷼</b>\n"
            msg += f"🎯 TP1: <b>{b['tp1']} ﷼</b>\n"
            msg += f"🎯 TP2: <b>{b['tp2']} ﷼</b>\n"
            msg += f"💬 {b['reason']}\n\n"
        msg += "━━━━━━━━━━━━━━━\n"
        msg += "⚠️ للأغراض التعليمية فقط"
        send(msg)
    else:
        send("⏳ <b>لا توجد فرص شراء واضحة اليوم</b>")
    print("✅ اكتمل المسح")

schedule.every().day.at("06:15").do(run_scan)

print("✅ النظام يعمل...")
run_scan()

while True:
    schedule.run_pending()
    time.sleep(30)
