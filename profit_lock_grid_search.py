"""
Grid search หา Trigger/Lock level ของ Profit Lock ที่ "ไม่ทำร้าย" ผลตอบแทน (เทียบกับไม่มี Lock เลย)
ใช้ engine แบบ compounded equity เดียวกับที่ใช้ประเมิน SL/TP มาตลอด (net_return_pct)
ไม่ใช่แค่ผลรวม % แบบง่ายที่ trade_log_detail.py ใช้

รัน: python profit_lock_grid_search.py
"""

from compare_strategies import START, END, INITIAL_CAPITAL, load_data, signal_ma_crossover
from fee_impact_analysis import fee_rate_for
from delta_sl_optimization import compute_atr, FAST, SLOW, ATR_PERIOD
from ticker_strategy_config import get_config
from watchlist import WATCHLIST

SLIPPAGE_PCT = 0.5
TRIGGER_GRID = [20, 30, 40, 50, 75, 100, 150]
LOCK_GRID = [5, 10, 15, 20, 30]


def run_backtest_with_lock(df, in_position, fee_rate, atr, sl_mult, tp_pct, slippage_pct, trigger_pct=None, lock_pct=None) -> dict:
    cash = INITIAL_CAPITAL
    shares = 0
    entry_price = None
    buy_date = None
    lock_active = False
    holding_days = []
    total_commission = 0.0
    num_round_trips = 0
    was_holding = False

    for date, row in df.iterrows():
        price, low, high = row["Close"], row["Low"], row["High"]
        want_hold = bool(in_position.loc[date])

        if shares > 0:
            atr_val = atr.loc[date]
            stop_price = entry_price - sl_mult * atr_val if atr_val == atr_val else None
            target_price = entry_price * (1 + tp_pct / 100) if tp_pct is not None else None

            if trigger_pct is not None:
                floating_gain_pct = (high - entry_price) / entry_price * 100
                if floating_gain_pct >= trigger_pct:
                    lock_active = True
                if lock_active:
                    lock_stop = entry_price * (1 + lock_pct / 100)
                    lock_stop = min(lock_stop, high)  # กันไม่ให้ "ขาย" ในราคาที่สูงกว่าราคาสูงสุดที่เกิดขึ้นจริงวันนั้น
                    stop_price = max(stop_price, lock_stop) if stop_price is not None else lock_stop

            exit_price = None
            if stop_price is not None and low <= stop_price:
                exit_price = stop_price * (1 - slippage_pct / 100)
            elif target_price is not None and high >= target_price:
                exit_price = target_price * (1 - slippage_pct / 100)
            elif not want_hold and was_holding:
                exit_price = price * (1 - slippage_pct / 100)

            if exit_price is not None:
                proceeds = shares * exit_price
                commission = proceeds * fee_rate
                cash += proceeds - commission
                total_commission += commission
                holding_days.append((date - buy_date).days)
                num_round_trips += 1
                shares = 0
                was_holding = False
                lock_active = False
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
            lock_active = False

        was_holding = want_hold

    final_price = df["Close"].iloc[-1]
    final_equity_net = cash + shares * final_price
    net_return_pct = (final_equity_net - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100

    return {"net_return_pct": net_return_pct, "num_round_trips": num_round_trips}


if __name__ == "__main__":
    tickers_to_test = [t for t in WATCHLIST]

    for ticker in tickers_to_test:
        config = get_config(ticker)
        fee_rate = fee_rate_for(ticker)
        data = load_data(ticker, START, END)

        if len(data) < SLOW + 20:
            print(f"\n{ticker}: ข้าม (ข้อมูลไม่พอ)")
            continue

        signal = signal_ma_crossover(data, fast=FAST, slow=SLOW)
        atr = compute_atr(data, ATR_PERIOD)

        baseline = run_backtest_with_lock(
            data, signal, fee_rate, atr, config["sl_atr_mult"], config["tp_pct"], SLIPPAGE_PCT,
            trigger_pct=None, lock_pct=None,
        )

        results = []
        for trigger_pct in TRIGGER_GRID:
            for lock_pct in LOCK_GRID:
                if lock_pct > trigger_pct:
                    continue  # lock_pct ต้อง <= trigger_pct เสมอ (ล็อกได้แค่กำไรที่ "เกิดขึ้นจริงแล้ว" ไม่ใช่ทายล่วงหน้า)
                stats = run_backtest_with_lock(
                    data, signal, fee_rate, atr, config["sl_atr_mult"], config["tp_pct"], SLIPPAGE_PCT,
                    trigger_pct=trigger_pct, lock_pct=lock_pct,
                )
                results.append({"trigger": trigger_pct, "lock": lock_pct, **stats})

        results.sort(key=lambda x: x["net_return_pct"], reverse=True)
        not_worse = [r for r in results if r["net_return_pct"] >= baseline["net_return_pct"]]

        print(f"\n{'='*90}")
        print(f"{ticker}  — Baseline (ไม่มี Lock): {baseline['net_return_pct']:+.2f}%")
        print(f"{'='*90}")
        if not_worse:
            print(f"  พบ {len(not_worse)} combo ที่ไม่แย่กว่า baseline — Top 3:")
            for r in not_worse[:3]:
                print(f"    Trigger {r['trigger']:>3d}% -> Lock {r['lock']:>2d}%   Net Return: {r['net_return_pct']:>+10.2f}%")
        else:
            print(f"  ❌ ไม่มี combo ไหนดีเท่าหรือดีกว่า baseline เลย — ตัวที่แย่น้อยที่สุด:")
            best_bad = results[0]
            print(f"    Trigger {best_bad['trigger']:>3d}% -> Lock {best_bad['lock']:>2d}%   Net Return: {best_bad['net_return_pct']:>+10.2f}%  (ยังแย่กว่า baseline {baseline['net_return_pct'] - best_bad['net_return_pct']:.2f}pp)")
