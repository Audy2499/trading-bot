"""
รัน composite signal (เทคนิค + ข่าว) ข้ามหุ้นหลายหมวดอุตสาหกรรม
เพื่อดูว่า pipeline ที่สร้างไว้ใช้ได้กว้างกว่าแค่หุ้นเทคไหม

รัน: python multi_sector_signal.py
"""

from fetch_news_signal import NEWS_LIMIT, get_latest_news, get_technical_snapshot
from news_sentiment_signal import score_sentiment, combine_signal

SECTOR_TICKERS = {
    "การเงิน": "JPM",
    "สุขภาพ": "UNH",
    "พลังงาน": "XOM",
    "สินค้าอุปโภคบริโภค": "WMT",
    "อุตสาหกรรม": "CAT",
    "เทคโนโลยี (baseline)": "NVDA",
}


def run_all() -> list[dict]:
    results = []
    for sector, ticker in SECTOR_TICKERS.items():
        try:
            news = get_latest_news(ticker, NEWS_LIMIT)
            tech = get_technical_snapshot(ticker)
            scores = score_sentiment(ticker, news)
            combined = combine_signal(tech, scores)
            results.append({"sector": sector, "ticker": ticker, **combined, "error": None})
        except Exception as e:
            results.append(
                {
                    "sector": sector,
                    "ticker": ticker,
                    "avg_sentiment": None,
                    "technical_bullish": None,
                    "action": None,
                    "error": str(e),
                }
            )
    return results


def print_summary(results: list[dict]) -> None:
    print(f"\n{'='*90}")
    print("สรุป Composite Signal ข้ามหมวดอุตสาหกรรม")
    print(f"{'='*90}")
    header = f"{'หมวด':<22}{'Ticker':<8}{'Sentiment':>10}{'Technical':>12}   คำแนะนำ"
    print(header)
    print("-" * 90)
    for r in results:
        if r["error"]:
            print(f"{r['sector']:<22}{r['ticker']:<8}  ERROR: {r['error']}")
            continue
        tech_label = "BULLISH" if r["technical_bullish"] else "BEARISH"
        print(
            f"{r['sector']:<22}{r['ticker']:<8}"
            f"{r['avg_sentiment']:>+9.2f} "
            f"{tech_label:>12}   {r['action']}"
        )
    print(f"{'='*90}")


if __name__ == "__main__":
    results = run_all()
    print_summary(results)
