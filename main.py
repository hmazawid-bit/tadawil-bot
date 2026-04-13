import os, json, time, schedule
import yfinance as yf
import pandas_ta as ta
import google.generativeai as genai
import requests

GEMINI_KEY = os.environ["GEMINI_API_KEY"]
BOT_TOKEN  = os.environ["TELEGRAM_TOKEN"]
CHAT_ID    = os.environ["TELEGRAM_CHAT_ID"]

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
    {"symbol": "2082.SR", "name": "أكوا باور"},
    {"symbol": "4081.SR", "name": "المملكة القابضة"},
    {"symbol": "1211.SR", "name": "معادن"},
    {"symbol": "2380.SR", "name": "بتروكيم"},
]

def send(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(f"خطأ تيليجرام: {e}")

def get_data(symbol):
    try:
        df = yf.download(symbol, period="3mo", interval="1d", auto_adjust=True, progress=False)
        if df is None or df.empty or len(df) < 50:
            return None

        close  = df["Close"].squeeze().astype(float)
        volume = df["Volume"].squeeze().astype(float)

        rsi_val  = ta.rsi(close, length=14)
        macd_val = ta.macd(close)
        ma20     = close.rolling(20).mean()
        ma50     = close.rolling(50).mean()
        vol10    = volume.rolling(10).mean()

        # بولنجر بدون اعتماد على اسم عمود محدد
        bb_up   = close.rolling(20).mean() + 2 * close.rolling(20).std()
        bb_low  = close.rolling(20).mean() - 2 * close.rolling(20).std()

        current_price = float(close.iloc[-1])
        prev_price    = float(close.iloc[-2])
        current_vol   = float(volume.iloc[-1])
        avg_vol       = float(vol10.iloc[-1])
        high52        = float(close.rolling(252).max().iloc[-1])

        if avg_vol == 0:
            return None

        return {
            "price":       round(current_price, 2),
            "change":      round((current_price - prev_price) / prev_price * 100, 2),
            "rsi":         round(float(rsi_val.iloc[-1]), 1),
            "macd":        round(float(macd_val["MACD_12_26_9"].iloc[-1]), 3),
            "macd_signal": round(float(macd_val["MACDs_12_26_9"].iloc[-1]), 3),
            "ma20":        round(float(ma20.iloc[-1]), 2),
            "ma50":        round(float(ma50.iloc[-1]), 2),
            "bb_up":       round(float(bb_up.iloc[-1]), 2),
            "bb_low":      round(float(bb_low.iloc[-1]), 2),
            "volume":      int(current_vol),
            "avg_volume":  int(avg_vol),
            "vol_ratio":   round(current_vol / avg_vol, 2),
            "high52":      round(high52, 2),
            "dist_high52": round((high52 - current_price) / high52 * 100, 2),
        }
    except Exception as e:
        print(f"خطأ بيانات {symbol}: {e}")
        return None

def passes_filters(d):
    reasons = []
    if not (35 <= d["rsi"] <= 65):
        reasons.append(f"RSI ({d['rsi']})")
    if d["price"] < d["ma20"]:
        reasons.append("تحت MA20")
    if d["macd"] < d["macd_signal"]:
        reasons.append("MACD سلبي")
    if d["vol_ratio"] < 1.2:
        reasons.append(f"حجم ضعيف ({d['vol_ratio']}x)")
    if d["dist_high52"] < 5:
        reasons.append("قرب أعلى 52 أسبوع")
    return len(reasons) == 0, reasons

def get_signal(name, d):
    try:
        prompt = f"""أنت محلل مضاربي متخصص في سوق تداول السعودي.
السهم: {name}
السعر: {d['price']} ﷼ | التغير: {d['change']}%
RSI: {d['rsi']} | MACD: {d['macd']} / Signal: {d['macd_signal']}
MA20: {d['ma20']} | MA50: {d['ma50']}
بولنجر: أعلى {d['bb_up']} / أدنى {d['bb_low']}
حجم: {d['volume']:,} (نسبة: {d['vol_ratio']}x)
المسافة من أعلى 52 أسبوع: {d['dist_high52']}%

قواعد صارمة:
- وقف الخسارة لا يتجاوز 4%
- TP1: ربح 3-5% | TP2: ربح 7-10%
- نسبة المكافأة/المخاطرة لا تقل عن 2:1

أجب بـ JSON فقط بدون أي نص:
{{"signal": "شراء قوي" او "شراء" او "انتظار", "confidence": 0-100, "entry": رقم, "sl": رقم, "tp1": رقم, "tp2": رقم, "rr_ratio": رقم, "reason": "سبب موجز"}}"""

        resp = model.generate_content(prompt)
        text = resp.text.replace("```json","").replace("```","").strip()
        result = json.loads(text)
        if result.get("rr_ratio", 0) < 2:
            return None
        return result
    except Exception as e:
        print(f"خطأ AI {name}: {e}")
        return None

def run_scan():
    try:
        print("بدء المسح...")
        send("🔍 <b>بدء مسح السوق السعودي...</b>")
        buys = []
        filtered = []

        for i, stock in enumerate(STOCKS, 1):
            try:
                print(f"[{i}/{len(STOCKS)}] {stock['name']}")
                data = get_data(stock["symbol"])
                if not data:
                    continue
                passed, reasons = passes_filters(data)
                if not passed:
                    filtered.append(stock["name"])
                    continue
                sig = get_signal(stock["name"], data)
                if sig and "شراء" in sig.get("signal", ""):
                    buys.append({**stock, **data, **sig})
                    print(f"  فرصة! {sig['signal']} @ {sig['entry']}")
            except Exception as e:
                print(f"خطأ في {stock['name']}: {e}")
            time.sleep(2)

        if buys:
            buys.sort(key=lambda x: (-x["confidence"], -x.get("rr_ratio", 0)))
            msg  = "🟢 <b>فرص المضاربة اليوم - تداول</b>\n"
            msg += f"📅 {time.strftime('%Y-%m-%d')} | ⏰ {time.strftime('%H:%M')}\n\n"
            for b in buys:
                sl_pct  = round((b['entry'] - b['sl'])  / b['entry'] * 100, 1)
                tp1_pct = round((b['tp1'] - b['entry']) / b['entry'] * 100, 1)
                tp2_pct = round((b['tp2'] - b['entry']) / b['entry'] * 100, 1)
                msg += "━━━━━━━━━━━━━━━\n"
                msg += f"⚡ <b>{b['name']}</b> — {b['signal']}\n"
                msg += f"📊 ثقة: {b['confidence']}% | R:R = {b.get('rr_ratio','?')}:1\n"
                msg += f"💰 السعر: {b['price']} ﷼ ({b['change']:+}%)\n"
                msg += f"📍 <b>دخول: {b['entry']} ﷼</b>\n"
                msg += f"🛑 <b>وقف: {b['sl']} ﷼</b> (-{sl_pct}%)\n"
                msg += f"🎯 <b>TP1: {b['tp1']} ﷼</b> (+{tp1_pct}%)\n"
                msg += f"🎯 <b>TP2: {b['tp2']} ﷼</b> (+{tp2_pct}%)\n"
                msg += f"📈 RSI: {b['rsi']} | حجم: {b['vol_ratio']}x\n"
                msg += f"💬 {b['reason']}\n\n"
            msg += "━━━━━━━━━━━━━━━\n⚠️ للأغراض التعليمية فقط"
            send(msg)
        else:
            send(f"⏳ <b>لا توجد فرص اليوم</b>\nتم مسح {len(STOCKS)} سهم | مفلتر: {len(filtered)}")

        print(f"اكتمل | فرص: {len(buys)} | مفلتر: {len(filtered)}")

    except Exception as e:
        print(f"خطأ عام: {e}")
        send(f"⚠️ خطأ في المسح: {e}")

schedule.every().day.at("06:15").do(run_scan)
print("النظام يعمل...")
run_scan()

while True:
    try:
        schedule.run_pending()
        time.sleep(30)
    except Exception as e:
        print(f"خطأ: {e}")
        time.sleep(30)
