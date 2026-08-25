"""
Walk-forward validation สำหรับ DELTA.BK MA(5/15) + SL:
แบ่งข้อมูลเป็น 2 ช่วง หา parameter ที่ดีที่สุดจากช่วง Train เท่านั้น
แล้วเอาไปทดสอบกับช่วง Test ที่ไม่เคยเห็นมาก่อน เพื่อเช็คว่า overfit หรือไม่

Train: 2020-01-01 - 2023-12-31 (4 ปี)
Test:  2024-01-01 - 2026-08-01 (~2.5 ปี, ไม่เคยใช้ตอนหา parameter เลย)

รัน: python walk_forward_validation.py
"""

from compare_strategies import INITIAL_CAPITAL, load_data, signal_ma_crossover
from fee_impact_analysis import fee_rate_for
from delta_sl_optimization import compute_atr, run_backtest, FIXED_SL_GRID, ATR_MULTIPLIER_GRID, ATR_PERIOD, FAST, SLOW

TICKER = "DELTA.BK"
BUFFER_START = "2019-09-01"  # โหลดข้อมูลเผื่อ warmup ก่อน train เริ่ม
TRAIN_START, TRAIN_END = "2020-01-01", "2023-12-31"
TEST_START, TEST_END = "2024-01-01", "2026-08-01"


def build_candidates() -> list[dict]:
    candidates = [{"label": "ไม่มี SL", "sl_mode": "none", "sl_param": None}]
    for pct in FIXED_SL_GRID:
        candidates.append({"label": f"Fixed SL {pct}%", "sl_mode": "fixed", "sl_param": pct})
    for mult in ATR_MULTIPLIER_GRID:
        candidates.append({"label": f"ATR-based {mult}x", "sl_mode": "atr", "sl_param": mult})
    return candidates


def evaluate(data_slice, signal_slice, atr_slice, fee_rate, candidate) -> dict:
    stats = run_backtest(
        data_slice, signal_slice, fee_rate,
        sl_mode=candidate["sl_mode"], sl_param=candidate["sl_param"], atr=atr_slice,
    )
    return {**candidate, **stats}


if __name__ == "__main__":
    fee_rate = fee_rate_for(TICKER)

    # โหลดข้อมูลรวดเดียวตั้งแต่ buffer จนจบ test เพื่อให้ indicator มี warmup ถูกต้อง
    data_full = load_data(TICKER, BUFFER_START, TEST_END)
    signal_full = signal_ma_crossover(data_full, fast=FAST, slow=SLOW)
    atr_full = compute_atr(data_full, ATR_PERIOD)

    train_mask = (data_full.index >= TRAIN_START) & (data_full.index <= TRAIN_END)
    test_mask = (data_full.index >= TEST_START) & (data_full.index <= TEST_END)

    data_train, signal_train, atr_train = data_full[train_mask], signal_full[train_mask], atr_full[train_mask]
    data_test, signal_test, atr_test = data_full[test_mask], signal_full[test_mask], atr_full[test_mask]

    candidates = build_candidates()

    # ---- Step 1: หา parameter ที่ดีที่สุดจาก TRAIN เท่านั้น ----
    train_results = [evaluate(data_train, signal_train, atr_train, fee_rate, c) for c in candidates]
    train_results.sort(key=lambda x: x["net_return_pct"], reverse=True)
    best_from_train = train_results[0]

    # ---- Step 2: เอา parameter ที่ชนะใน TRAIN ไปรันกับ TEST (ไม่เคยเห็นมาก่อน) ----
    test_result_using_train_best = evaluate(data_test, signal_test, atr_test, fee_rate, best_from_train)

    # ---- สำหรับเทียบ: ถ้า "โกง" หา best จาก TEST เองเลยจะได้เท่าไหร่ ----
    test_results_all = [evaluate(data_test, signal_test, atr_test, fee_rate, c) for c in candidates]
    test_results_all.sort(key=lambda x: x["net_return_pct"], reverse=True)
    best_if_cheated = test_results_all[0]

    print(f"\n{'='*100}")
    print(f"TRAIN period ({TRAIN_START} ถึง {TRAIN_END}) — Top 5 parameter ที่ดีที่สุด")
    print(f"{'='*100}")
    for r in train_results[:5]:
        print(f"  {r['label']:<20} Net Return: {r['net_return_pct']:>+10.2f}%   เทรด/ปี: {r['trades_per_year']:.1f}")

    print(f"\n{'='*100}")
    print(f"ผลจากการเอา parameter ที่ดีที่สุดใน TRAIN ('{best_from_train['label']}') ไปรันกับ TEST period ที่ไม่เคยเห็น")
    print(f"({TEST_START} ถึง {TEST_END})")
    print(f"{'='*100}")
    print(f"  Net Return ใน TRAIN (ตอนหา param):  {best_from_train['net_return_pct']:>+10.2f}%")
    print(f"  Net Return ใน TEST (ของจริง):        {test_result_using_train_best['net_return_pct']:>+10.2f}%")
    print(f"  จำนวนเทรดใน TEST:                    {test_result_using_train_best['trades_per_year']:.1f} เทรด/ปี")

    print(f"\n{'='*100}")
    print(f"เทียบ: ถ้า 'โกง' หา best parameter จาก TEST เองเลย (ไม่ควรทำจริง แค่ไว้เทียบ)")
    print(f"{'='*100}")
    print(f"  Parameter ที่ดีที่สุดใน TEST (ถ้ารู้ล่วงหน้า): {best_if_cheated['label']:<20} Net Return: {best_if_cheated['net_return_pct']:>+10.2f}%")

    gap = best_if_cheated["net_return_pct"] - test_result_using_train_best["net_return_pct"]
    print(f"\n  ส่วนต่างระหว่าง 'รู้ล่วงหน้า' กับ 'ใช้ param จาก TRAIN จริง': {gap:+.2f} percentage points")
    print(f"{'='*100}")
