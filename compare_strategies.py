"""
เปรียบเทียบหลายกลยุทธ์บน ticker เดียวกัน:
- MA Crossover      (ตามแนวโน้ม)
- RSI Mean Reversion (ซื้อตอนขายมากเกินไป / ขายตอนซื้อมากเกินไป)
- Bollinger Bands    (ซื้อตอนราคาหลุดกรอบล่าง / ขายตอนกลับสู่เส้นกลาง)
- Buy & Hold          (baseline เทียบ)

ไม่มี margin, ไม่มีค่าคอมมิชชัน/สลิปเพจ (ของจริงต้องหักด้วย)

รัน: python compare_strategies.py
"""

import yfinance as yf
import pandas as pd

TICKER = "AAPL"
START = "2020-01-01"
END = "2026-08-01"
INITIAL_CAPITAL = 100_000.0


def load_data(ticker: str, start: str, end: str) -> pd.DataFrame:
    df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    df.columns = df.columns.get_level_values(0)
    return df


# ---------- ตัวสร้างสัญญาณของแต่ละกลยุทธ์ ----------
# แต่ละฟังก์ชันคืนค่า pd.Series[bool] บอกว่า "ควรถือหุ้นอยู่ไหม" ในแต่ละวัน

def signal_ma_crossover(df: pd.DataFrame, fast=20, slow=50) -> pd.Series:
    fast_ma = df["Close"].rolling(fast).mean()
    slow_ma = df["Close"].rolling(slow).mean()
    return (fast_ma > slow_ma).fillna(False)


def signal_rsi(df: pd.DataFrame, period=14, lower=30, upper=70) -> pd.Series:
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    in_position = pd.Series(False, index=df.index)
    holding = False
    for date in df.index:
        r = rsi.loc[date]
        if pd.notna(r):
            if not holding and r < lower:
                holding = True
            elif holding and r > upper:
                holding = False
        in_position.loc[date] = holding
    return in_position


def signal_bollinger(df: pd.DataFrame, window=20, num_std=2) -> pd.Series:
    mid = df["Close"].rolling(window).mean()
    std = df["Close"].rolling(window).std()
    lower_band = mid - num_std * std
    upper_band = mid + num_std * std

    in_position = pd.Series(False, index=df.index)
    holding = False
    for date in df.index:
        price = df["Close"].loc[date]
        lo, hi = lower_band.loc[date], upper_band.loc[date]
        if pd.notna(lo):
            if not holding and price < lo:
                holding = True
            elif holding and price > hi:
                holding = False
        in_position.loc[date] = holding
    return in_position


def signal_buy_and_hold(df: pd.DataFrame) -> pd.Series:
    return pd.Series(True, index=df.index)


# ---------- Backtest engine (ใช้ร่วมกันทุกกลยุทธ์) ----------

def run_backtest(df: pd.DataFrame, in_position: pd.Series) -> dict:
    cash = INITIAL_CAPITAL
    shares = 0
    trades = []
    equity_curve = []
    was_holding = False

    for date, row in df.iterrows():
        price = row["Close"]
        want_hold = bool(in_position.loc[date])

        if want_hold and not was_holding and shares == 0:
            shares = int(cash // price)
            cash -= shares * price
            trades.append({"date": date, "side": "BUY", "price": price})
        elif not want_hold and was_holding and shares > 0:
            cash += shares * price
            trades.append({"date": date, "side": "SELL", "price": price})
            shares = 0

        was_holding = want_hold
        equity_curve.append(cash + shares * price)

    final_price = df["Close"].iloc[-1]
    final_equity = cash + shares * final_price

    equity_series = pd.Series(equity_curve, index=df.index)
    running_max = equity_series.cummax()
    drawdown = (equity_series - running_max) / running_max
    max_drawdown = drawdown.min()

    sells = [t for t in trades if t["side"] == "SELL"]
    buys = [t for t in trades if t["side"] == "BUY"]
    wins = sum(1 for b, s in zip(buys, sells) if s["price"] > b["price"])
    win_rate = wins / len(sells) if sells else 0.0

    return {
        "final_equity": final_equity,
        "return_pct": (final_equity - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100,
        "max_drawdown_pct": max_drawdown * 100,
        "num_trades": len(trades),
        "win_rate_pct": win_rate * 100,
    }


def print_comparison(ticker: str, results: dict) -> None:
    print(f"\nเปรียบเทียบกลยุทธ์ — {ticker} ({START} ถึง {END})\n")
    header = f"{'กลยุทธ์':<20}{'ผลตอบแทน':>12}{'Max DD':>10}{'จำนวนคำสั่ง':>14}{'Win rate':>10}"
    print(header)
    print("-" * len(header))
    for name, r in sorted(results.items(), key=lambda kv: kv[1]["return_pct"], reverse=True):
        print(
            f"{name:<20}"
            f"{r['return_pct']:>+11.2f}%"
            f"{r['max_drawdown_pct']:>9.2f}%"
            f"{r['num_trades']:>14d}"
            f"{r['win_rate_pct']:>9.1f}%"
        )


if __name__ == "__main__":
    data = load_data(TICKER, START, END)

    strategies = {
        "MA Crossover (20/50)": signal_ma_crossover(data),
        "RSI Mean Reversion": signal_rsi(data),
        "Bollinger Bands": signal_bollinger(data),
        "Buy & Hold": signal_buy_and_hold(data),
    }

    results = {name: run_backtest(data, sig) for name, sig in strategies.items()}
    print_comparison(TICKER, results)
