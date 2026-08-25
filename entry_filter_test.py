"""
ทดสอบวิธี "กรองจุดเข้า" หลายแบบ บนพื้นฐาน MA(5/15) เดิม + SL/TP ที่เลือกไว้แล้ว (ATR 3.0x / TP 100%)

แนวคิด: MA ตัดขึ้น = เข้าสู่ "โซนขาขึ้น" แต่ไม่จำเป็นต้องเข้าซื้อทันทีวันแรกที่ตัดขึ้น
ลองรอ confirm เพิ่มก่อนค่อยเข้าจริง ภายในโซนขาขึ้นเดียวกัน (ออกจากตำแหน่งเมื่อ MA ตัดลงเหมือนเดิม)

วิธีที่ทดสอบ:
1. Baseline    — เข้าทันทีวันที่ MA ตัดขึ้น (แบบเดิมที่ใช้มาตลอด)
2. Volume      — รอวันที่ volume > 1.2 เท่าของค่าเฉลี่ย 20 วัน ถึงเข้า (ยืนยันว่ามีแรงซื้อจริง)
3. RSI         — รอวันที่ RSI(14) > 50 ถึงเข้า (ยืนยันโมเมนตัมเป็นบวกจริง ไม่ใช่แค่ MA ขยับ)
4. Breakout    — รอวันที่ราคาปิดทำ high ใหม่ในรอบ 10 วัน ถึงเข้า (ยืนยันว่าราคาไปต่อจริง)

รัน: python entry_filter_test.py
"""

from compare_strategies import START, END, load_data, signal_ma_crossover
from fee_impact_analysis import fee_rate_for
from delta_sl_optimization import compute_atr, FAST, SLOW, ATR_PERIOD
from take_profit_test import run_backtest_with_sl_tp, SL_ATR_MULTIPLIER

TICKER = "DELTA.BK"
TP_PCT = 100
SLIPPAGE_PCT = 0.5
VOLUME_LOOKBACK = 20
VOLUME_THRESHOLD = 1.2
RSI_PERIOD = 14
RSI_THRESHOLD = 50
BREAKOUT_LOOKBACK = 10


def compute_rsi(close, period):
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    return 100 - (100 / (1 + gain / loss))


def apply_entry_filter(base_bullish, confirm_ok):
    """
    base_bullish: True ตลอดช่วงที่ MA เป็นขาขึ้น (จาก signal_ma_crossover)
    confirm_ok:   True ในวันที่เงื่อนไขกรองผ่าน
    คืนค่า in_position ใหม่ที่ 'เข้าช้ากว่าเดิม' รอจนกว่า confirm_ok เป็นจริงครั้งแรกในแต่ละรอบขาขึ้น
    ออกจากตำแหน่งพร้อมกับ base_bullish เหมือนเดิม (จบรอบเมื่อ MA ตัดลง)
    """
    result = base_bullish.copy()
    in_confirmed_entry = False
    prev_bullish = False

    for date in base_bullish.index:
        bullish = bool(base_bullish.loc[date])

        if bullish and not prev_bullish:
            in_confirmed_entry = False  # เริ่มรอบขาขึ้นใหม่ ต้อง confirm ใหม่

        if bullish and not in_confirmed_entry:
            if bool(confirm_ok.loc[date]):
                in_confirmed_entry = True
            result.loc[date] = in_confirmed_entry
        else:
            result.loc[date] = bullish and in_confirmed_entry

        prev_bullish = bullish

    return result


if __name__ == "__main__":
    fee_rate = fee_rate_for(TICKER)
    data = load_data(TICKER, START, END)
    base_bullish = signal_ma_crossover(data, fast=FAST, slow=SLOW)
    atr = compute_atr(data, ATR_PERIOD)

    avg_volume = data["Volume"].rolling(VOLUME_LOOKBACK).mean()
    volume_confirm = data["Volume"] > avg_volume * VOLUME_THRESHOLD

    rsi = compute_rsi(data["Close"], RSI_PERIOD)
    rsi_confirm = rsi > RSI_THRESHOLD

    rolling_high = data["Close"].rolling(BREAKOUT_LOOKBACK).max()
    breakout_confirm = data["Close"] >= rolling_high

    variants = {
        "Baseline (เข้าทันที)": base_bullish,
        "Volume confirm": apply_entry_filter(base_bullish, volume_confirm.fillna(False)),
        "RSI > 50 confirm": apply_entry_filter(base_bullish, rsi_confirm.fillna(False)),
        "Breakout 10d confirm": apply_entry_filter(base_bullish, breakout_confirm.fillna(False)),
    }

    print(f"\n{'='*100}")
    print(f"Entry Filter Comparison — DELTA.BK, SL {SL_ATR_MULTIPLIER}x ATR / TP {TP_PCT}%, slippage {SLIPPAGE_PCT}%")
    print(f"{'='*100}")
    header = f"{'วิธีเข้า':<24}{'Net Return':>13}{'เทรดทั้งหมด':>13}{'โดนSL':>7}{'โดนTP':>7}{'ถือเฉลี่ย(วัน)':>15}"
    print(header)
    print("-" * 100)

    results = []
    for label, in_position in variants.items():
        stats = run_backtest_with_sl_tp(data, in_position, fee_rate, atr, SL_ATR_MULTIPLIER, TP_PCT, SLIPPAGE_PCT)
        results.append({"label": label, **stats})
        print(
            f"{label:<24}"
            f"{stats['net_return_pct']:>+12.2f}%"
            f"{stats['num_round_trips']:>13d}"
            f"{stats['num_sl_hits']:>7d}"
            f"{stats['num_tp_hits']:>7d}"
            f"{stats['avg_holding_days']:>14.1f} "
        )
    print(f"{'='*100}")
