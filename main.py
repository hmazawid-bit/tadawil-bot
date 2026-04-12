import os, json, time, schedule
import yfinance as yf
import pandas_ta as ta
from google import genai
import requests

GEMINI_KEY = os.environ["GEMINI_API_KEY"]
BOT_TOKEN  = os.environ["TELEGRAM_TOKEN"]
CHAT_ID    = os.environ["TELEGRAM_CHAT_ID"]

client = genai.Client(api_key=GEMINI_KEY)

STOCKS = [
    # مصرفي
    {"symbol": "1010.SR", "name": "الرياض"},
    {"symbol": "1020.SR", "name": "الجزيرة"},
    {"symbol": "1030.SR", "name": "السعودي الفرنسي"},
    {"symbol": "1050.SR", "name": "بنك الرياض"},
    {"symbol": "1060.SR", "name": "العربي الوطني"},
    {"symbol": "1080.SR", "name": "الخليج"},
    {"symbol": "1120.SR", "name": "الراجحي"},
    {"symbol": "1140.SR", "name": "البلاد"},
    {"symbol": "1150.SR", "name": "الإنماء"},
    {"symbol": "1180.SR", "name": "الأهلي"},
    {"symbol": "1182.SR", "name": "الاستثمار"},
    # طاقة وبتروكيماويات
    {"symbol": "2010.SR", "name": "سابك"},
    {"symbol": "2020.SR", "name": "سابك للمغذيات"},
    {"symbol": "2060.SR", "name": "كيان"},
    {"symbol": "2080.SR", "name": "الشرقية للتطوير"},
    {"symbol": "2082.SR", "name": "أكوا باور"},
    {"symbol": "2090.SR", "name": "النمالج"},
    {"symbol": "2100.SR", "name": "وفرة"},
    {"symbol": "2110.SR", "name": "سابك الابتكارية"},
    {"symbol": "2150.SR", "name": "يانسابكو"},
    {"symbol": "2160.SR", "name": "نجران سمنت"},
    {"symbol": "2170.SR", "name": "المتقدمة"},
    {"symbol": "2180.SR", "name": "حلول"},
    {"symbol": "2200.SR", "name": "أرامكو"},
    {"symbol": "2210.SR", "name": "نوفا"},
    {"symbol": "2220.SR", "name": "إيثيل"},
    {"symbol": "2222.SR", "name": "أرامكو"},
    {"symbol": "2223.SR", "name": "المجموعة السعودية"},
    {"symbol": "2230.SR", "name": "السعودية للكهرباء"},
    {"symbol": "2240.SR", "name": "زين السعودية"},
    {"symbol": "2250.SR", "name": "جبسكو"},
    {"symbol": "2290.SR", "name": "أبوقير"},
    {"symbol": "2300.SR", "name": "سواني"},
    {"symbol": "2310.SR", "name": "سبكيم"},
    {"symbol": "2320.SR", "name": "الصناعات الوطنية"},
    {"symbol": "2330.SR", "name": "أدوار"},
    {"symbol": "2340.SR", "name": "متكور"},
    {"symbol": "2350.SR", "name": "أسمنت العربية"},
    {"symbol": "2360.SR", "name": "بترورابغ"},
    {"symbol": "2370.SR", "name": "مدينة المعرفة"},
    {"symbol": "2380.SR", "name": "بتروكيم"},
    {"symbol": "2381.SR", "name": "فيبكو"},
    # صناعة وتعدين
    {"symbol": "1211.SR", "name": "معادن"},
    {"symbol": "2050.SR", "name": "سافكو"},
    {"symbol": "2120.SR", "name": "ميبكو"},
    {"symbol": "2130.SR", "name": "التصنيع"},
    {"symbol": "2140.SR", "name": "أنابيب"},
    {"symbol": "2190.SR", "name": "جدة"},
    {"symbol": "3001.SR", "name": "فيصل الرشيد"},
    {"symbol": "3002.SR", "name": "يونيفرسال"},
    {"symbol": "3003.SR", "name": "الجوف"},
    {"symbol": "3004.SR", "name": "الكابلات"},
    {"symbol": "3005.SR", "name": "فيبكو"},
    {"symbol": "3007.SR", "name": "طباعة الإعلام"},
    {"symbol": "3008.SR", "name": "حديد"},
    {"symbol": "3009.SR", "name": "أسمنت الجوف"},
    {"symbol": "3010.SR", "name": "أسمنت اليمامة"},
    {"symbol": "3020.SR", "name": "أسمنت العربية"},
    {"symbol": "3030.SR", "name": "أسمنت السعودية"},
    {"symbol": "3040.SR", "name": "أسمنت القصيم"},
    {"symbol": "3050.SR", "name": "أسمنت الجنوب"},
    {"symbol": "3060.SR", "name": "أسمنت ينبع"},
    {"symbol": "3080.SR", "name": "أسمنت الشمالية"},
    {"symbol": "3090.SR", "name": "أسمنت طبوك"},
    {"symbol": "3091.SR", "name": "أسمنت نجران"},
    {"symbol": "3092.SR", "name": "أسمنت حائل"},
    # اتصالات وتقنية
    {"symbol": "7010.SR", "name": "STC"},
    {"symbol": "7020.SR", "name": "موبايلي"},
    {"symbol": "7030.SR", "name": "زين السعودية"},
    {"symbol": "7040.SR", "name": "سلوى"},
    {"symbol": "7200.SR", "name": "أريبيان إنترنت"},
    {"symbol": "7203.SR", "name": "إيلاف"},
    {"symbol": "7204.SR", "name": "أمن للتقنية"},
    # تجزئة وخدمات
    {"symbol": "4001.SR", "name": "ثمار"},
    {"symbol": "4002.SR", "name": "المتطورة"},
    {"symbol": "4003.SR", "name": "BinDawood"},
    {"symbol": "4006.SR", "name": "الجميلة"},
    {"symbol": "4007.SR", "name": "الحكير"},
    {"symbol": "4008.SR", "name": "عبدالعزيز الصالح"},
    {"symbol": "4009.SR", "name": "العليان"},
    {"symbol": "4011.SR", "name": "فواز الحكير"},
    {"symbol": "4012.SR", "name": "ألماني"},
    {"symbol": "4013.SR", "name": "صدى"},
    {"symbol": "4020.SR", "name": "مدى"},
    {"symbol": "4030.SR", "name": "البلاد"},
    {"symbol": "4031.SR", "name": "نادك"},
    {"symbol": "4040.SR", "name": "أسواق"},
    {"symbol": "4050.SR", "name": "سيكو"},
    {"symbol": "4051.SR", "name": "سلامة"},
    {"symbol": "4061.SR", "name": "صفوة"},
    {"symbol": "4070.SR", "name": "الدريم"},
    {"symbol": "4071.SR", "name": "مجدي"},
    {"symbol": "4080.SR", "name": "الشرايع"},
    {"symbol": "4081.SR", "name": "المملكة القابضة"},
    {"symbol": "4082.SR", "name": "مجموعة MBC"},
    # غذاء وزراعة
    {"symbol": "6001.SR", "name": "المراعي"},
    {"symbol": "6002.SR", "name": "حلواني"},
    {"symbol": "6004.SR", "name": "الغذائية"},
    {"symbol": "6010.SR", "name": "سدافكو"},
    {"symbol": "6013.SR", "name": "الحافظ"},
    {"symbol": "6014.SR", "name": "أنعام"},
    {"symbol": "6015.SR", "name": "جازادكو"},
    {"symbol": "6016.SR", "name": "بيشة للزراعة"},
    {"symbol": "6017.SR", "name": "ثروات"},
    {"symbol": "6020.SR", "name": "التكامل"},
    # مالي واستثمار
    {"symbol": "4200.SR", "name": "تداول"},
    {"symbol": "4210.SR", "name": "العلم"},
    {"symbol": "4240.SR", "name": "الرياض المالية"},
    {"symbol": "4250.SR", "name": "السعودية للاستثمار"},
    {"symbol": "4260.SR", "name": "صروح"},
    {"symbol": "4270.SR", "name": "أرامكو ريت"},
    {"symbol": "4280.SR", "name": "الرياض ريت"},
    {"symbol": "4290.SR", "name": "جازان"},
    {"symbol": "4300.SR", "name": "الأولى للتمويل"},
    {"symbol": "4310.SR", "name": "مصرف الراجحي"},
    {"symbol": "4320.SR", "name": "أملاك"},
    {"symbol": "4330.SR", "name": "تمويل"},
    # عقارات
    {"symbol": "4020.SR", "name": "مدى"},
    {"symbol": "4090.SR", "name": "دار الأركان"},
    {"symbol": "4100.SR", "name": "مكة"},
    {"symbol": "4110.SR", "name": "جبل عمر"},
    {"symbol": "4120.SR", "name": "الإسكان"},
    {"symbol": "4130.SR", "name": "البناء والتعمير"},
    {"symbol": "4140.SR", "name": "المدينة المنورة"},
    {"symbol": "4150.SR", "name": "طيبة"},
    {"symbol": "4160.SR", "name": "السعودية للتطوير"},
    {"symbol": "4170.SR", "name": "أعيان"},
    {"symbol": "4180.SR", "name": "أملاك العقارية"},
    {"symbol": "4190.SR", "name": "الصواري"},
    # تأمين
    {"symbol": "8010.SR", "name": "الاتحاد الوطني"},
    {"symbol": "8012.SR", "name": "التعاونية"},
    {"symbol": "8020.SR", "name": "ميد غلف"},
    {"symbol": "8030.SR", "name": "الأهلية"},
    {"symbol": "8040.SR", "name": "سلامة"},
    {"symbol": "8050.SR", "name": "الدرع"},
    {"symbol": "8060.SR", "name": "بوبا العربية"},
    {"symbol": "8070.SR", "name": "وقاية"},
    {"symbol": "8080.SR", "name": "الخليجية"},
    {"symbol": "8100.SR", "name": "ولاء"},
    {"symbol": "8120.SR", "name": "الصقر"},
    {"symbol": "8150.SR", "name": "العالمية"},
    {"symbol": "8160.SR", "name": "الشركة العربية"},
    {"symbol": "8170.SR", "name": "جي آي جي"},
    {"symbol": "8180.SR", "name": "المتحدة للتأمين"},
    {"symbol": "8190.SR", "name": "أيس"},
    {"symbol": "8200.SR", "name": "تكافل الراجحي"},
    {"symbol": "8210.SR", "name": "إتقان"},
    {"symbol": "8230.SR", "name": "أمانة للتأمين"},
    {"symbol": "8240.SR", "name": "الإعادة"},
    {"symbol": "8250.SR", "name": "سايكو"},
    {"symbol": "8260.SR", "name": "سلامة للتكافل"},
    {"symbol": "8270.SR", "name": "السعودية الهندية"},
    {"symbol": "8280.SR", "name": "أليانز"},
    {"symbol": "8300.SR", "name": "المجموعة المتحدة"},
    # نقل ولوجستيات
    {"symbol": "4261.SR", "name": "ناقلات"},
    {"symbol": "4262.SR", "name": "البحري"},
    {"symbol": "4263.SR", "name": "الوطنية للطيران"},
    {"symbol": "4264.SR", "name": "سل"},
]

