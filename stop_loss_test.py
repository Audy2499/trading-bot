"""
ทดสอบกลยุทธ์ "เข้าเร็ว ออกเร็ว" (fast MA) ร่วมกับ Stop-Loss หลายระดับ
บน DELTA.BK และ SPCX โดยเฉพาะ (2 ตัวที่ผันผวนสูง/ข้อมูลน้อย) เทียบผลหลังหักค่าธรรมเนียมจริง

Stop-Loss ทำงานแบบนี้: ระหว่างถือ position ถ้าราคา Low ของวันไหนหลุดจุด SL
(entry_price x (1 - SL%)) จะ "ขายทิ้งทันทีที่ราคา SL" ไม่รอสัญญาณกลับตัว
เป็นการจำลอง SL แบบ real-time ไม่ใช่แค่เช็คตอนปิดตลาด

รัน: python stop_loss_test.py
"""

import pandas as pd

from compare_strategies import START, END, INITIAL_CAPITAL, load_data, signal_ma_crossover
from fee_impact_analysis import fee_rate_for

TEST_TICKERS = ["DELTA.BK", "SPCX"]

FAST_STRATEGIES = {
    "MA (3/8) เร็วมาก": (3, 8),
    "MA (5/15) เร็ว": (5, 15),
}

SL_LEVELS_PCT = [None, 3, 5, 8, 12]  # None = ไม่มี SL เทียบเป็น baseline


def run_backtest_with_sl(df: pd.DataFrame, in_position: pd.Series, fee_rate: float, sl_pct: float | None) -> dict:
    cash = INITIAL_CAPITAL
    shares = 0
    entry_price = None
    buy_date = None
    holding_days = []
    total_commission = 0.0
    num_round_trips = 0
    num_sl_hits = 0
    was_holding = False

    for date, row in df.iterrows():
        price = row["Close"]
        low = row["Low"]
        want_hold = bool(in_position.loc[date])

        # เช็ค stop-loss ก่อนเสมอ ถ้าถืออยู่และมี SL ตั้งไว้
        if shares > 0 and sl_pct is not None:
            stop_price = entry_price * (1 - sl_pct / 100)
            if low <= stop_price:
                proceeds = shares * stop_price
                commission = proceeds * fee_rate
                cash += proceeds - commission
                total_commission += commission
                holding_days.append((date - buy_date).days)
                num_round_trips += 1
                num_sl_hits += 1
                shares = 0
                was_holding = False
                continue  # โดน SL ไปแล้ว ไม่ต้องเช็คสัญญาณปกติวันนี้ต่อ

        if want_hold and not was_holding and shares == 0:
            shares = int(cash // (price * (1 + fee_rate)))
            cost = shares * price
            commission = cost * fee_rate
            cash -= cost + commission
            total_commission += commission
            entry_price = price
            buy_date = date

        elif not want_hold and was_holding and shares > 0:
            proceeds = shares * price
            commission = proceeds * fee_rate
            cash += proceeds - commission
            total_commission += commission
            holding_days.append((date - buy_date).days)
            num_round_trips += 1
            shares = 0

        was_holding = want_hold

    final_price = df["Close"].iloc[-1]
    final_equity_net = cash + shares * final_price
    net_return_pct = (final_equity_net - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    fee_drag_pct = total_commission / INITIAL_CAPITAL * 100

    years = (df.index[-1] - df.index[0]).days / 365.25
    trades_per_year = (num_round_trips * 2) / years if years > 0 else 0
    avg_holding_days = sum(holding_days) / len(holding_days) if holding_days else 0

    equity_curve = []
    cash_sim, shares_sim = INITIAL_CAPITAL, 0
    # (ประมาณ max drawdown แบบง่ายจาก equity ปลายทาง ไม่ใช่ path เต็ม เพื่อความเรียบง่าย)

    return {
        "net_return_pct": net_return_pct,
        "trades_per_year": trades_per_year,
        "avg_holding_days": avg_holding_days,
        "num_round_trips": num_round_trips,
        "num_sl_hits": num_sl_hits,
        "total_commission": total_commission,
        "fee_drag_pct": fee_drag_pct,
    }


def print_report(results: list[dict]) -> None:
    print(f"\n{'='*115}")
    print("Fast Entry/Exit + Stop-Loss เทียบกับค่าธรรมเนียม — DELTA.BK & SPCX")
    print(f"{'='*115}")
    header = (
        f"{'Ticker':<10}{'กลยุทธ์':<18}{'SL':>6}{'Net Return':>13}"
        f"{'เทรด/ปี':>9}{'ถือเฉลี่ย(วัน)':>15}{'โดน SL กี่ครั้ง':>15}{'ค่าธรรมเนียมกิน':>17}"
    )
    print(header)
    print("-" * 115)
    for r in results:
        sl_label = f"{r['sl_pct']}%" if r["sl_pct"] is not None else "ไม่มี"
        print(
            f"{r['ticker']:<10}{r['strategy']:<18}{sl_label:>6}"
            f"{r['net_return_pct']:>+12.2f}%"
            f"{r['trades_per_year']:>8.1f} "
            f"{r['avg_holding_days']:>14.1f} "
            f"{r['num_sl_hits']:>14d} "
            f"{r['fee_drag_pct']:>15.2f}%"
        )
    print(f"{'='*115}")


if __name__ == "__main__":
    results = []
    for ticker in TEST_TICKERS:
        fee_rate = fee_rate_for(ticker)
        data = load_data(ticker, START, END)

        if len(data) < 20:
            print(f"\n⚠️  {ticker}: มีข้อมูลแค่ {len(data)} วัน — น้อยเกินกว่าจะ backtest ได้น่าเชื่อถือ (ข้ามการทดสอบ)")
            continue

        for strat_name, (fast, slow) in FAST_STRATEGIES.items():
            if len(data) < slow + 5:
                print(f"\n⚠️  {ticker} / {strat_name}: ข้อมูล {len(data)} วัน ไม่พอสำหรับ MA{slow} (ข้าม)")
                continue
            signal = signal_ma_crossover(data, fast=fast, slow=slow)
            for sl_pct in SL_LEVELS_PCT:
                stats = run_backtest_with_sl(data, signal, fee_rate, sl_pct)
                results.append({"ticker": ticker, "strategy": strat_name, "sl_pct": sl_pct, **stats})

    print_report(results)
