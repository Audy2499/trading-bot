"""
รัน backtest ทั้ง watchlist โดยแต่ละตัวใช้ SL/TP ของตัวเอง (จาก ticker_strategy_config.py)
แทนที่จะใช้ค่าเดียวกันทั้งหมด — entry ใช้ MA(5/15) baseline (ไม่มี RSI filter แล้ว)

รัน: python run_watchlist_backtest.py
"""

from compare_strategies import START, END, load_data, signal_ma_crossover
from fee_impact_analysis import fee_rate_for
from delta_sl_optimization import compute_atr, FAST, SLOW, ATR_PERIOD
from take_profit_test import run_backtest_with_sl_tp
from ticker_strategy_config import get_config
from watchlist import WATCHLIST

SLIPPAGE_PCT = 0.5


def run_for_ticker(ticker: str) -> dict | None:
    config = get_config(ticker)
    fee_rate = fee_rate_for(ticker)
    data = load_data(ticker, START, END)

    if len(data) < SLOW + 20:
        return {"ticker": ticker, "skipped": f"ข้อมูลแค่ {len(data)} วัน ไม่พอ"}

    signal = signal_ma_crossover(data, fast=FAST, slow=SLOW)
    atr = compute_atr(data, ATR_PERIOD)

    stats = run_backtest_with_sl_tp(data, signal, fee_rate, atr, config["sl_atr_mult"], config["tp_pct"], SLIPPAGE_PCT)
    return {"ticker": ticker, "config": config, **stats}


def print_report(results: list[dict]) -> None:
    print(f"\n{'='*110}")
    print(f"Watchlist Backtest — ใช้ config เฉพาะตัว (slippage {SLIPPAGE_PCT}%)")
    print(f"{'='*110}")
    header = f"{'Ticker':<10}{'SL/TP':<14}{'สถานะ':<10}{'Net Return':>13}{'เทรด':>7}{'โดนSL':>7}{'โดนTP':>7}"
    print(header)
    print("-" * 110)
    for r in results:
        if "skipped" in r:
            print(f"{r['ticker']:<10}ข้าม — {r['skipped']}")
            continue
        c = r["config"]
        sl_tp_label = f"{c['sl_atr_mult']}x/{c['tp_pct']}%"
        status = "validated" if c["validated"] else "default"
        print(
            f"{r['ticker']:<10}{sl_tp_label:<14}{status:<10}"
            f"{r['net_return_pct']:>+12.2f}%"
            f"{r['num_round_trips']:>7d}"
            f"{r['num_sl_hits']:>7d}"
            f"{r['num_tp_hits']:>7d}"
        )
    print(f"{'='*110}")


if __name__ == "__main__":
    results = [run_for_ticker(t) for t in WATCHLIST]
    print_report(results)