def send(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": msg,
            "parse_mode": "HTML"
        })
    except Exception as e:
        print(f"خطأ تيليجرام: {e}")

def get_data(symbol):
    try:
        df = yf.download(symbol, period="3mo", interval="1d",
                         auto_adjust=True, progress=False)
        if df.empty or len(df) < 50:
            return None

        close  = df["Close"].squeeze().astype(float)
        volume = df["Volume"].squeeze().astype(float)

        rsi   = ta.rsi(close, length=14)
        macd  = ta.macd(close)
        bb    = ta.bbands(close)
        ma20  = close.rolling(20).mean()
        ma50  = close.rolling(50).mean()
        vol10 = volume.rolling(10).mean()

        current_price = float(close.iloc[-1])
        prev_price    = float(close.iloc[-2])
        current_vol   = float(volume.iloc[-1])
        avg_vol       = float(vol10.iloc[-1])
        high52        = float(close.rolling(252).max().iloc[-1])

        return {
            "price":       round(current_price, 2),
            "change":      round((current_price - prev_price) / prev_price * 100, 2),
            "rsi":         round(float(rsi.iloc[-1]), 1),
            "macd":        round(float(macd["MACD_12_26_9"].iloc[-1]), 3),
            "macd_signal": round(float(macd["MACDs_12_26_9"].iloc[-1]), 3),
            "ma20":        round(float(ma20.iloc[-1]), 2),
            "ma50":        round(float(ma50.iloc[-1]), 2),
            "bb_up":       round(float(bb["BBU_5_2.0"].iloc[-1]), 2),
            "bb_low":      round(float(bb["BBL_5_2.0"].iloc[-1]), 2),
            "volume":      int(current_vol),
            "avg_volume":  int(avg_vol),
            "vol_ratio":   round(current_vol / avg_vol, 2),
            "high52":      round(high52, 2),
            "dist_high52": round((high52 - current_price) / high52 * 100, 2),
        }
    except Exception as e:
        print(f"خطأ في {symbol}: {e}")
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
    prompt = f"""أنت محلل مضاربي متخصص في سوق تداول السعودي.

السهم: {name}
السعر: {d['price']} ﷼  |  التغير: {d['change']}%
RSI: {d['rsi']}  |  MACD: {d['macd']} / Signal: {d['macd_signal']}
MA20: {d['ma20']}  |  MA50: {d['ma50']}
بولنجر: أعلى {d['bb_up']} / أدنى {d['bb_low']}
حجم التداول: {d['volume']:,} (نسبة للمتوسط: {d['vol_ratio']}x)
المسافة من أعلى 52 أسبوع: {d['dist_high52']}%

قواعد صارمة:
- وقف الخسارة لا يتجاوز 4% من سعر الدخول
- TP1: ربح 3-5% | TP2: ربح 7-10%
- نسبة المكافأة/المخاطرة لا تقل عن 2:1

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
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        text = resp.text.replace("```json","").replace("```","").strip()
        result = json.loads(text)
        if result.get("rr_ratio", 0) < 2:
            return None
        return result
    except Exception as e:
        print(f"خطأ AI {name}: {e}")
        return None

def run_scan():
    print("🔍 بدء المسح الشامل...")
    send(f"🔍 <b>بدء المسح الشامل للسوق السعودي</b>\n📊 عدد الأسهم: {len(STOCKS)}\n⏳ يستغرق 10-15 دقيقة...")

    buys     = []
    filtered = []
    errors   = []

    for i, stock in enumerate(STOCKS, 1):
        print(f"[{i}/{len(STOCKS)}] {stock['name']}")
        data = get_data(stock["symbol"])

        if not data:
            errors.append(stock["name"])
            continue

        passed, reasons = passes_filters(data)
        if not passed:
            filtered.append(stock["name"])
            continue

        sig = get_signal(stock["name"], data)
        if sig and "شراء" in sig.get("signal", ""):
            buys.append({**stock, **data, **sig})
            print(f"  ✅ فرصة! {sig['signal']} @ {sig['entry']}")

        time.sleep(1.5)

    # إرسال النتائج
    if buys:
        buys.sort(key=lambda x: (-x["confidence"], -x.get("rr_ratio", 0)))

        msg  = "🟢 <b>فرص المضاربة اليوم - تداول</b>\n"
        msg += f"📅 {time.strftime('%Y-%m-%d')} | ⏰ {time.strftime('%H:%M')}\n"
        msg += f"🔍 مسح {len(STOCKS)} سهم | ✅ فرص: {len(buys)}\n\n"

        for b in buys:
            sl_pct  = round((b['entry'] - b['sl'])   / b['entry'] * 100, 1)
            tp1_pct = round((b['tp1']  - b['entry'])  / b['entry'] * 100, 1)
            tp2_pct = round((b['tp2']  - b['entry'])  / b['entry'] * 100, 1)

            msg += f"━━━━━━━━━━━━━━━\n"
            msg += f"⚡ <b>{b['name']}</b> ({b['symbol']}) — {b['signal']}\n"
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
        msg += f"🔍 تم مسح {len(STOCKS)} سهم\n"
        msg += f"❌ مفلتر: {len(filtered)} | ⚠️ أخطاء: {len(errors)}"
        send(msg)

    print(f"✅ اكتمل | فرص: {len(buys)} | مفلتر: {len(filtered)} | أخطاء: {len(errors)}")

# كل يوم 6:15 UTC = 9:15 صباحاً بتوقيت الرياض
schedule.every().day.at("06:15").do(run_scan)

print(f"✅ النظام يعمل | {len(STOCKS)} سهم في قائمة المراقبة")
run_scan()

while True:
    schedule.run_pending()
    time.sleep(30)
