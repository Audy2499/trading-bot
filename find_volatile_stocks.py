"""
สแกนหาหุ้นที่ผันผวนสูงใกล้เคียง DELTA.BK (annualized volatility ~70%+, มีวันเดียวขึ้น/ลง >15% บ่อย)
รวม universe หุ้นสหรัฐฯ กลุ่มเก็งกำไร/high-beta + หุ้นไทยกลุ่มเก็งกำไรที่รู้จักกันทั่วไป

รัน: python find_volatile_stocks.py
"""

from volatility_guard import compute_volatility

# หุ้นสหรัฐฯ กลุ่ม high-beta / เก็งกำไร / meme / คริปโตเกี่ยวข้อง
US_VOLATILE_CANDIDATES = [
    "GME", "AMC", "MARA", "RIOT", "COIN", "MSTR",
    "PLTR", "SMCI", "CVNA", "SOFI", "RIVN", "LCID",
    "UPST", "AFRM", "HOOD",
]

# หุ้นไทยกลุ่มที่นักลงทุนไทยรู้จักว่ามีความผันผวนสูง/เก็งกำไรหนัก (ต้องเช็คสถานะปัจจุบันเสมอ ราคาหุ้นเปลี่ยนพฤติกรรมได้)
THAI_VOLATILE_CANDIDATES = [
    "DELTA.BK", "JAS.BK", "TRUE.BK", "JMART.BK", "GULF.BK", "STA.BK",
]

REFERENCE_TICKER = "DELTA.BK"  # ใช้เป็นเกณฑ์เทียบ


def scan_volatility(tickers: list[str]) -> list[dict]:
    results = []
    for ticker in tickers:
        try:
            vol = compute_volatility(ticker)
            results.append(vol)
        except Exception as e:
            results.append({"ticker": ticker, "error": str(e)})
    return results


def print_report(results: list[dict], reference_vol: float) -> None:
    print(f"\n{'='*90}")
    print(f"หุ้นผันผวนสูง เรียงจากมากไปน้อย (DELTA.BK = เกณฑ์เทียบ, ann. vol = {reference_vol:.1f}%)")
    print(f"{'='*90}")
    header = f"{'Ticker':<12}{'ราคาล่าสุด':>12}{'Ann.Volatility':>16}{'Daily Range':>14}"
    print(header)
    print("-" * 90)

    valid = [r for r in results if "error" not in r]
    valid.sort(key=lambda x: x["annualized_volatility_pct"], reverse=True)

    for r in valid:
        flag = ""
        if r["annualized_volatility_pct"] >= reference_vol:
            flag = "  <-- ผันผวนเท่าหรือมากกว่า DELTA.BK"
        print(
            f"{r['ticker']:<12}{r['last_price']:>12.2f}"
            f"{r['annualized_volatility_pct']:>15.1f}%"
            f"{r['avg_daily_range_pct']:>13.2f}%{flag}"
        )

    errors = [r for r in results if "error" in r]
    if errors:
        print(f"\nดึงข้อมูลไม่ได้ ({len(errors)} ตัว):")
        for e in errors:
            print(f"  {e['ticker']}: {e['error']}")

    print(f"{'='*90}")


if __name__ == "__main__":
    reference = compute_volatility(REFERENCE_TICKER)

    all_candidates = US_VOLATILE_CANDIDATES + THAI_VOLATILE_CANDIDATES
    results = scan_volatility(all_candidates)

    print_report(results, reference["annualized_volatility_pct"])
