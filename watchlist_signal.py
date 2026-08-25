"""
รัน composite signal (เทคนิค + ข่าว) กับ watchlist ส่วนตัว (watchlist.py)

รัน: python watchlist_signal.py
"""

from fetch_news_signal import NEWS_LIMIT, get_latest_news, get_technical_snapshot
from news_sentiment_signal import score_sentiment, combine_signal
from watchlist import WATCHLIST


def run_all() -> list[dict]:
    results = []
    for ticker, note in WATCHLIST.items():
        try:
            news = get_latest_news(ticker, NEWS_LIMIT)
            tech = get_technical_snapshot(ticker)
            scores = score_sentiment(ticker, news)
            combined = combine_signal(tech, scores)
            results.append({"ticker": ticker, "note": note, **combined, "error": None})
        except Exception as e:
            results.append(
                {
                    "ticker": ticker,
                    "note": note,
                    "avg_sentiment": None,
                    "technical_bullish": None,
                    "action": None,
                    "error": str(e),
                }
            )
    return results


def print_summary(results: list[dict]) -> None:
    print(f"\n{'='*100}")
    print("Composite Signal — Watchlist ส่วนตัว")
    print(f"{'='*100}")
    for r in results:
        print(f"\n{r['ticker']}  ({r['note']})")
        if r["error"]:
            print(f"  ERROR: {r['error']}")
            continue
        tech_label = "BULLISH" if r["technical_bullish"] else "BEARISH"
        print(f"  Sentiment: {r['avg_sentiment']:+.2f}   Technical: {tech_label}")
        print(f"  คำแนะนำ: {r['action']}")
    print(f"\n{'='*100}")


if __name__ == "__main__":
    results = run_all()
    print_summary(results)
