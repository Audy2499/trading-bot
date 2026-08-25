"""
เครื่องมือป้องกันหุ้นผันผวนสูง (เช่น DELTA.BK) ทำลายพอร์ต มี 2 ฟังก์ชันหลัก:

1. compute_volatility() — วัดความผันผวนจริงของหุ้น (annualized volatility จาก daily return)
2. position_size() — คำนวณขนาดไม้ตาม "ความเสี่ยงที่ยอมรับได้" ไม่ใช่ตามวงเงินเปล่าๆ
   หุ้นผันผวนสูง -> ไม้เล็กลงอัตโนมัติ / หุ้นนิ่ง -> ไม้ใหญ่ขึ้นได้
   (แนวคิดเดียวกับ "risk parity" / "volatility targeting" ที่กองทุนใช้จริง)

รัน: python volatility_guard.py
"""

import numpy as np

from compare_strategies import START, END, load_data

POSITION_SIZING_MODE = "all_in"  # โหมดหลัก (ใช้กับทุก ticker ที่ไม่ได้ override) "all_in" | "volatility_scaled"
MAX_RISK_PER_TRADE_PCT = 1.0  # ใช้เฉพาะโหมด volatility_scaled: ยอมเสี่ยงสูญเสียได้กี่ % ของทุน ต่อ 1 position
VOLATILITY_EXCLUDE_THRESHOLD = 80.0  # ถ้า annualized volatility เกินนี้ (%) -> ตัดทิ้งเสมอ ไม่ว่าโหมดไหน (เกราะป้องกันขั้นต่ำ)

# override โหมดเฉพาะ ticker (มีผลเหนือกว่า POSITION_SIZING_MODE หลัก) — ใส่เหตุผลกำกับไว้เตือนตัวเองด้วย
TICKER_MODE_OVERRIDES = {
    "DELTA.BK": "volatility_scaled",  # ผันผวนสุดขั้ว (เคยขึ้น/ลง >20% ในวันเดียวหลายครั้ง) ไม่ควรออลอิน
    "SPCX": "volatility_scaled",       # ข้อมูลราคามีแค่ ~34 วัน ยังประเมินความเสี่ยงจริงไม่ได้
}


def compute_volatility(ticker: str) -> dict:
    data = load_data(ticker, START, END)
    daily_returns = data["Close"].pct_change().dropna()

    annualized_vol_pct = daily_returns.std() * np.sqrt(252) * 100

    # ATR แบบง่าย (14 วัน) ใช้ high-low range แทนของจริงที่ต้องมี intraday high/low
    daily_range_pct = ((data["Close"].rolling(2).max() - data["Close"].rolling(2).min())
                        / data["Close"] * 100).rolling(14).mean().iloc[-1]

    return {
        "ticker": ticker,
        "annualized_volatility_pct": annualized_vol_pct,
        "avg_daily_range_pct": daily_range_pct,
        "last_price": data["Close"].iloc[-1],
    }


def position_size(vol_info: dict, capital: float, mode: str = None) -> dict:
    """
    "volatility_scaled": ยิ่งผันผวนสูง ยิ่งได้เงินลงทุนน้อยลง (risk parity)
    "all_in"           : ซื้อเต็มวงเงินเสมอ ถ้าผ่านเกณฑ์ VOLATILITY_EXCLUDE_THRESHOLD
                          (เกราะป้องกันขั้นต่ำที่ยังมีอยู่เสมอ ไม่ว่าจะเลือกโหมดไหน)
    """
    ticker = vol_info["ticker"]
    mode = mode or TICKER_MODE_OVERRIDES.get(ticker, POSITION_SIZING_MODE)
    price = vol_info["last_price"]
    shares_by_capital = int(capital // price)  # ห้ามซื้อเกินทุนที่มีจริง ไม่ว่าโหมดไหน

    if mode == "all_in":
        shares = shares_by_capital
    elif mode == "volatility_scaled":
        max_loss_amount = capital * MAX_RISK_PER_TRADE_PCT / 100
        daily_range_pct = vol_info["avg_daily_range_pct"]
        risk_per_share = price * daily_range_pct / 100
        shares_by_risk = int(max_loss_amount / risk_per_share) if risk_per_share > 0 else 0
        shares = min(shares_by_risk, shares_by_capital)
    else:
        raise ValueError(f"ไม่รู้จักโหมด: {mode}")

    excluded = vol_info["annualized_volatility_pct"] > VOLATILITY_EXCLUDE_THRESHOLD
    if excluded:
        shares = 0  # เกราะป้องกันขั้นต่ำ: ผันผวนเกินเกณฑ์ -> ไม่เข้าเลย ไม่ว่าโหมดไหน

    position_value = shares * price
    position_pct_of_capital = position_value / capital * 100

    return {
        "ticker": vol_info["ticker"],
        "mode": mode,
        "shares_allowed": shares,
        "position_value": position_value,
        "position_pct_of_capital": position_pct_of_capital,
        "excluded": excluded,
    }


def print_report(results: list[dict], capital: float) -> None:
    print(f"\n{'='*100}")
    print(f"Volatility Guard — ทุนทั้งหมด {capital:,.0f} | ยอมเสี่ยง {MAX_RISK_PER_TRADE_PCT}%/ไม้ | ตัดหุ้นที่ vol > {VOLATILITY_EXCLUDE_THRESHOLD}%")
    print(f"{'='*100}")
    header = f"{'Ticker':<10}{'Ann.Volatility':>15}{'Daily Range':>13}{'ไม้ที่อนุญาต':>13}{'มูลค่าไม้':>13}{'% ของทุน':>10}"
    print(header)
    print("-" * 100)
    for r in results:
        flag = "  <-- ตัดออก (ผันผวนเกินเกณฑ์)" if r["sizing"]["excluded"] else ""
        print(
            f"{r['ticker']:<10}"
            f"{r['vol']['annualized_volatility_pct']:>14.1f}%"
            f"{r['vol']['avg_daily_range_pct']:>12.2f}%"
            f"{r['sizing']['shares_allowed']:>13d}"
            f"{r['sizing']['position_value']:>13,.0f}"
            f"{r['sizing']['position_pct_of_capital']:>9.2f}%{flag}"
        )
    print(f"{'='*100}")


if __name__ == "__main__":
    from watchlist import WATCHLIST

    CAPITAL = 100_000.0
    results = []
    for ticker in WATCHLIST:
        vol = compute_volatility(ticker)
        sizing = position_size(vol, CAPITAL)
        results.append({"ticker": ticker, "vol": vol, "sizing": sizing})

    print_report(results, CAPITAL)
