"""
รัน SL x TP grid search (เหมือน sl_tp_grid_search.py) กับหุ้นหลายตัวพร้อมกัน
เพื่อหา config ที่ดีที่สุดของแต่ละตัว ไม่ใช่แค่ DELTA.BK

รัน: python multi_ticker_sl_tp_search.py
"""

from compare_strategies import START, END, load_data, signal_ma_crossover
from fee_impact_analysis import fee_rate_for
from delta_sl_optimization import compute_atr, FAST, SLOW, ATR_PERIOD
from take_profit_test import run_backtest_with_sl_tp

CANDIDATES = ["PLTR", "AFRM", "TRUE.BK", "GULF.BK", "DELTA.BK"]

SLIPPAGE_PCT = 0.5
SL_GRID = [1.0, 1.5, 2.0, 2.5, 3.0]
TP_GRID = [30, 50, 75, 100, 125, 150, 200]

MIN_TRADES = 8  # เกณฑ์ขั้นต่ำให้เชื่อสถิติได้


def search_best(ticker: str) -> dict | None:
    fee_rate = fee_rate_for(ticker)
    data = load_data(ticker, START, END)
    if len(data) < 250:
        return {"ticker": ticker, "skipped": f"ข้อมูลแค่ {len(data)} วัน ไม่พอ"}

    signal = signal_ma_crossover(data, fast=FAST, slow=SLOW)
    atr = compute_atr(data, ATR_PERIOD)

    best = None
    for sl_mult in SL_GRID:
        for tp_pct in TP_GRID:
            stats = run_backtest_with_sl_tp(data, signal, fee_rate, atr, sl_mult, tp_pct, SLIPPAGE_PCT)
            if stats["num_round_trips"] < MIN_TRADES:
                continue
            candidate = {"ticker": ticker, "sl_mult": sl_mult, "tp_pct": tp_pct, **stats}
            if best is None or candidate["net_return_pct"] > best["net_return_pct"]:
                best = candidate

    return best if best is not None else {"ticker": ticker, "skipped": "ไม่มี combo ไหนเทรดครบเกณฑ์ขั้นต่ำ"}


def print_report(results: list[dict]) -> None:
    valid = [r for r in results if "skipped" not in r]
    skipped = [r for r in results if "skipped" in r]

    valid.sort(key=lambda x: x["net_return_pct"], reverse=True)

    print(f"\n{'='*110}")
    print(f"Config ที่ดีที่สุดต่อหุ้น (slippage {SLIPPAGE_PCT}%, MA{FAST}/{SLOW})")
    print(f"{'='*110}")
    header = f"{'Ticker':<10}{'SL(ATR)':>9}{'TP':>6}{'Net Return':>13}{'เทรด':>7}{'โดนSL':>7}{'โดนTP':>7}"
    print(header)
    print("-" * 110)
    for r in valid:
        print(
            f"{r['ticker']:<10}{r['sl_mult']:>8.1f}x{r['tp_pct']:>5d}%"
            f"{r['net_return_pct']:>+12.2f}%"
            f"{r['num_round_trips']:>7d}"
            f"{r['num_sl_hits']:>7d}"
            f"{r['num_tp_hits']:>7d}"
        )

    if skipped:
        print(f"\nข้าม:")
        for r in skipped:
            print(f"  {r['ticker']}: {r['skipped']}")
    print(f"{'='*110}")


if __name__ == "__main__":
    print(f"กำลังทดสอบ: {', '.join(CANDIDATES)}")
    results = [search_best(t) for t in CANDIDATES]
    print_report(results)
