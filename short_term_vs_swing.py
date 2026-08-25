"""
เทียบ MA Crossover แบบ "short-term" (5/15 วัน) กับ "swing" เดิม (20/50 วัน)
บนหุ้นที่ screener.py คัดมาว่าน่าสนใจตอนนี้ — ดูว่า short-term คุ้มไหมหลังหักค่าธรรมเนียม

หมายเหตุสำคัญ: นี่คือ backtest ด้วยข้อมูลราคา "รายวัน" (short-term swing, ถือ 2-2 สัปดาห์)
ไม่ใช่ day trading ระดับนาที/ชั่วโมงจริง เพราะข้อมูล intraday ฟรีของ Yahoo
ย้อนหลังได้แค่ ~60 วัน ไม่พอ backtest ให้น่าเชื่อถือ

รัน: python short_term_vs_swing.py
"""

from compare_strategies import START, END, load_data, signal_ma_crossover
from fee_impact_analysis import fee_rate_for, run_backtest_with_fees
from screener import UNIVERSE, TOP_N, scan


def run_comparison(tickers: list[str]) -> list[dict]:
    results = []
    for ticker in tickers:
        fee_rate = fee_rate_for(ticker)
        data = load_data(ticker, START, END)

        for label, fast, slow in [("Short-term (5/15)", 5, 15), ("Swing (20/50)", 20, 50)]:
            signal = signal_ma_crossover(data, fast=fast, slow=slow)
            stats = run_backtest_with_fees(data, signal, fee_rate)
            results.append({"ticker": ticker, "variant": label, **stats})
    return results


def print_report(results: list[dict]) -> None:
    print(f"\n{'='*105}")
    print("Short-term (5/15) vs Swing (20/50) — บนหุ้นที่ screener คัดมา")
    print(f"{'='*105}")
    header = f"{'Ticker':<8}{'รูปแบบ':<20}{'เทรด/ปี':>9}{'ถือเฉลี่ย(วัน)':>15}{'Net Return':>13}{'ค่าธรรมเนียมกิน':>17}"
    print(header)
    print("-" * 105)
    for r in results:
        print(
            f"{r['ticker']:<8}{r['variant']:<20}"
            f"{r['trades_per_year']:>8.1f} "
            f"{r['avg_holding_days']:>14.1f} "
            f"{r['net_return_pct']:>+12.2f}%"
            f"{r['fee_drag_pct']:>16.2f}%"
        )
    print(f"{'='*105}")


if __name__ == "__main__":
    top_picks = scan(UNIVERSE, TOP_N)
    tickers = [p["ticker"] for p in top_picks[:5]]  # เอา 5 ตัวแรกจาก screener มาเทียบ
    print(f"หุ้นที่ screener คัดมา: {', '.join(tickers)}")

    results = run_comparison(tickers)
    print_report(results)
