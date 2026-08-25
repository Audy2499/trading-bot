"""
ต่อยอดจาก fetch_news_signal.py:
ดึงข่าวล่าสุด -> ส่งให้ Gemini ให้คะแนน sentiment เป็นตัวเลข -> รวมกับสัญญาณเทคนิค
เป็นสัญญาณ composite เดียว

ก่อนรัน:
1. คัดลอก .env.example เป็น .env
2. วาง GEMINI_API_KEY ของพี่ลงในไฟล์ .env (ไฟล์นี้ไม่ต้องส่งให้ใคร เก็บไว้ในเครื่อง)

รัน: python news_sentiment_signal.py
"""

import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from fetch_news_signal import TICKER, NEWS_LIMIT, get_latest_news, get_technical_snapshot

load_dotenv()

MODEL = "gemini-3.6-flash"

SENTIMENT_PROMPT = """คุณคือนักวิเคราะห์การเงิน ให้คะแนน sentiment ของข่าวแต่ละข้อว่าส่งผลต่อราคาหุ้น {ticker} อย่างไร
ให้คะแนนเป็นตัวเลข -1.0 (ลบมากที่สุด) ถึง +1.0 (บวกมากที่สุด) 0 คือเป็นกลาง/ไม่เกี่ยวข้อง

ข่าว:
{news_list}

ตอบเป็น JSON array เท่านั้น รูปแบบ:
[{{"title": "...", "score": 0.0, "reason": "เหตุผลสั้นๆ ภาษาไทย"}}]
"""


def score_sentiment(ticker: str, news: list[dict]) -> list[dict]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ไม่พบ GEMINI_API_KEY — คัดลอก .env.example เป็น .env แล้ววาง key ก่อนรัน"
        )

    client = genai.Client(api_key=api_key)
    news_list = "\n".join(f"- {n['title']}" for n in news)
    prompt = SENTIMENT_PROMPT.format(ticker=ticker, news_list=news_list)

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return json.loads(response.text)


def combine_signal(tech: dict, sentiment_scores: list[dict]) -> dict:
    avg_score = (
        sum(s["score"] for s in sentiment_scores) / len(sentiment_scores)
        if sentiment_scores
        else 0.0
    )

    technical_bullish = tech["ma_crossover_bullish"]

    conflicted = False
    if technical_bullish and avg_score >= -0.2:
        action = "เข้า/ถือ (technical + ข่าวไม่ขัดแย้งกัน)"
    elif not technical_bullish and avg_score <= 0.2:
        action = "หลีกเลี่ยง/ไม่เข้า (technical + ข่าวไม่สนับสนุน)"
    else:
        action = "สัญญาณขัดแย้งกัน — ควรระวัง ไม่ควรเข้าเต็มไม้"
        conflicted = True

    return {
        "avg_sentiment": avg_score,
        "technical_bullish": technical_bullish,
        "action": action,
        "conflicted": conflicted,
    }


def print_report(ticker: str, sentiment_scores: list[dict], combined: dict) -> None:
    print(f"\n[Sentiment รายข่าว]")
    for s in sentiment_scores:
        print(f"  ({s['score']:+.2f}) {s['title']}")
        print(f"         เหตุผล: {s['reason']}")

    print(f"\n{'='*60}")
    print(f"สัญญาณ Composite — {ticker}")
    print(f"{'='*60}")
    print(f"  Sentiment เฉลี่ย:     {combined['avg_sentiment']:+.2f}")
    print(f"  Technical (MA):       {'BULLISH' if combined['technical_bullish'] else 'BEARISH'}")
    print(f"  คำแนะนำ:              {combined['action']}")
    print(f"{'='*60}")


if __name__ == "__main__":
    news = get_latest_news(TICKER, NEWS_LIMIT)
    tech = get_technical_snapshot(TICKER)
    scores = score_sentiment(TICKER, news)
    combined = combine_signal(tech, scores)
    print_report(TICKER, scores, combined)
