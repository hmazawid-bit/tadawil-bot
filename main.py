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
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "HTML"
    })

def get_data(symbol):
    try:
        df = yf.download(symbol, period="3mo", interval="1d",
                         auto_adjust=True, progress=False)
        if df.empty or len(df) < 50:
            return None

        close  = df["Close"].squeeze()
        volume = df["Volume"].squeeze()

        rsi    = ta.rsi(close, length=14)
        macd   = ta.macd(close)
        bb     = ta.bbands(close)
        ma20   = close.rolling(20).mean()
        ma50   = close.rolling(50).mean()
        vol10  = volume.rolling(10).mean()

        last   = df.iloc[-1]
        prev   = df.iloc[-2]
        high52 = close.rolling(252).max().iloc[-1]

        current_price = float(last["Close"])
        current_vol   = float(last["Volume"])
        avg_vol       = float(vol10.iloc[-1])

        return {
            "price":        round(current_price, 2),
            "change":       round((current_price - float(prev["Close"])) / float(prev["Close"]) * 100, 2),
            "rsi":          round(float(rsi.iloc[-1]), 1),
            "macd":         round(float(macd["MACD_12_26_9"].iloc[-1]), 3),
            "macd_signal":  round(float(macd["MACDs_12_26_9"].iloc[-1]), 3),
            "ma20":         round(float(ma20.iloc[-1]), 2),
            "ma50":         round(float(ma50.iloc[-1]), 2),
            "bb_up":        round(float(bb["BBU_5_2.0"].iloc[-1]), 2),
            "bb_low":       round(float(bb["BBL_5_2.0"].iloc[-1]), 2),
            "volume":       int(current_vol),
            "avg_volume":   int(avg_vol),
            "vol_ratio":    round(current_vol / avg_vol, 2),
            "high52":       round(float(high52), 2),
            "dist_high52":  round((high52 - current_price) / high52 * 100, 2),
        }
    except Exception as e:
        print(f"خطأ في {symbol}: {e}")
        return None

def passes_filters(d):
    """فلاتر مضاربية للسوق السعودي"""
    reasons = []

    # 1. RSI بين 35 و 65
    if not (35 <= d["rsi"] <= 65):
        reasons.append(f"RSI خارج النطاق ({d['rsi']})")

    # 2. السعر فوق MA20
    if d["price"] < d["ma20"]:
        reasons.append("السعر تحت MA20")

    # 3. MACD إيجابي أو أعلى من الـ signal
    if d["macd"] < d["macd_signal"]:
        reasons.append("MACD سلبي")

    # 4. حجم التداول أعلى من المتوسط بـ 20%
    if d["vol_ratio"] < 1.2:
        reasons.append(f"حجم تداول ضعيف ({d['vol_ratio']}x)")

    # 5. بعيد عن أعلى 52 أسبوع بأكثر من 5%
    if d["dist_high52"] < 5:
        reasons.append(f"قريب من أعلى 52 أسبوع")

    return len(reasons) == 0, reasons

def get_signal(name, d):
    prompt = f"""أنت محلل مضاربي متخصص في سوق تداول السعودي.

السهم: {name}
السعر الحالي: {d['price']} ﷼  |  التغير: {d['change']}%
RSI: {d['rsi']}  |  MACD: {d['macd']} / Signal: {d['macd_signal']}
MA20: {d['ma20']}  |  MA50: {d['ma50']}
بولنجر: أعلى {d['bb_up']} / أدنى {d['bb_low']}
حجم التداول: {d['volume']:,} (نسبة للمتوسط: {d['vol_ratio']}x)
المسافة من أعلى 52 أسبوع: {d['dist_high52']}%

قواعد صارمة للتوصية:
- وقف الخسارة: تحت آخر قاع + 1.5%، ولا يتجاوز 4% من سعر الدخول
- TP1: ربح 3-5% من الدخول
- TP2: ربح 7-10% من الدخول
- نسبة المكافأة/المخاطرة لا تقل عن 2:1
- إذا لم تتوفر الشروط، أعطِ "انتظار"

أجب بـ JSON فقط:
{{
  "signal": "شراء قوي" أو "شراء" أو "انتظار",
  "confidence": رقم 0-100,
  "entry": رقم,
  "sl": رقم,
  "tp1": رقم,
  "tp2": رقم,
  "rr_ratio": رقم,
  "reason": "سبب موجز"
}}"""

    try:
        resp = model.generate_content(prompt)
        text = resp.text.replace("```json","").replace("```","").strip()
        result = json.loads(text)

        # تحقق من نسبة المكافأة/المخاطرة
        if result.get("rr_ratio", 0) < 2:
            return None

        return result
    except Exception as e:
        print(f"خطأ AI {name}: {e}")
        return None

