"""
Backtest ง่ายๆ: กลยุทธ์ Moving Average Crossover
- MA เร็ว ตัดขึ้นเหนือ MA ช้า -> ซื้อ (all-in ด้วยเงินสดที่มี)
- MA เร็ว ตัดลงต่ำกว่า MA ช้า -> ขายทั้งหมด
ไม่มี margin, ไม่มีค่าคอมมิชชัน/สลิปเพจ (ของจริงต้องหักด้วย)

รัน: python backtest_ma_strategy.py
"""

import yfinance as yf
import pandas as pd

TICKER = "AAPL"
START = "2020-01-01"
END = "2026-08-01"
FAST_MA = 20
SLOW_MA = 50
INITIAL_CAPITAL = 100_000.0


def load_data(ticker: str, start: str, end: str) -> pd.DataFrame:
    df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    df.columns = df.columns.get_level_values(0)
    df["fast_ma"] = df["Close"].rolling(FAST_MA).mean()
    df["slow_ma"] = df["Close"].rolling(SLOW_MA).mean()
    return df.dropna()


def run_backtest(df: pd.DataFrame) -> dict:
    cash = INITIAL_CAPITAL
    shares = 0
    trades = []
    equity_curve = []

    was_above = df["fast_ma"].iloc[0] > df["slow_ma"].iloc[0]

    for date, row in df.iterrows():
        is_above = row["fast_ma"] > row["slow_ma"]
        price = row["Close"]

        if is_above and not was_above and shares == 0:
            shares = int(cash // price)
            cash -= shares * price
            trades.append({"date": date, "side": "BUY", "price": price, "shares": shares})

        elif not is_above and was_above and shares > 0:
            cash += shares * price
            trades.append({"date": date, "side": "SELL", "price": price, "shares": shares})
            shares = 0

        was_above = is_above
        equity_curve.append(cash + shares * price)

    final_price = df["Close"].iloc[-1]
    final_equity = cash + shares * final_price

    equity_series = pd.Series(equity_curve, index=df.index)
    running_max = equity_series.cummax()
    drawdown = (equity_series - running_max) / running_max
    max_drawdown = drawdown.min()

    sells = [t for t in trades if t["side"] == "SELL"]
    buys = [t for t in trades if t["side"] == "BUY"]
    wins = sum(
        1 for b, s in zip(buys, sells) if s["price"] > b["price"]
    )
    win_rate = wins / len(sells) if sells else 0.0

    buy_hold_return = (final_price - df["Close"].iloc[0]) / df["Close"].iloc[0]
    strategy_return = (final_equity - INITIAL_CAPITAL) / INITIAL_CAPITAL

    return {
        "trades": trades,
        "num_trades": len(trades),
        "win_rate": win_rate,
        "final_equity": final_equity,
        "strategy_return_pct": strategy_return * 100,
        "buy_hold_return_pct": buy_hold_return * 100,
        "max_drawdown_pct": max_drawdown * 100,
    }


def print_report(ticker: str, result: dict) -> None:
    print(f"\n{'='*50}")
    print(f"Backtest: {ticker}  |  MA{FAST_MA}/MA{SLOW_MA} Crossover")
    print(f"{'='*50}")
    print(f"เงินทุนเริ่มต้น:      {INITIAL_CAPITAL:,.2f}")
    print(f"เงินทุนสุดท้าย:       {result['final_equity']:,.2f}")
    print(f"ผลตอบแทนกลยุทธ์:      {result['strategy_return_pct']:+.2f}%")
    print(f"ผลตอบแทน Buy & Hold:  {result['buy_hold_return_pct']:+.2f}%")
    print(f"Max Drawdown:         {result['max_drawdown_pct']:.2f}%")
    print(f"จำนวนคำสั่ง:          {result['num_trades']}")
    print(f"Win rate:             {result['win_rate']*100:.1f}%")
    print(f"{'='*50}")
    print("\nรายการคำสั่งล่าสุด 10 รายการ:")
    for t in result["trades"][-10:]:
        print(f"  {t['date'].date()}  {t['side']:4s}  ราคา {t['price']:.2f}  จำนวน {t['shares']}")


if __name__ == "__main__":
    data = load_data(TICKER, START, END)
    result = run_backtest(data)
    print_report(TICKER, result)
