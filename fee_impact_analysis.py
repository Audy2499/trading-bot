"""
วิเคราะห์ 3 กลยุทธ์ที่ใช้อยู่ (MA Crossover, RSI, Bollinger Bands) บน watchlist จริง:
- ความถี่ในการซื้อขาย (เทรด/ปี)
- ระยะเวลาถือครองเฉลี่ยต่อไม้
- ผลตอบแทนก่อน vs หลังหักค่าธรรมเนียมจริงของ Webull TH

ค่าธรรมเนียมอ้างอิงจากหน้าเว็บ Webull TH (webull.co.th):
- หุ้นสหรัฐฯ: 0.10% ต่อการซื้อขาย (ไม่มีขั้นต่ำ)
- หุ้นไทย: 0.04% ต่อการซื้อขาย (ไม่มีขั้นต่ำ)
เก็บทั้งฝั่งซื้อและฝั่งขาย (2 ขา ต่อ 1 รอบเทรด)

รัน: python fee_impact_analysis.py
"""

import pandas as pd

from compare_strategies import START, END, INITIAL_CAPITAL, load_data, signal_ma_crossover, signal_rsi, signal_bollinger
from watchlist import WATCHLIST

US_FEE_RATE = 0.0010
THAI_FEE_RATE = 0.0004

STRATEGIES = {
    "MA Crossover (20/50)": signal_ma_crossover,
    "RSI Mean Reversion": signal_rsi,
    "Bollinger Bands": signal_bollinger,
}


def fee_rate_for(ticker: str) -> float:
    return THAI_FEE_RATE if ticker.endswith(".BK") else US_FEE_RATE


def run_backtest_with_fees(df: pd.DataFrame, in_position: pd.Series, fee_rate: float) -> dict:
    cash = INITIAL_CAPITAL
    shares = 0
    buy_date = None
    holding_days = []
    total_commission = 0.0
    num_round_trips = 0
    was_holding = False

    for date, row in df.iterrows():
        price = row["Close"]
        want_hold = bool(in_position.loc[date])

        if want_hold and not was_holding and shares == 0:
            shares = int(cash // (price * (1 + fee_rate)))
            cost = shares * price
            commission = cost * fee_rate
            cash -= cost + commission
            total_commission += commission
            buy_date = date

        elif not want_hold and was_holding and shares > 0:
            proceeds = shares * price
            commission = proceeds * fee_rate
            cash += proceeds - commission
            total_commission += commission
            if buy_date is not None:
                holding_days.append((date - buy_date).days)
                num_round_trips += 1
            shares = 0

        was_holding = want_hold

    final_price = df["Close"].iloc[-1]
    final_equity_net = cash + shares * final_price
    net_return_pct = (final_equity_net - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    gross_return_pct = net_return_pct + (total_commission / INITIAL_CAPITAL * 100)

    years = (df.index[-1] - df.index[0]).days / 365.25
    trades_per_year = (num_round_trips * 2) / years if years > 0 else 0
    avg_holding_days = sum(holding_days) / len(holding_days) if holding_days else 0

    return {
        "gross_return_pct": gross_return_pct,
        "net_return_pct": net_return_pct,
        "fee_drag_pct": gross_return_pct - net_return_pct,
        "total_commission": total_commission,
        "num_round_trips": num_round_trips,
        "trades_per_year": trades_per_year,
        "avg_holding_days": avg_holding_days,
    }


def print_report(results: list[dict]) -> None:
    print(f"\n{'='*115}")
    print("ผลกระทบค่าธรรมเนียม + ความถี่การเทรด + ระยะเวลาถือครอง")
    print(f"{'='*115}")
    header = (
        f"{'Ticker':<10}{'กลยุทธ์':<22}{'เทรด/ปี':>9}{'ถือเฉลี่ย(วัน)':>15}"
        f"{'Gross Return':>14}{'Net Return':>12}{'ค่าธรรมเนียมกิน':>17}"
    )
    print(header)
    print("-" * 115)
    for r in results:
        print(
            f"{r['ticker']:<10}{r['strategy']:<22}"
            f"{r['trades_per_year']:>8.1f} "
            f"{r['avg_holding_days']:>14.1f} "
            f"{r['gross_return_pct']:>+13.2f}%"
            f"{r['net_return_pct']:>+11.2f}%"
            f"{r['fee_drag_pct']:>16.2f}%"
        )
    print(f"{'='*115}")


if __name__ == "__main__":
    results = []
    for ticker in WATCHLIST:
        fee_rate = fee_rate_for(ticker)
        data = load_data(ticker, START, END)
        for strat_name, signal_fn in STRATEGIES.items():
            signal = signal_fn(data)
            stats = run_backtest_with_fees(data, signal, fee_rate)
            results.append({"ticker": ticker, "strategy": strat_name, **stats})

    print_report(results)
