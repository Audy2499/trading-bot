"""
รัน fast MA + Stop-Loss (เหมือน stop_loss_test.py) กับหุ้นผันผวนสูงทุกตัวที่ find_volatile_stocks.py เจอ
แล้วคัดว่าตัวไหน "ใช้ได้จริง" หลังหักค่าธรรมเนียม ไม่ใช่แค่ผันผวนเฉยๆ

เกณฑ์คัดออก (ต้องผ่านทุกข้อ):
- net_return_pct > 0 (ต้องกำไรสุทธิหลังหักค่าธรรมเนียมแล้ว)
- num_round_trips >= 10 (มีจำนวนเทรดพอจะเชื่อสถิติได้ ไม่ใช่ fluke จากไม้เดียว)
- ข้อมูลราคาย้อนหลัง >= 250 วัน (พอสำหรับ MA ยาวสุดที่ใช้ + มีนัยสำคัญทางสถิติ)

รัน: python best_volatile_picks.py
"""

from compare_strategies import START, END, load_data, signal_ma_crossover
from fee_impact_analysis import fee_rate_for
from stop_loss_test import FAST_STRATEGIES, SL_LEVELS_PCT, run_backtest_with_sl
from find_volatile_stocks import US_VOLATILE_CANDIDATES, THAI_VOLATILE_CANDIDATES

MIN_TRADES = 10
MIN_DATA_DAYS = 250

CANDIDATES = US_VOLATILE_CANDIDATES + THAI_VOLATILE_CANDIDATES + ["DELTA.BK"]
CANDIDATES = list(dict.fromkeys(CANDIDATES))  # ตัดตัวซ้ำ (DELTA.BK อยู่ใน THAI list แล้ว)


def find_best_config(ticker: str) -> dict | None:
    fee_rate = fee_rate_for(ticker)
    data = load_data(ticker, START, END)

    if len(data) < MIN_DATA_DAYS:
        return {"ticker": ticker, "skipped": f"ข้อมูลแค่ {len(data)} วัน (ต้องการ >= {MIN_DATA_DAYS})"}

    best = None
    for strat_name, (fast, slow) in FAST_STRATEGIES.items():
        if len(data) < slow + 5:
            continue
        signal = signal_ma_crossover(data, fast=fast, slow=slow)
        for sl_pct in SL_LEVELS_PCT:
            stats = run_backtest_with_sl(data, signal, fee_rate, sl_pct)
            candidate = {"ticker": ticker, "strategy": strat_name, "sl_pct": sl_pct, **stats}
            if best is None or candidate["net_return_pct"] > best["net_return_pct"]:
                best = candidate

    return best


def print_report(all_results: list[dict]) -> None:
    passed = [
        r for r in all_results
        if "skipped" not in r
        and r["net_return_pct"] > 0
        and r["num_round_trips"] >= MIN_TRADES
    ]
    passed.sort(key=lambda x: x["net_return_pct"], reverse=True)

    print(f"\n{'='*115}")
    print(f"✅ ผ่านเกณฑ์คัด (กำไรสุทธิจริง + เทรด >= {MIN_TRADES} ครั้ง + ข้อมูลพอ)")
    print(f"{'='*115}")
    header = f"{'Ticker':<10}{'กลยุทธ์ที่ดีที่สุด':<18}{'SL':>6}{'Net Return':>13}{'เทรด/ปี':>9}{'ถือเฉลี่ย(วัน)':>15}{'ค่าธรรมเนียมกิน':>17}"
    print(header)
    print("-" * 115)
    for r in passed:
        sl_label = f"{r['sl_pct']}%" if r["sl_pct"] is not None else "ไม่มี"
        print(
            f"{r['ticker']:<10}{r['strategy']:<18}{sl_label:>6}"
            f"{r['net_return_pct']:>+12.2f}%"
            f"{r['trades_per_year']:>8.1f} "
            f"{r['avg_holding_days']:>14.1f} "
            f"{r['fee_drag_pct']:>16.2f}%"
        )

    failed = [r for r in all_results if r not in passed and "skipped" not in r]
    skipped = [r for r in all_results if "skipped" in r]

    if failed:
        print(f"\n❌ ไม่ผ่านเกณฑ์ ({len(failed)} ตัว) — กำไรไม่พอ หรือเทรดน้อยเกินจะเชื่อสถิติ:")
        for r in failed:
            print(f"  {r['ticker']:<10} best net_return={r['net_return_pct']:+.2f}%  round_trips={r['num_round_trips']}")

    if skipped:
        print(f"\n⚠️  ข้ามการทดสอบ ({len(skipped)} ตัว) — ข้อมูลไม่พอ:")
        for r in skipped:
            print(f"  {r['ticker']:<10} {r['skipped']}")

    print(f"{'='*115}")


if __name__ == "__main__":
    print(f"กำลังทดสอบ {len(CANDIDATES)} ตัว: {', '.join(CANDIDATES)}")
    results = [find_best_config(t) for t in CANDIDATES]
    print_report(results)
