"""
Walk-forward validation สำหรับ RSI > 50 entry filter เทียบกับ Baseline (เข้าทันทีที่ MA ตัดขึ้น)
บน DELTA.BK, SL 3.0x ATR / TP 100% (config เดิมที่ยืนยันแล้ว)

Train: 2020-01-01 - 2023-12-31
Test:  2024-01-01 - 2026-08-01

รัน: python walk_forward_entry_validation.py
"""

from compare_strategies import load_data, signal_ma_crossover
from fee_impact_analysis import fee_rate_for
from delta_sl_optimization import compute_atr, FAST, SLOW, ATR_PERIOD
from take_profit_test import run_backtest_with_sl_tp, SL_ATR_MULTIPLIER, TP_LEVELS_PCT
from entry_filter_test import compute_rsi, apply_entry_filter, RSI_PERIOD, RSI_THRESHOLD, SLIPPAGE_PCT

TICKER = "DELTA.BK"
TP_PCT = 100
BUFFER_START = "2019-09-01"
TRAIN_START, TRAIN_END = "2020-01-01", "2023-12-31"
TEST_START, TEST_END = "2024-01-01", "2026-08-01"


def evaluate(data_slice, in_position_slice, atr_slice, fee_rate) -> dict:
    return run_backtest_with_sl_tp(data_slice, in_position_slice, fee_rate, atr_slice, SL_ATR_MULTIPLIER, TP_PCT, SLIPPAGE_PCT)


if __name__ == "__main__":
    fee_rate = fee_rate_for(TICKER)
    data_full = load_data(TICKER, BUFFER_START, TEST_END)

    base_bullish_full = signal_ma_crossover(data_full, fast=FAST, slow=SLOW)
    atr_full = compute_atr(data_full, ATR_PERIOD)
    rsi_full = compute_rsi(data_full["Close"], RSI_PERIOD)
    rsi_confirm_full = (rsi_full > RSI_THRESHOLD).fillna(False)
    rsi_entry_full = apply_entry_filter(base_bullish_full, rsi_confirm_full)

    train_mask = (data_full.index >= TRAIN_START) & (data_full.index <= TRAIN_END)
    test_mask = (data_full.index >= TEST_START) & (data_full.index <= TEST_END)

    print(f"\n{'='*100}")
    print(f"Walk-forward: RSI > {RSI_THRESHOLD} Entry Filter vs Baseline — {TICKER}")
    print(f"{'='*100}")

    for period_name, mask in [("TRAIN (2020-2023)", train_mask), ("TEST (2024-2026, ไม่เคยเห็นตอนหา idea)", test_mask)]:
        data_s = data_full[mask]
        atr_s = atr_full[mask]
        baseline_s = base_bullish_full[mask]
        rsi_entry_s = rsi_entry_full[mask]

        baseline_result = evaluate(data_s, baseline_s, atr_s, fee_rate)
        rsi_result = evaluate(data_s, rsi_entry_s, atr_s, fee_rate)

        print(f"\n{period_name}")
        print(f"  Baseline (เข้าทันที):   {baseline_result['net_return_pct']:>+10.2f}%   ({baseline_result['num_round_trips']} เทรด)")
        print(f"  RSI > {RSI_THRESHOLD} confirm:      {rsi_result['net_return_pct']:>+10.2f}%   ({rsi_result['num_round_trips']} เทรด)")
        diff = rsi_result["net_return_pct"] - baseline_result["net_return_pct"]
        verdict = "RSI filter ดีกว่า" if diff > 0 else "Baseline ดีกว่า"
        print(f"  ส่วนต่าง: {diff:+.2f} percentage points  ({verdict})")

    print(f"\n{'='*100}")
