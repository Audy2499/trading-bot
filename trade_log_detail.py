"""
แสดงรายละเอียดทุกไม้ที่เทรด (ไม่ใช่แค่สรุปผลรวม) — เข้าวันไหน ออกวันไหน กำไร/ขาดทุนกี่ %
ออกเพราะอะไร (สัญญาณกลับตัว / โดน SL / โดน TP) เพื่อดู "จังหวะ" ของระบบจริงๆ

รัน: python trade_log_detail.py
"""

from compare_strategies import START, END, INITIAL_CAPITAL, load_data, signal_ma_crossover
from fee_impact_analysis import fee_rate_for
from delta_sl_optimization import compute_atr, FAST, SLOW, ATR_PERIOD
from ticker_strategy_config import get_config
from watchlist import WATCHLIST

SLIPPAGE_PCT = 0.5

# Profit Lock: พอกำไรลอยถึง LOCK_TRIGGER_PCT% ขยับ SL ขึ้นมาล็อกกำไรขั้นต่ำ LOCK_PCT% ไว้
# (ล็อกครั้งเดียวแบบขั้นบันได ไม่ใช่ trailing ต่อเนื่องที่เคยทดสอบแล้วแย่กับ DELTA.BK)
USE_PROFIT_LOCK = False  # ปิดไว้: grid search (profit_lock_grid_search.py) พบว่าช่วยแค่ 1-7% และเสี่ยงตั้งค่าผิดง่าย
LOCK_TRIGGER_PCT = 15
LOCK_PCT = 5


def run_with_trade_log(df, in_position, fee_rate, atr, sl_mult, tp_pct, slippage_pct, use_profit_lock=False) -> list[dict]:
    trades = []
    shares = 0
    entry_price = None
    entry_date = None
    lock_active = False
    was_holding = False

    for date, row in df.iterrows():
        price, low, high = row["Close"], row["Low"], row["High"]
        want_hold = bool(in_position.loc[date])

        if shares > 0:
            atr_val = atr.loc[date]
            stop_price = entry_price - sl_mult * atr_val if atr_val == atr_val else None
            target_price = entry_price * (1 + tp_pct / 100) if tp_pct is not None else None

            if use_profit_lock:
                floating_gain_pct = (high - entry_price) / entry_price * 100
                if floating_gain_pct >= LOCK_TRIGGER_PCT:
                    lock_active = True
                if lock_active:
                    lock_stop = entry_price * (1 + LOCK_PCT / 100)
                    stop_price = max(stop_price, lock_stop) if stop_price is not None else lock_stop

            exit_price, exit_reason = None, None
            if stop_price is not None and low <= stop_price:
                exit_price = stop_price * (1 - slippage_pct / 100)
                exit_reason = "Profit Lock" if (use_profit_lock and lock_active and stop_price > entry_price) else "SL"
            elif target_price is not None and high >= target_price:
                exit_price = target_price * (1 - slippage_pct / 100)
                exit_reason = "TP"
            elif not want_hold and was_holding:
                exit_price = price * (1 - slippage_pct / 100)
                exit_reason = "สัญญาณกลับตัว"

            if exit_price is not None:
                pnl_pct = (exit_price - entry_price) / entry_price * 100
                trades.append({
                    "entry_date": entry_date, "exit_date": date,
                    "entry_price": entry_price, "exit_price": exit_price,
                    "pnl_pct": pnl_pct, "holding_days": (date - entry_date).days,
                    "exit_reason": exit_reason,
                })
                shares = 0
                was_holding = False
                lock_active = False
                continue

        if want_hold and not was_holding and shares == 0:
            entry_price = price * (1 + slippage_pct / 100)
            entry_date = date
            shares = 1  # แค่ track ว่าเปิด position ไม่ต้องคำนวณจำนวนหุ้นจริงสำหรับ log นี้
            lock_active = False

        was_holding = want_hold

    return trades


