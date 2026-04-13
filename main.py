import os, json, time, schedule
import yfinance as yf
import pandas_ta as ta
import google.generativeai as genai
import requests

GEMINI_KEY = os.environ["GEMINI_API_KEY"]
BOT_TOKEN  = os.environ["TELEGRAM_TOKEN"]
CHAT_ID    = os.environ["TELEGRAM_CHAT_ID"]

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("gemini-pro")
STOCKS = [
    # طاقة وبتروكيماويات
    {"symbol": "2010.SR", "name": "سابك"},
    {"symbol": "2020.SR", "name": "سابك للمغذيات"},
    {"symbol": "2060.SR", "name": "كيان"},
    {"symbol": "2082.SR", "name": "أكوا باور"},
    {"symbol": "2310.SR", "name": "سبكيم"},
    {"symbol": "2360.SR", "name": "بترورابغ"},
    {"symbol": "2380.SR", "name": "بتروكيم"},
    {"symbol": "2230.SR", "name": "السعودية للكهرباء"},
    # صناعة وتعدين
    {"symbol": "1211.SR", "name": "معادن"},
    {"symbol": "2050.SR", "name": "سافكو"},
    {"symbol": "2130.SR", "name": "التصنيع"},
    {"symbol": "2140.SR", "name": "أنابيب"},
    {"symbol": "3008.SR", "name": "حديد"},
    {"symbol": "3004.SR", "name": "الكابلات"},
    # أسمنت
    {"symbol": "3010.SR", "name": "أسمنت اليمامة"},
    {"symbol": "3020.SR", "name": "أسمنت العربية"},
    {"symbol": "3030.SR", "name": "أسمنت السعودية"},
    {"symbol": "3040.SR", "name": "أسمنت القصيم"},
    {"symbol": "3050.SR", "name": "أسمنت الجنوب"},
    {"symbol": "3060.SR", "name": "أسمنت ينبع"},
    {"symbol": "3080.SR", "name": "أسمنت الشمالية"},
    {"symbol": "3090.SR", "name": "أسمنت طبوك"},
    {"symbol": "3091.SR", "name": "أسمنت نجران"},
    # اتصالات وتقنية
    {"symbol": "7010.SR", "name": "STC"},
    {"symbol": "7020.SR", "name": "موبايلي"},
    {"symbol": "7030.SR", "name": "زين السعودية"},
    # تجزئة وخدمات
    {"symbol": "4003.SR", "name": "BinDawood"},
    {"symbol": "4040.SR", "name": "أسواق"},
    {"symbol": "4081.SR", "name": "المملكة القابضة"},
    {"symbol": "4082.SR", "name": "مجموعة MBC"},
    # غذاء وزراعة
    {"symbol": "6001.SR", "name": "المراعي"},
    {"symbol": "6002.SR", "name": "حلواني"},
    {"symbol": "6010.SR", "name": "سدافكو"},
    {"symbol": "6004.SR", "name": "الغذائية"},
    {"symbol": "6014.SR", "name": "أنعام"},
    # عقارات
    {"symbol": "4090.SR", "name": "دار الأركان"},
    {"symbol": "4100.SR", "name": "مكة"},
    {"symbol": "4110.SR", "name": "جبل عمر"},
    {"symbol": "4150.SR", "name": "طيبة"},
    {"symbol": "4180.SR", "name": "أملاك العقارية"},
    # نقل ولوجستيات
    {"symbol": "4261.SR", "name": "ناقلات"},
    {"symbol": "4262.SR", "name": "البحري"},
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
        bb_up    = close.rolling(20).mean() + 2 * close.rolling(20).std()
        bb_low   = close.rolling(20).mean() - 2 * close.rolling(20).std()

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
    if not (30 <= d["rsi"] <= 70):
        reasons.append(f"RSI ({d['rsi']})")
    if d["price"] < d["ma50"]:
        reasons.append("تحت MA50")
    if d["vol_ratio"] < 0.8:
        reasons.append(f"حجم ضعيف ({d['vol_ratio']}x)")
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

أجب بـ JSON فقط:
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
        send(f"🔍 <b>بدء مسح السوق السعودي</b>\n📊 {len(STOCKS)} سهم (بدون بنوك وتأمين)")
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
                    filtered.append(f"{stock['name']}: {', '.join(reasons)}")
                    continue
                sig = get_signal(stock["name"], data)
                if sig and "شراء" in sig.get("signal", ""):
                    buys.append({**stock, **data, **sig})
                    print(f"  ✅ {sig['signal']} @ {sig['entry']}")
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
            msg  = f"⏳ <b>لا توجد فرص اليوم</b>\n"
            msg += f"🔍 مسح {len(STOCKS)} سهم | مفلتر: {len(filtered)}\n\n"
            msg += "<b>أسباب الاستبعاد:</b>\n"
            for f in filtered[:10]:
                msg += f"• {f}\n"
            send(msg)

        print(f"اكتمل | فرص: {len(buys)} | مفلتر: {len(filtered)}")

    except Exception as e:
        print(f"خطأ عام: {e}")
        send(f"⚠️ خطأ: {e}")

schedule.every().day.at("06:15").do(run_scan)
print(f"النظام يعمل | {len(STOCKS)} سهم")
run_scan()

while True:
    try:
        schedule.run_pending()
        time.sleep(30)
    except Exception as e:
        print(f"خطأ: {e}")
        time.sleep(30)
