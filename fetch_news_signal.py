"""
ดึงข่าวล่าสุดของหุ้น + สถานะสัญญาณเทคนิคปัจจุบัน มาแสดงคู่กัน
เพื่อเป็น input ให้ LLM (Claude/Gemini) วิเคราะห์ sentiment ต่อ

หมายเหตุ: สคริปต์นี้ "ดึงข้อมูล" เท่านั้น ยังไม่ได้เรียก LLM API จริง
เพราะต้องมี API key ก่อน (ตอนนี้ยังรอ Webull API อนุมัติ + ยังไม่ได้ตั้งค่า
Claude/Gemini API key) — เอาไว้ต่อ LLM ทีหลังตรงจุดที่คอมเมนต์ไว้

รัน: python fetch_news_signal.py
"""

import yfinance as yf
from datetime import datetime

from compare_strategies import load_data, signal_ma_crossover, signal_rsi

TICKER = "NVDA"
NEWS_LIMIT = 8


def get_latest_news(ticker: str, limit: int) -> list[dict]:
    t = yf.Ticker(ticker)
    raw = t.news[:limit]
    news = []
    for item in raw:
        content = item.get("content", item)
        title = content.get("title", "(ไม่มีหัวข้อ)")
        publisher = content.get("provider", {}).get("displayName", "ไม่ทราบแหล่งข่าว")
        pub_date = content.get("pubDate", "")
        news.append({"title": title, "publisher": publisher, "pub_date": pub_date})
    return news


def get_technical_snapshot(ticker: str) -> dict:
    data = load_data(ticker, "2024-01-01", datetime.today().strftime("%Y-%m-%d"))
    ma_signal = signal_ma_crossover(data)
    rsi_signal = signal_rsi(data)
    last_close = data["Close"].iloc[-1]
    return {
        "last_close": last_close,
        "ma_crossover_bullish": bool(ma_signal.iloc[-1]),
        "rsi_oversold_recovery_position": bool(rsi_signal.iloc[-1]),
    }


def print_report(ticker: str, news: list[dict], tech: dict) -> None:
    print(f"\n{'='*60}")
    print(f"สรุปข้อมูลสำหรับ {ticker} — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")

    print(f"\n[สถานะเทคนิคปัจจุบัน]")
    print(f"  ราคาปิดล่าสุด:        {tech['last_close']:.2f}")
    print(f"  MA Crossover:         {'BULLISH (ถืออยู่)' if tech['ma_crossover_bullish'] else 'BEARISH (ไม่ถือ)'}")
    print(f"  RSI position:         {'IN POSITION' if tech['rsi_oversold_recovery_position'] else 'OUT'}")

    print(f"\n[ข่าวล่าสุด {len(news)} รายการ]")
    for i, n in enumerate(news, 1):
        print(f"  {i}. {n['title']}")
        print(f"     แหล่ง: {n['publisher']}  |  วันที่: {n['pub_date']}")

    print(f"\n{'='*60}")
    print("ขั้นต่อไป: ส่งหัวข้อข่าวด้านบนให้ LLM วิเคราะห์ sentiment")
    print("แล้วรวมกับสถานะเทคนิค เพื่อสร้างสัญญาณ composite")
    print(f"{'='*60}")


if __name__ == "__main__":
    news = get_latest_news(TICKER, NEWS_LIMIT)
    tech = get_technical_snapshot(TICKER)
    print_report(TICKER, news, tech)
