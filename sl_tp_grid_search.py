"""
Grid search 2 มิติ: SL (ATR multiplier) x TP (%) พร้อมกัน
เพื่อดูว่า "ช่องว่าง" ระหว่างจุดตัดขาดทุนกับจุดล็อกกำไรแบบไหนดีที่สุด
ไม่ใช่ตรึง SL ไว้คงที่แล้วปรับแค่ TP เหมือนรอบก่อน

รวม slippage 0.5% (ระดับสมจริงที่ยืนยันแล้วจากการทดสอบก่อนหน้า)

รัน: python sl_tp_grid_search.py
"""

from compare_strategies import START, END, load_data, signal_ma_crossover
from fee_impact_analysis import fee_rate_for
from delta_sl_optimization import compute_atr, FAST, SLOW, ATR_PERIOD
from take_profit_test import run_backtest_with_sl_tp

TICKER = "DELTA.BK"
SLIPPAGE_PCT = 0.5

SL_GRID = [1.0, 1.5, 2.0, 2.5, 3.0]        # ATR multiplier — ยิ่งน้อย ยิ่งแคบ (โดนง่าย)
TP_GRID = [30, 50, 75, 100, 125, 150, 200]  # % กำไรที่ล็อก — ยิ่งน้อย ยิ่งแคบ (ล็อกไว)


def approx_sl_pct(sl_mult: float, avg_range_pct: float) -> float:
    """ประมาณระยะ SL เป็น % คร่าวๆ จาก ATR multiplier x daily range เฉลี่ย"""
    return sl_mult * avg_range_pct


if __name__ == "__main__":
    fee_rate = fee_rate_for(TICKER)
    data = load_data(TICKER, START, END)
    signal = signal_ma_crossover(data, fast=FAST, slow=SLOW)
    atr = compute_atr(data, ATR_PERIOD)

    avg_range_pct = (atr / data["Close"] * 100).mean()  # ATR เฉลี่ยเป็น % ของราคา ตลอดช่วงข้อมูล

    results = []
    for sl_mult in SL_GRID:
        for tp_pct in TP_GRID:
            stats = run_backtest_with_sl_tp(data, signal, fee_rate, atr, sl_mult, tp_pct, SLIPPAGE_PCT)
            sl_pct_approx = approx_sl_pct(sl_mult, avg_range_pct)
            gap_ratio = tp_pct / sl_pct_approx  # risk:reward ratio โดยประมาณ
            results.append({"sl_mult": sl_mult, "tp_pct": tp_pct, "sl_pct_approx": sl_pct_approx, "gap_ratio": gap_ratio, **stats})

    results.sort(key=lambda x: x["net_return_pct"], reverse=True)

    print(f"\n{'='*115}")
    print(f"SL x TP Grid Search — DELTA.BK, slippage {SLIPPAGE_PCT}% (เรียงจากผลตอบแทนสูงสุด, Top 15)")
    print(f"ATR เฉลี่ย ≈ {avg_range_pct:.2f}% ของราคา")
    print(f"{'='*115}")
    header = f"{'SL(ATR x)':>10}{'SL≈%':>8}{'TP%':>8}{'Gap(TP/SL)':>12}{'Net Return':>13}{'เทรด':>7}{'โดนSL':>7}{'โดนTP':>7}"
    print(header)
    print("-" * 115)
    for r in results[:15]:
        print(
            f"{r['sl_mult']:>9.1f}x"
            f"{r['sl_pct_approx']:>7.1f}%"
            f"{r['tp_pct']:>7d}%"
            f"{r['gap_ratio']:>11.1f}x"
            f"{r['net_return_pct']:>+12.2f}%"
            f"{r['num_round_trips']:>7d}"
            f"{r['num_sl_hits']:>7d}"
            f"{r['num_tp_hits']:>7d}"
        )

    print(f"\n{'-'*115}")
    print("Bottom 5 (แย่ที่สุด) — เผื่อดูว่า gap แคบไปจริงไหม")
    print("-" * 115)
    for r in results[-5:]:
        print(
            f"{r['sl_mult']:>9.1f}x"
            f"{r['sl_pct_approx']:>7.1f}%"
            f"{r['tp_pct']:>7d}%"
            f"{r['gap_ratio']:>11.1f}x"
            f"{r['net_return_pct']:>+12.2f}%"
            f"{r['num_round_trips']:>7d}"
            f"{r['num_sl_hits']:>7d}"
            f"{r['num_tp_hits']:>7d}"
        )
    print(f"{'='*115}")
