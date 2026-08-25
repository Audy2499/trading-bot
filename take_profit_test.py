"""
เพิ่ม Take-Profit (TP) เข้าไปคู่กับ SL ที่ทนทานที่สุดที่เจอ (ATR-based 2.0x)
ทดสอบว่าการ "ล็อกกำไร" ก่อนถึงเวลาช่วยหรือทำร้ายผลตอบแทน โดยเฉพาะเมื่อคิด slippage จริงด้วย
(เพราะบทเรียนก่อนหน้า: backtest ไม่มี cost ไว้ใจไม่ได้)

กติกาแต่ละวันที่ถือ position:
- เช็ค SL ก่อนเสมอ (สมมติกรณีเลวร้ายสุด ถ้าทั้ง SL และ TP โดนในวันเดียวกัน)
- ถ้าไม่โดน SL ค่อยเช็ค TP (High แตะจุดเป้าหมายกำไรไหม)

รัน: python take_profit_test.py
"""

from compare_strategies import START, END, INITIAL_CAPITAL, load_data, signal_ma_crossover
from fee_impact_analysis import fee_rate_for
from delta_sl_optimization import compute_atr, FAST, SLOW, ATR_PERIOD

TICKER = "DELTA.BK"
SL_ATR_MULTIPLIER = 3.0  # อัปเกรดจาก 2.0x: ผลตอบแทนใกล้เคียงกันแต่โดน SL น้อยกว่ามาก (14 -> 2 ครั้ง ใน 6 ปี) จาก sl_tp_grid_search.py
TP_LEVELS_PCT = [None, 20, 30, 50, 75, 100, 150]  # None = ไม่มี TP (baseline)
SLIPPAGE_LEVELS_PCT = [0.5, 1.0]  # ระดับที่สมจริงจากการทดสอบก่อนหน้า


def run_backtest_with_sl_tp(df, in_position, fee_rate, atr, sl_mult, tp_pct, slippage_pct) -> dict:
    cash = INITIAL_CAPITAL
    shares = 0
    entry_price = None
    buy_date = None
    holding_days = []
    total_commission = 0.0
    num_round_trips = 0
    num_sl_hits = 0
    num_tp_hits = 0
    was_holding = False

    for date, row in df.iterrows():
        price, low, high = row["Close"], row["Low"], row["High"]
        want_hold = bool(in_position.loc[date])

        if shares > 0:
            atr_val = atr.loc[date]
            stop_price = entry_price - sl_mult * atr_val if atr_val == atr_val else None
            target_price = entry_price * (1 + tp_pct / 100) if tp_pct is not None else None

            exited = False
            if stop_price is not None and low <= stop_price:
                exec_price = stop_price * (1 - slippage_pct / 100)
                num_sl_hits += 1
                exited = True
            elif target_price is not None and high >= target_price:
                exec_price = target_price * (1 - slippage_pct / 100)  # ขายตอน TP ก็ยังมี slippage
                num_tp_hits += 1
                exited = True

            if exited:
                proceeds = shares * exec_price
                commission = proceeds * fee_rate
                cash += proceeds - commission
                total_commission += commission
                holding_days.append((date - buy_date).days)
                num_round_trips += 1
                shares = 0
                was_holding = False
                continue

        if want_hold and not was_holding and shares == 0:
            exec_price = price * (1 + slippage_pct / 100)
            shares = int(cash // (exec_price * (1 + fee_rate)))
            cost = shares * exec_price
            commission = cost * fee_rate
            cash -= cost + commission
            total_commission += commission
            entry_price = exec_price
            buy_date = date

        elif not want_hold and was_holding and shares > 0:
            exec_price = price * (1 - slippage_pct / 100)
            proceeds = shares * exec_price
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
    avg_holding_days = sum(holding_days) / len(holding_days) if holding_days else 0

    return {
        "net_return_pct": net_return_pct,
        "num_round_trips": num_round_trips,
        "num_sl_hits": num_sl_hits,
        "num_tp_hits": num_tp_hits,
        "avg_holding_days": avg_holding_days,
    }


def print_report(results: list[dict]) -> None:
    for slippage in SLIPPAGE_LEVELS_PCT:
        print(f"\n{'='*105}")
        print(f"Slippage {slippage}% — DELTA.BK, SL = ATR-based {SL_ATR_MULTIPLIER}x, TP หลายระดับ")
        print(f"{'='*105}")
        header = f"{'TP':<10}{'Net Return':>13}{'เทรดทั้งหมด':>13}{'โดน SL':>9}{'โดน TP':>9}{'ถือเฉลี่ย(วัน)':>15}"
        print(header)
        print("-" * 105)
        subset = [r for r in results if r["slippage_pct"] == slippage]
        for r in subset:
            tp_label = f"{r['tp_pct']}%" if r["tp_pct"] is not None else "ไม่มี"
            print(
                f"{tp_label:<10}"
                f"{r['net_return_pct']:>+12.2f}%"
                f"{r['num_round_trips']:>13d}"
                f"{r['num_sl_hits']:>9d}"
                f"{r['num_tp_hits']:>9d}"
                f"{r['avg_holding_days']:>14.1f} "
            )
        print(f"{'='*105}")


if __name__ == "__main__":
    fee_rate = fee_rate_for(TICKER)
    data = load_data(TICKER, START, END)
    signal = signal_ma_crossover(data, fast=FAST, slow=SLOW)
    atr = compute_atr(data, ATR_PERIOD)

    results = []
    for slippage in SLIPPAGE_LEVELS_PCT:
        for tp_pct in TP_LEVELS_PCT:
            stats = run_backtest_with_sl_tp(data, signal, fee_rate, atr, SL_ATR_MULTIPLIER, tp_pct, slippage)
            results.append({"tp_pct": tp_pct, "slippage_pct": slippage, **stats})

    print_report(results)