def summarize(trades: list[dict], years: float) -> dict:
    if not trades:
        return {"num_trades": 0}
    wins = [t for t in trades if t["pnl_pct"] > 0]
    losses = [t for t in trades if t["pnl_pct"] <= 0]
    return {
        "num_trades": len(trades),
        "trades_per_year": len(trades) / years,
        "win_rate_pct": len(wins) / len(trades) * 100,
        "avg_win_pct": sum(t["pnl_pct"] for t in wins) / len(wins) if wins else 0,
        "avg_loss_pct": sum(t["pnl_pct"] for t in losses) / len(losses) if losses else 0,
        "best_trade_pct": max(t["pnl_pct"] for t in trades),
        "worst_trade_pct": min(t["pnl_pct"] for t in trades),
        "avg_holding_days": sum(t["holding_days"] for t in trades) / len(trades),
    }


if __name__ == "__main__":
    for ticker in WATCHLIST:
        config = get_config(ticker)
        fee_rate = fee_rate_for(ticker)
        data = load_data(ticker, START, END)

        if len(data) < SLOW + 20:
            print(f"\n{ticker}: ข้ามเพราะข้อมูลไม่พอ ({len(data)} วัน)")
            continue

        signal = signal_ma_crossover(data, fast=FAST, slow=SLOW)
        atr = compute_atr(data, ATR_PERIOD)
        years = (data.index[-1] - data.index[0]).days / 365.25

        trades_before = run_with_trade_log(data, signal, fee_rate, atr, config["sl_atr_mult"], config["tp_pct"], SLIPPAGE_PCT, use_profit_lock=False)
        trades_after = run_with_trade_log(data, signal, fee_rate, atr, config["sl_atr_mult"], config["tp_pct"], SLIPPAGE_PCT, use_profit_lock=USE_PROFIT_LOCK)
        summary_before = summarize(trades_before, years)
        summary_after = summarize(trades_after, years)

        status = "validated" if config["validated"] else "default"
        print(f"\n{'='*100}")
        print(f"{ticker}  (SL {config['sl_atr_mult']}x ATR / TP {config['tp_pct']}%, {status})")
        print(f"{'='*100}")
        if summary_before["num_trades"] == 0:
            print("  ไม่มีการเทรดเลยในช่วงนี้")
            continue

        total_pnl_before = sum(t["pnl_pct"] for t in trades_before)
        total_pnl_after = sum(t["pnl_pct"] for t in trades_after)
        num_locked = sum(1 for t in trades_after if t["exit_reason"] == "Profit Lock")

        print(f"  {'':20s}{'เดิม (ไม่มี Profit Lock)':>28}{'มี Profit Lock ' + str(LOCK_TRIGGER_PCT) + '%->' + str(LOCK_PCT) + '%':>32}")
        print(f"  {'Win rate':20s}{summary_before['win_rate_pct']:>27.1f}%{summary_after['win_rate_pct']:>31.1f}%")
        print(f"  {'กำไรเฉลี่ยไม้ชนะ':20s}{summary_before['avg_win_pct']:>+27.2f}%{summary_after['avg_win_pct']:>+31.2f}%")
        print(f"  {'ขาดทุนเฉลี่ยไม้แพ้':20s}{summary_before['avg_loss_pct']:>+27.2f}%{summary_after['avg_loss_pct']:>+31.2f}%")
        print(f"  {'ผลรวม P&L ทุกไม้':20s}{total_pnl_before:>+27.2f}%{total_pnl_after:>+31.2f}%")
        print(f"  โดน Profit Lock ทำงาน: {num_locked} ครั้ง จาก {summary_after['num_trades']} ไม้")

        print(f"\n  ไม้ล่าสุด 8 รายการ (มี Profit Lock):")
        for t in trades_after[-8:]:
            print(
                f"    {t['entry_date'].date()} -> {t['exit_date'].date()}  "
                f"({t['holding_days']:>3d} วัน)  P&L {t['pnl_pct']:>+8.2f}%  ออกเพราะ: {t['exit_reason']}"
            )
