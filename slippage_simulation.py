"""
จำลอง slippage (ราคาที่ได้จริงแย่กว่าราคาทฤษฎี) ใส่เข้าไปในทุกคำสั่งซื้อ/ขาย
เพื่อดูว่า edge ของ Fixed SL 1% กับ ATR-based 2.0x ที่เจอก่อนหน้า ยังเหลือพอไหม
เมื่อคิดต้นทุนที่สมจริงกว่าการจำลองแบบ "ขายได้ราคาตรงจุดเป๊ะ"

Slippage คือส่วนต่างระหว่างราคาที่ตั้งใจซื้อ/ขาย กับราคาที่ได้จริง เกิดจาก spread,
คำสั่งจำนวนมากกระทบราคา, หรือราคา gap ข้ามจุด stop ไปเลย — ยิ่งหุ้นผันผวนสูงและ
เทรดถี่ ยิ่งโดนกัดกินหนัก

รัน: python slippage_simulation.py
"""

from compare_strategies import START, END, INITIAL_CAPITAL, load_data, signal_ma_crossover
from fee_impact_analysis import fee_rate_for
from delta_sl_optimization import compute_atr, FAST, SLOW, ATR_PERIOD

TICKER = "DELTA.BK"
SLIPPAGE_LEVELS_PCT = [0.0, 0.1, 0.3, 0.5, 1.0, 2.0]

CANDIDATES = [
    {"label": "Fixed SL 1%", "sl_mode": "fixed", "sl_param": 1},
    {"label": "ATR-based 2.0x", "sl_mode": "atr", "sl_param": 2.0},
]


def run_backtest_with_slippage(df, in_position, fee_rate, sl_mode, sl_param, atr, slippage_pct) -> dict:
    cash = INITIAL_CAPITAL
    shares = 0
    entry_price = None
    buy_date = None
    holding_days = []
    total_commission = 0.0
    total_slippage_cost = 0.0
    num_round_trips = 0
    num_sl_hits = 0
    was_holding = False

    for date, row in df.iterrows():
        price = row["Close"]
        low = row["Low"]
        want_hold = bool(in_position.loc[date])

        if shares > 0:
            if sl_mode == "fixed":
                stop_price = entry_price * (1 - sl_param / 100)
            elif sl_mode == "atr":
                stop_price = entry_price - sl_param * atr.loc[date] if atr is not None and (atr.loc[date] == atr.loc[date]) else None
            else:
                stop_price = None

            if stop_price is not None and low <= stop_price:
                exec_price = stop_price * (1 - slippage_pct / 100)  # ขายได้แย่กว่าจุด SL ทฤษฎี
                proceeds = shares * exec_price
                commission = proceeds * fee_rate
                cash += proceeds - commission
                total_commission += commission
                total_slippage_cost += shares * (stop_price - exec_price)
                holding_days.append((date - buy_date).days)
                num_round_trips += 1
                num_sl_hits += 1
                shares = 0
                was_holding = False
                continue

        if want_hold and not was_holding and shares == 0:
            exec_price = price * (1 + slippage_pct / 100)  # ซื้อได้แพงกว่าราคาปิดทฤษฎี
            shares = int(cash // (exec_price * (1 + fee_rate)))
            cost = shares * exec_price
            commission = cost * fee_rate
            cash -= cost + commission
            total_commission += commission
            total_slippage_cost += shares * (exec_price - price)
            entry_price = exec_price
            buy_date = date

        elif not want_hold and was_holding and shares > 0:
            exec_price = price * (1 - slippage_pct / 100)  # ขายได้ถูกกว่าราคาปิดทฤษฎี
            proceeds = shares * exec_price
            commission = proceeds * fee_rate
            cash += proceeds - commission
            total_commission += commission
            total_slippage_cost += shares * (price - exec_price)
            holding_days.append((date - buy_date).days)
            num_round_trips += 1
            shares = 0

        was_holding = want_hold

    final_price = df["Close"].iloc[-1]
    final_equity_net = cash + shares * final_price
    net_return_pct = (final_equity_net - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    slippage_drag_pct = total_slippage_cost / INITIAL_CAPITAL * 100
    fee_drag_pct = total_commission / INITIAL_CAPITAL * 100

    return {
        "net_return_pct": net_return_pct,
        "num_round_trips": num_round_trips,
        "num_sl_hits": num_sl_hits,
        "fee_drag_pct": fee_drag_pct,
        "slippage_drag_pct": slippage_drag_pct,
    }


def print_report(results: list[dict]) -> None:
    print(f"\n{'='*105}")
    print(f"ผลกระทบของ Slippage ต่อ Net Return — DELTA.BK")
    print(f"{'='*105}")
    header = f"{'กลยุทธ์':<18}{'Slippage':>10}{'Net Return':>13}{'เทรด':>7}{'ค่าธรรมเนียมกิน':>17}{'Slippage กิน':>15}"
    print(header)
    print("-" * 105)
    for r in results:
        print(
            f"{r['label']:<18}{r['slippage_pct']:>9.1f}%"
            f"{r['net_return_pct']:>+12.2f}%"
            f"{r['num_round_trips']:>7d}"
            f"{r['fee_drag_pct']:>16.2f}%"
            f"{r['slippage_drag_pct']:>14.2f}%"
        )
    print(f"{'='*105}")


if __name__ == "__main__":
    fee_rate = fee_rate_for(TICKER)
    data = load_data(TICKER, START, END)
    signal = signal_ma_crossover(data, fast=FAST, slow=SLOW)
    atr = compute_atr(data, ATR_PERIOD)

    results = []
    for candidate in CANDIDATES:
        for slip in SLIPPAGE_LEVELS_PCT:
            stats = run_backtest_with_slippage(
                data, signal, fee_rate,
                sl_mode=candidate["sl_mode"], sl_param=candidate["sl_param"],
                atr=atr, slippage_pct=slip,
            )
            results.append({"label": candidate["label"], "slippage_pct": slip, **stats})

    print_report(results)