def run_scan():
    print("🔍 بدء المسح...")
    send("🔍 <b>بدء مسح السوق السعودي...</b>\nيتحقق من الفلاتر المضاربية...")

    buys      = []
    filtered  = []
    errors    = []

    for stock in STOCKS:
        data = get_data(stock["symbol"])
        if not data:
            errors.append(stock["name"])
            continue

        passed, reasons = passes_filters(data)

        if not passed:
            filtered.append(f"{stock['name']}: {', '.join(reasons)}")
            print(f"❌ {stock['name']} - فشل الفلتر: {reasons}")
            continue

        print(f"✅ {stock['name']} - اجتاز الفلاتر، يحلل...")
        sig = get_signal(stock["name"], data)

        if sig and "شراء" in sig.get("signal", ""):
            buys.append({**stock, **data, **sig})

        time.sleep(2)

    # ── إرسال النتائج ──────────────────────────
    if buys:
        buys.sort(key=lambda x: (-x["confidence"], -x.get("rr_ratio", 0)))

        msg  = "🟢 <b>فرص المضاربة اليوم - تداول</b>\n"
        msg += f"📅 {time.strftime('%Y-%m-%d')} | ⏰ {time.strftime('%H:%M')}\n"
        msg += f"✅ اجتاز الفلاتر: {len(buys)} سهم\n\n"

        for b in buys:
            sl_pct  = round((b['entry'] - b['sl']) / b['entry'] * 100, 1)
            tp1_pct = round((b['tp1'] - b['entry']) / b['entry'] * 100, 1)
            tp2_pct = round((b['tp2'] - b['entry']) / b['entry'] * 100, 1)

            msg += f"━━━━━━━━━━━━━━━\n"
            msg += f"⚡ <b>{b['name']}</b> — {b['signal']}\n"
            msg += f"📊 ثقة: {b['confidence']}% | R:R = {b.get('rr_ratio','?')}:1\n"
            msg += f"💰 السعر: {b['price']} ﷼ ({b['change']:+}%)\n"
            msg += f"📍 <b>دخول: {b['entry']} ﷼</b>\n"
            msg += f"🛑 <b>وقف: {b['sl']} ﷼</b> (-{sl_pct}%)\n"
            msg += f"🎯 <b>TP1: {b['tp1']} ﷼</b> (+{tp1_pct}%)\n"
            msg += f"🎯 <b>TP2: {b['tp2']} ﷼</b> (+{tp2_pct}%)\n"
            msg += f"📈 RSI: {b['rsi']} | حجم: {b['vol_ratio']}x\n"
            msg += f"💬 {b['reason']}\n\n"

        msg += "━━━━━━━━━━━━━━━\n"
        msg += "⚠️ للأغراض التعليمية فقط"
        send(msg)

    else:
        msg  = "⏳ <b>لا توجد فرص مضاربة اليوم</b>\n\n"
        if filtered:
            msg += "❌ <b>أسهم فشلت الفلاتر:</b>\n"
            for f in filtered[:5]:
                msg += f"• {f}\n"
        send(msg)

    print(f"✅ اكتمل | فرص: {len(buys)} | مفلتر: {len(filtered)}")

# كل يوم 6:15 UTC = 9:15 صباحاً بتوقيت الرياض
schedule.every().day.at("06:15").do(run_scan)

print("✅ النظام يعمل...")
run_scan()  # تشغيل فوري للاختبار

while True:
    schedule.run_pending()
    time.sleep(30)
