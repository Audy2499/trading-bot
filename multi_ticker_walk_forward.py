"""
Walk-forward validation (SL x TP grid) กับหลายหุ้นพร้อมกัน
หา config ที่ดีที่สุดจาก TRAIN เท่านั้น แล้วเอาไปทดสอบกับ TEST ที่ไม่เคยเห็น

Train: 2020-01-01 - 2023-12-31
Test:  2024-01-01 - 2026-08-01

รัน: python multi_ticker_walk_forward.py
"""

from compare_strategies import load_data, signal_ma_crossover
from fee_impact_analysis import fee_rate_for
from delta_sl_optimization import compute_atr, FAST, SLOW, ATR_PERIOD
from take_profit_test import run_backtest_with_sl_tp

CANDIDATES = ["PLTR", "AFRM", "TRUE.BK", "GULF.BK"]

BUFFER_START = "2019-09-01"
TRAIN_START, TRAIN_END = "2020-01-01", "2023-12-31"
TEST_START, TEST_END = "2024-01-01", "2026-08-01"

SLIPPAGE_PCT = 0.5
SL_GRID = [1.0, 1.5, 2.0, 2.5, 3.0]
TP_GRID = [30, 50, 75, 100, 125, 150, 200]
MIN_TRADES_TRAIN = 5  # เกณฑ์ต่ำกว่าตอน full-period เพราะ train สั้นกว่า


def grid_search(data, signal, atr, fee_rate, min_trades) -> list[dict]:
    results = []
    for sl_mult in SL_GRID:
        for tp_pct in TP_GRID:
            stats = run_backtest_with_sl_tp(data, signal, fee_rate, atr, sl_mult, tp_pct, SLIPPAGE_PCT)
            if stats["num_round_trips"] < min_trades:
                continue
            results.append({"sl_mult": sl_mult, "tp_pct": tp_pct, **stats})
    results.sort(key=lambda x: x["net_return_pct"], reverse=True)
    return results


def validate_ticker(ticker: str) -> dict:
    fee_rate = fee_rate_for(ticker)
    data_full = load_data(ticker, BUFFER_START, TEST_END)

    if len(data_full) < 500:
        return {"ticker": ticker, "skipped": f"ข้อมูลรวมแค่ {len(data_full)} วัน ไม่พอแบ่ง train/test"}

    signal_full = signal_ma_crossover(data_full, fast=FAST, slow=SLOW)
    atr_full = compute_atr(data_full, ATR_PERIOD)

    train_mask = (data_full.index >= TRAIN_START) & (data_full.index <= TRAIN_END)
    test_mask = (data_full.index >= TEST_START) & (data_full.index <= TEST_END)

    data_train, signal_train, atr_train = data_full[train_mask], signal_full[train_mask], atr_full[train_mask]
    data_test, signal_test, atr_test = data_full[test_mask], signal_full[test_mask], atr_full[test_mask]

    train_results = grid_search(data_train, signal_train, atr_train, fee_rate, MIN_TRADES_TRAIN)
    if not train_results:
        return {"ticker": ticker, "skipped": "ไม่มี combo ไหนเทรดครบเกณฑ์ขั้นต่ำใน TRAIN"}

    best_train = train_results[0]

    test_result = run_backtest_with_sl_tp(
        data_test, signal_test, fee_rate, atr_test, best_train["sl_mult"], best_train["tp_pct"], SLIPPAGE_PCT
    )

    test_results_all = grid_search(data_test, signal_test, atr_test, fee_rate, min_trades=3)
    best_if_cheated = test_results_all[0] if test_results_all else None

    return {
        "ticker": ticker,
        "train_sl": best_train["sl_mult"],
        "train_tp": best_train["tp_pct"],
        "train_return": best_train["net_return_pct"],
        "test_return_using_train_config": test_result["net_return_pct"],
        "test_trades": test_result["num_round_trips"],
        "cheated_best_return": best_if_cheated["net_return_pct"] if best_if_cheated else None,
        "cheated_sl": best_if_cheated["sl_mult"] if best_if_cheated else None,
        "cheated_tp": best_if_cheated["tp_pct"] if best_if_cheated else None,
    }


def print_report(results: list[dict]) -> None:
    print(f"\n{'='*120}")
    print(f"Multi-ticker Walk-forward Validation (SL x TP grid, slippage {SLIPPAGE_PCT}%)")
    print(f"{'='*120}")
    for r in results:
        if "skipped" in r:
            print(f"\n{r['ticker']}: ข้าม — {r['skipped']}")
            continue

        print(f"\n{r['ticker']}")
        print(f"  Config ที่ชนะใน TRAIN:  SL {r['train_sl']}x ATR, TP {r['train_tp']}%  -> Net Return TRAIN: {r['train_return']:+.2f}%")
        print(f"  ผลใน TEST (config เดียวกัน):  {r['test_return_using_train_config']:+.2f}%  ({r['test_trades']} เทรด)")
        if r["cheated_best_return"] is not None:
            match = "✅ ตรงกัน" if (r["cheated_sl"] == r["train_sl"] and r["cheated_tp"] == r["train_tp"]) else "⚠️ ต่างกัน"
            print(f"  ถ้าโกงหา best จาก TEST เอง:  SL {r['cheated_sl']}x, TP {r['cheated_tp']}%  -> {r['cheated_best_return']:+.2f}%  ({match})")
    print(f"\n{'='*120}")


if __name__ == "__main__":
    results = [validate_ticker(t) for t in CANDIDATES]
    print_report(results)
