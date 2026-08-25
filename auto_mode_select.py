"""
รัน screener หาหุ้นน่าสนใจ -> เทียบ Short-term (5/15) vs Swing (20/50) ให้แต่ละตัว
-> เลือกโหมดที่ backtest ได้ผลตอบแทนสุทธิ (หลังหักค่าธรรมเนียม) ดีกว่าอัตโนมัติ

รัน: python auto_mode_select.py
"""

from compare_strategies import START, END, load_data, signal_ma_crossover
from fee_impact_analysis import fee_rate_for, run_backtest_with_fees
from screener import UNIVERSE, TOP_N, scan


def pick_best_mode(ticker: str) -> dict:
    fee_rate = fee_rate_for(ticker)
    data = load_data(ticker, START, END)

    variants = {}
    for label, fast, slow in [("short_term", 5, 15), ("swing", 20, 50)]:
        signal = signal_ma_crossover(data, fast=fast, slow=slow)
        variants[label] = run_backtest_with_fees(data, signal, fee_rate)

    best_label = max(variants, key=lambda k: variants[k]["net_return_pct"])
    return {"ticker": ticker, "recommended_mode": best_label, "variants": variants}


def print_report(picks: list[dict]) -> None:
    print(f"\n{'='*100}")
    print("โหมดที่แนะนำอัตโนมัติต่อหุ้น (เลือกจาก Net Return หลังหักค่าธรรมเนียมที่สูงกว่า)")
    print(f"{'='*100}")
    header = f"{'Ticker':<8}{'โหมดที่แนะนำ':<15}{'Net(short-term)':>16}{'Net(swing)':>13}{'ส่วนต่าง':>12}"
    print(header)
    print("-" * 100)
    for p in picks:
        st = p["variants"]["short_term"]["net_return_pct"]
        sw = p["variants"]["swing"]["net_return_pct"]
        diff = st - sw if p["recommended_mode"] == "short_term" else sw - st
        mode_th = "Short-term" if p["recommended_mode"] == "short_term" else "Swing"
        print(f"{p['ticker']:<8}{mode_th:<15}{st:>+15.2f}%{sw:>+12.2f}%{diff:>+11.2f}%")
    print(f"{'='*100}")
    print("หมายเหตุ: ผลจาก backtest ย้อนหลัง ไม่รับประกันว่าโหมดเดิมจะดีที่สุดในอนาคต")
    print("ควรรีสแกน+ประเมินซ้ำเป็นระยะ ไม่ใช่ยึดโหมดเดียวตลอดไป")


if __name__ == "__main__":
    top_picks = scan(UNIVERSE, TOP_N)
    tickers = [p["ticker"] for p in top_picks[:5]]
    print(f"หุ้นที่ screener คัดมาวันนี้: {', '.join(tickers)}")

    picks = [pick_best_mode(t) for t in tickers]
    print_report(picks)
