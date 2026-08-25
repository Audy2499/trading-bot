"""
รายงานสัญญาณรายวัน สำหรับกดซื้อขายเองในแอป Webull (ระหว่างรอ API อนุมัติ)

ไม่ยิงคำสั่งอะไรเลย แค่บอกว่า:
- วันนี้มีสัญญาณเข้าใหม่ไหม (MA ตัดขึ้นวันนี้/เร็วๆ นี้)
- ถ้าเข้า ควรตั้ง SL ที่เท่าไหร่ (ตาม ATR ของแต่ละหุ้น) และ TP ที่เท่าไหร่
- ถ้าถืออยู่แล้ว ยัง "ในเทรนด์ขาขึ้น" อยู่ไหม หรือควรขายแล้ว (MA ตัดลง)

รัน: python daily_signal_report.py
"""

from datetime import datetime, timedelta

from compare_strategies import load_data, signal_ma_crossover
from delta_sl_optimization import compute_atr, FAST, SLOW, ATR_PERIOD
from ticker_strategy_config import get_config
from watchlist import WATCHLIST

LOOKBACK_DAYS = 150  # พอสำหรับ MA15 + ATR14 warmup


def analyze_ticker(ticker: str) -> dict | None:
    end = datetime.today().strftime("%Y-%m-%d")
    start = (datetime.today() - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    data = load_data(ticker, start, end)

    if len(data) < SLOW + 5:
        return {"ticker": ticker, "skipped": f"ข้อมูลแค่ {len(data)} วัน ไม่พอคำนวณ"}

    signal = signal_ma_crossover(data, fast=FAST, slow=SLOW)
    atr = compute_atr(data, ATR_PERIOD)
    config = get_config(ticker)

    today_bullish = bool(signal.iloc[-1])
    yesterday_bullish = bool(signal.iloc[-2])
    current_price = data["Close"].iloc[-1]
    current_atr = atr.iloc[-1]

    if today_bullish and not yesterday_bullish:
        action = "🟢 สัญญาณเข้าใหม่วันนี้"
    elif today_bullish and yesterday_bullish:
        action = "🔵 อยู่ในเทรนด์ขาขึ้น (ถืออยู่ได้)"
    elif not today_bullish and yesterday_bullish:
        action = "🔴 สัญญาณออกวันนี้ (MA ตัดลง)"
    else:
        action = "⚪ ไม่มีตำแหน่ง (เทรนด์ขาลง)"

    sl_price = current_price - config["sl_atr_mult"] * current_atr
    tp_price = current_price * (1 + config["tp_pct"] / 100)

    return {
        "ticker": ticker,
        "action": action,
        "current_price": current_price,
        "sl_price": sl_price,
        "tp_price": tp_price,
        "sl_config": f"{config['sl_atr_mult']}x ATR",
        "tp_config": f"{config['tp_pct']}%",
        "validated": config["validated"],
    }


def print_report(results: list[dict]) -> None:
    print(f"\n{'='*100}")
    print(f"รายงานสัญญาณรายวัน — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"(ใช้ประกอบการตัดสินใจ ไม่ใช่คำสั่งอัตโนมัติ — พี่กดซื้อขายเองในแอป Webull)")
    print(f"{'='*100}")

    for r in results:
        if "skipped" in r:
            print(f"\n{r['ticker']}: ข้าม — {r['skipped']}")
            continue

        status = "" if r["validated"] else "  ⚠️ (config ยังไม่ validate)"
        print(f"\n{r['ticker']}{status}")
        print(f"  {r['action']}")
        print(f"  ราคาปัจจุบัน:  {r['current_price']:.2f}")
        if "🟢" in r["action"] or "🔵" in r["action"]:
            print(f"  ตั้ง SL ที่:    {r['sl_price']:.2f}   ({r['sl_config']} ต่ำกว่าราคาปัจจุบัน)")
            print(f"  ตั้ง TP ที่:    {r['tp_price']:.2f}   (+{r['tp_config']})")

    print(f"\n{'='*100}")
    print("หมายเหตุ: SL/TP คำนวณจากราคาปัจจุบัน ถ้าเป็นไม้ที่ถืออยู่แล้วจากราคาเข้าจริงก่อนหน้า")
    print("ให้คำนวณ SL/TP จากราคาที่ซื้อจริงของพี่แทน ไม่ใช่ราคาวันนี้")
    print(f"{'='*100}")


if __name__ == "__main__":
    results = [analyze_ticker(t) for t in WATCHLIST]
    print_report(results)
