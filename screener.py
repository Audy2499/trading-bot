"""
สแกนหาหุ้น "น่าสนใจ" อัตโนมัติจาก universe ที่กำหนด แทนการเลือก ticker เอง
เกณฑ์ที่ใช้ (ยิ่งเข้าเงื่อนไขเยอะ ยิ่งคะแนนสูง):
- RSI สุดขั้ว (< 30 หรือ > 70) -> มีโอกาส reversal
- โมเมนตัม 5 วันแรง (|% เปลี่ยนแปลง| สูง)
- ปริมาณซื้อขายผิดปกติ (volume วันนี้ / ค่าเฉลี่ย 20 วัน สูง) -> มีคนสนใจเยอะกว่าปกติ

รัน: python screener.py
"""

import pandas as pd
import yfinance as yf

# universe เริ่มต้น: หุ้นสภาพคล่องสูงข้ามหมวด (ปรับ/เพิ่มได้ตามต้องการ)
UNIVERSE = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
    "JPM", "BAC", "GS",
    "UNH", "JNJ", "PFE",
    "XOM", "CVX",
    "WMT", "COST", "KO",
    "CAT", "BA", "GE",
    "AMD", "AVGO", "CRM",
]

TOP_N = 10
RSI_PERIOD = 14
MOMENTUM_DAYS = 5
VOLUME_LOOKBACK = 20


def compute_metrics(ticker: str) -> dict | None:
    df = yf.download(ticker, period="3mo", auto_adjust=True, progress=False)
    if df.empty or len(df) < VOLUME_LOOKBACK + 1:
        return None
    df.columns = df.columns.get_level_values(0)

    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(RSI_PERIOD).mean()
    loss = (-delta.clip(upper=0)).rolling(RSI_PERIOD).mean()
    rsi = 100 - (100 / (1 + gain / loss))
    latest_rsi = rsi.iloc[-1]

    momentum_pct = (
        (df["Close"].iloc[-1] - df["Close"].iloc[-1 - MOMENTUM_DAYS]) / df["Close"].iloc[-1 - MOMENTUM_DAYS] * 100
    )

    avg_volume = df["Volume"].iloc[-VOLUME_LOOKBACK - 1 : -1].mean()
    volume_ratio = df["Volume"].iloc[-1] / avg_volume if avg_volume > 0 else 0

    if pd.isna(latest_rsi):
        return None

    return {
        "ticker": ticker,
        "price": df["Close"].iloc[-1],
        "rsi": latest_rsi,
        "momentum_5d_pct": momentum_pct,
        "volume_ratio": volume_ratio,
    }


def score(m: dict) -> float:
    s = 0.0
    if m["rsi"] < 30 or m["rsi"] > 70:
        s += 2.0
    s += min(abs(m["momentum_5d_pct"]) / 5, 2.0)  # cap ที่ 2 คะแนน
    s += min(max(m["volume_ratio"] - 1, 0), 2.0)  # volume สูงกว่าเฉลี่ยเท่าไหร่ (cap 2 คะแนน)
    return s


def scan(universe: list[str], top_n: int) -> list[dict]:
    results = []
    for ticker in universe:
        m = compute_metrics(ticker)
        if m is None:
            continue
        m["score"] = score(m)
        results.append(m)
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_n]


def print_report(results: list[dict]) -> None:
    print(f"\n{'='*90}")
    print(f"หุ้นน่าสนใจจากการสแกน {len(UNIVERSE)} ตัว (top {TOP_N})")
    print(f"{'='*90}")
    header = f"{'Ticker':<8}{'ราคา':>10}{'RSI':>8}{'Momentum 5วัน':>15}{'Volume x เฉลี่ย':>17}{'คะแนน':>8}"
    print(header)
    print("-" * 90)
    for r in results:
        flag = ""
        if r["rsi"] < 30:
            flag = "(oversold)"
        elif r["rsi"] > 70:
            flag = "(overbought)"
        print(
            f"{r['ticker']:<8}{r['price']:>10.2f}{r['rsi']:>8.1f}"
            f"{r['momentum_5d_pct']:>+14.2f}%{r['volume_ratio']:>16.2f}x{r['score']:>8.2f}  {flag}"
        )
    print(f"{'='*90}")


if __name__ == "__main__":
    results = scan(UNIVERSE, TOP_N)
    print_report(results)
