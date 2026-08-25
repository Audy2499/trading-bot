"""
หาวิธี Stop-Loss ที่เหมาะกับ DELTA.BK มากที่สุด เทียบ 3 แบบ บนกลยุทธ์ MA(5/15) ที่เป็นตัวชนะเดิม:

1. Fixed SL (grid ละเอียดขึ้น) — % คงที่จากราคาเข้า เหมือนเดิมแต่ทดสอบละเอียดกว่า
2. Trailing SL — จุด SL ขยับตามราคาสูงสุดตั้งแต่เข้า (ล็อกกำไรไว้ ไม่ใช่ตรึงจุดเดิม)
3. ATR-based SL — ระยะ SL ปรับตามความผันผวนจริงรายวัน (ATR 14 วัน) แทนเปอร์เซ็นต์ตายตัว

รัน: python delta_sl_optimization.py
"""

import pandas as pd

from compare_strategies import START, END, INITIAL_CAPITAL, load_data, signal_ma_crossover
from fee_impact_analysis import fee_rate_for

TICKER = "DELTA.BK"
FAST, SLOW = 5, 15
FIXED_SL_GRID = [1, 2, 3, 4, 5, 6, 7, 8, 10, 15, 20]
TRAILING_SL_GRID = [3, 5, 8, 10, 15]
ATR_MULTIPLIER_GRID = [1.0, 1.5, 2.0, 2.5, 3.0]
ATR_PERIOD = 14


def compute_atr(df: pd.DataFrame, period: int) -> pd.Series:
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return true_range.rolling(period).mean()


def run_backtest(df: pd.DataFrame, in_position: pd.Series, fee_rate: float, sl_mode: str, sl_param, atr: pd.Series = None) -> dict:
    cash = INITIAL_CAPITAL
    shares = 0
    entry_price = None
    highest_since_entry = None
    buy_date = None
    holding_days = []
    total_commission = 0.0
    num_round_trips = 0
    num_sl_hits = 0
    was_holding = False

    for date, row in df.iterrows():
        price = row["Close"]
        low = row["Low"]
        high = row["High"]
        want_hold = bool(in_position.loc[date])

        if shares > 0:
            if sl_mode == "fixed":
                stop_price = entry_price * (1 - sl_param / 100)
            elif sl_mode == "trailing":
                highest_since_entry = max(highest_since_entry, high)
                stop_price = highest_since_entry * (1 - sl_param / 100)
            elif sl_mode == "atr":
                stop_price = entry_price - sl_param * atr.loc[date] if pd.notna(atr.loc[date]) else None
            else:
                stop_price = None

            if stop_price is not None and low <= stop_price:
                proceeds = shares * stop_price
                commission = proceeds * fee_rate
                cash += proceeds - commission
                total_commission += commission
                holding_days.append((date - buy_date).days)
                num_round_trips += 1
                num_sl_hits += 1
                shares = 0
                was_holding = False
                continue

        if want_hold and not was_holding and shares == 0:
            shares = int(cash // (price * (1 + fee_rate)))
            cost = shares * price
            commission = cost * fee_rate
            cash -= cost + commission
            total_commission += commission
            entry_price = price
            highest_since_entry = price
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

    return {
        "net_return_pct": net_return_pct,
        "trades_per_year": trades_per_year,
        "avg_holding_days": avg_holding_days,
        "num_sl_hits": num_sl_hits,
        "fee_drag_pct": fee_drag_pct,
    }


def print_report(results: list[dict]) -> None:
    results.sort(key=lambda x: x["net_return_pct"], reverse=True)
    print(f"\n{'='*110}")
    print(f"DELTA.BK — เทียบวิธี Stop-Loss บนกลยุทธ์ MA({FAST}/{SLOW}) (เรียงจากผลตอบแทนสูงสุด)")
    print(f"{'='*110}")
    header = f"{'วิธี SL':<25}{'พารามิเตอร์':>12}{'Net Return':>13}{'เทรด/ปี':>9}{'ถือเฉลี่ย(วัน)':>15}{'โดน SL':>8}{'ค่าธรรมเนียมกิน':>17}"
    print(header)
    print("-" * 110)
    for r in results:
        print(
            f"{r['label']:<25}{r['param']:>12}"
            f"{r['net_return_pct']:>+12.2f}%"
            f"{r['trades_per_year']:>8.1f} "
            f"{r['avg_holding_days']:>14.1f} "
            f"{r['num_sl_hits']:>8d}"
            f"{r['fee_drag_pct']:>16.2f}%"
        )
    print(f"{'='*110}")


if __name__ == "__main__":
    fee_rate = fee_rate_for(TICKER)
    data = load_data(TICKER, START, END)
    signal = signal_ma_crossover(data, fast=FAST, slow=SLOW)
    atr = compute_atr(data, ATR_PERIOD)

    all_results = []

    # baseline ไม่มี SL
    stats = run_backtest(data, signal, fee_rate, sl_mode="none", sl_param=None)
    all_results.append({"label": "ไม่มี SL (baseline)", "param": "-", **stats})

    # 1) Fixed SL grid ละเอียด
    for sl_pct in FIXED_SL_GRID:
        stats = run_backtest(data, signal, fee_rate, sl_mode="fixed", sl_param=sl_pct)
        all_results.append({"label": "Fixed SL", "param": f"{sl_pct}%", **stats})

    # 2) Trailing SL
    for trail_pct in TRAILING_SL_GRID:
        stats = run_backtest(data, signal, fee_rate, sl_mode="trailing", sl_param=trail_pct)
        all_results.append({"label": "Trailing SL", "param": f"{trail_pct}%", **stats})

    # 3) ATR-based SL
    for mult in ATR_MULTIPLIER_GRID:
        stats = run_backtest(data, signal, fee_rate, sl_mode="atr", sl_param=mult, atr=atr)
        all_results.append({"label": "ATR-based SL", "param": f"{mult}x ATR", **stats})

    print_report(all_results)
