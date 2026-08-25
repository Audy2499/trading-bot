"""
รันเปรียบเทียบกลยุทธ์เดิม (compare_strategies.py) กับหุ้นเทคชั้นนำหลายตัว
เพื่อดูว่ากลยุทธ์ไหน "เสถียร" ข้ามหุ้น ไม่ใช่ดีแค่ตัวเดียว

รัน: python multi_ticker_compare.py
"""

import pandas as pd

from compare_strategies import (
    START,
    END,
    load_data,
    run_backtest,
    signal_ma_crossover,
    signal_rsi,
    signal_bollinger,
    signal_buy_and_hold,
)

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META"]

STRATEGIES = {
    "MA Crossover (20/50)": signal_ma_crossover,
    "RSI Mean Reversion": signal_rsi,
    "Bollinger Bands": signal_bollinger,
    "Buy & Hold": signal_buy_and_hold,
}


def run_all() -> pd.DataFrame:
    rows = []
    for ticker in TICKERS:
        data = load_data(ticker, START, END)
        for strat_name, signal_fn in STRATEGIES.items():
            signal = signal_fn(data)
            result = run_backtest(data, signal)
            rows.append({"ticker": ticker, "strategy": strat_name, **result})
    return pd.DataFrame(rows)


def print_per_ticker(df: pd.DataFrame) -> None:
    for ticker in TICKERS:
        sub = df[df["ticker"] == ticker].sort_values("return_pct", ascending=False)
        print(f"\n{ticker}")
        print("-" * 60)
        for _, r in sub.iterrows():
            print(
                f"  {r['strategy']:<22}{r['return_pct']:>+9.2f}%"
                f"   DD {r['max_drawdown_pct']:>7.2f}%"
                f"   เทรด {int(r['num_trades']):>3d}"
                f"   Win {r['win_rate_pct']:>5.1f}%"
            )


def print_summary(df: pd.DataFrame) -> None:
    print(f"\n{'='*70}")
    print(f"สรุปเฉลี่ยข้ามหุ้นเทค {len(TICKERS)} ตัว: {', '.join(TICKERS)}")
    print(f"{'='*70}")

    summary = (
        df.groupby("strategy")
        .agg(
            avg_return_pct=("return_pct", "mean"),
            avg_max_dd_pct=("max_drawdown_pct", "mean"),
            avg_trades=("num_trades", "mean"),
        )
        .sort_values("avg_return_pct", ascending=False)
    )

    beat_buy_hold = {}
    bh = df[df["strategy"] == "Buy & Hold"].set_index("ticker")["return_pct"]
    for strat in STRATEGIES:
        if strat == "Buy & Hold":
            beat_buy_hold[strat] = "-"
            continue
        strat_returns = df[df["strategy"] == strat].set_index("ticker")["return_pct"]
        wins = (strat_returns > bh).sum()
        beat_buy_hold[strat] = f"{wins}/{len(TICKERS)}"

    header = f"{'กลยุทธ์':<22}{'ผลตอบแทนเฉลี่ย':>16}{'Max DD เฉลี่ย':>15}{'ชนะ Buy&Hold':>15}"
    print(header)
    print("-" * len(header))
    for strat, row in summary.iterrows():
        print(
            f"{strat:<22}{row['avg_return_pct']:>+15.2f}%"
            f"{row['avg_max_dd_pct']:>14.2f}%"
            f"{beat_buy_hold[strat]:>15}"
        )


if __name__ == "__main__":
    df = run_all()
    print_per_ticker(df)
    print_summary(df)
