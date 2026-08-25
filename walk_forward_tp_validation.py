"""
Walk-forward validation สำหรับ combo SL (ATR-based 2.0x) + TP
หา TP ที่ดีที่สุดจาก TRAIN เท่านั้น แล้วเอาไปทดสอบกับ TEST ที่ไม่เคยเห็น
ทำที่ slippage 0.5% และ 1.0% ตามที่ทดสอบไว้ก่อนหน้า

รัน: python walk_forward_tp_validation.py
"""

from compare_strategies import load_data, signal_ma_crossover
from fee_impact_analysis import fee_rate_for
from delta_sl_optimization import compute_atr, FAST, SLOW, ATR_PERIOD
from take_profit_test import run_backtest_with_sl_tp, TP_LEVELS_PCT, SL_ATR_MULTIPLIER

TICKER = "DELTA.BK"
BUFFER_START = "2019-09-01"
TRAIN_START, TRAIN_END = "2020-01-01", "2023-12-31"
TEST_START, TEST_END = "2024-01-01", "2026-08-01"
SLIPPAGE_LEVELS_PCT = [0.5, 1.0]


if __name__ == "__main__":
    fee_rate = fee_rate_for(TICKER)

    data_full = load_data(TICKER, BUFFER_START, TEST_END)
    signal_full = signal_ma_crossover(data_full, fast=FAST, slow=SLOW)
    atr_full = compute_atr(data_full, ATR_PERIOD)

    train_mask = (data_full.index >= TRAIN_START) & (data_full.index <= TRAIN_END)
    test_mask = (data_full.index >= TEST_START) & (data_full.index <= TEST_END)

    data_train, signal_train, atr_train = data_full[train_mask], signal_full[train_mask], atr_full[train_mask]
    data_test, signal_test, atr_test = data_full[test_mask], signal_full[test_mask], atr_full[test_mask]

    for slippage in SLIPPAGE_LEVELS_PCT:
        print(f"\n{'='*100}")
        print(f"Slippage {slippage}%")
        print(f"{'='*100}")

        # หา TP ที่ดีที่สุดจาก TRAIN เท่านั้น
        train_results = []
        for tp_pct in TP_LEVELS_PCT:
            stats = run_backtest_with_sl_tp(data_train, signal_train, fee_rate, atr_train, SL_ATR_MULTIPLIER, tp_pct, slippage)
            train_results.append({"tp_pct": tp_pct, **stats})
        train_results.sort(key=lambda x: x["net_return_pct"], reverse=True)
        best_from_train = train_results[0]

        print(f"TRAIN — Top 3 TP:")
        for r in train_results[:3]:
            tp_label = f"{r['tp_pct']}%" if r["tp_pct"] is not None else "ไม่มี"
            print(f"  TP {tp_label:<8} Net Return: {r['net_return_pct']:>+10.2f}%")

        # เอา TP ที่ชนะใน TRAIN ไปรันกับ TEST
        test_result = run_backtest_with_sl_tp(
            data_test, signal_test, fee_rate, atr_test, SL_ATR_MULTIPLIER, best_from_train["tp_pct"], slippage
        )

        # เทียบ: ถ้าโกงหา best จาก TEST เองเลย
        test_results_all = []
        for tp_pct in TP_LEVELS_PCT:
            stats = run_backtest_with_sl_tp(data_test, signal_test, fee_rate, atr_test, SL_ATR_MULTIPLIER, tp_pct, slippage)
            test_results_all.append({"tp_pct": tp_pct, **stats})
        test_results_all.sort(key=lambda x: x["net_return_pct"], reverse=True)
        best_if_cheated = test_results_all[0]

        best_tp_label = f"{best_from_train['tp_pct']}%" if best_from_train["tp_pct"] is not None else "ไม่มี"
        cheat_tp_label = f"{best_if_cheated['tp_pct']}%" if best_if_cheated["tp_pct"] is not None else "ไม่มี"

        print(f"\nTP ที่ชนะใน TRAIN: {best_tp_label}")
        print(f"  Net Return ใน TRAIN:  {best_from_train['net_return_pct']:>+10.2f}%")
        print(f"  Net Return ใน TEST:   {test_result['net_return_pct']:>+10.2f}%   (เอา TP เดียวกันมารันกับข้อมูลใหม่)")
        print(f"\nถ้า 'โกง' หา TP ที่ดีที่สุดจาก TEST เอง: TP {cheat_tp_label} -> {best_if_cheated['net_return_pct']:>+10.2f}%")

        gap = best_if_cheated["net_return_pct"] - test_result["net_return_pct"]
        match = "✅ TP เดียวกัน (ไม่ overfit)" if best_from_train["tp_pct"] == best_if_cheated["tp_pct"] else "⚠️ TP ต่างกัน (มีสัญญาณ overfit)"
        print(f"ส่วนต่าง: {gap:+.2f} percentage points   {match}")
