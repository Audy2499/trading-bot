"""
Config กลยุทธ์ (SL/TP) แยกรายตัวหุ้น — แต่ละตัว "นิสัย" ไม่เหมือนกัน จึงไม่ควรใช้ค่าเดียวกันทั้งหมด
ตัวที่ยังไม่ผ่าน walk-forward validation จะ fallback ไปใช้ DEFAULT_CONFIG โดยอัตโนมัติ
พร้อม flag `validated: False` เตือนว่ายังไม่ผ่านการทดสอบเต็มรูปแบบ

หมายเหตุ: RSI entry filter ถูกตัดออกแล้ว (walk-forward ให้สัญญาณผสม ไม่น่าเชื่อถือพอ)
กลับไปใช้ entry แบบเข้าทันทีที่ MA ตัดขึ้น (baseline) สำหรับทุกตัว
"""

STRATEGY_CONFIG = {
    "DELTA.BK": {"sl_atr_mult": 3.0, "tp_pct": 100, "validated": True,
                 "note": "ผ่าน backtest + walk-forward (SL/TP) + slippage stress test ครบ"},
    "PLTR": {"sl_atr_mult": 1.0, "tp_pct": 75, "validated": True,
             "note": "ผ่าน walk-forward validation"},
    "TRUE.BK": {"sl_atr_mult": 1.5, "tp_pct": 75, "validated": True,
                "note": "ผ่าน walk-forward validation"},
    "NVDA": {"sl_atr_mult": 1.5, "tp_pct": 50, "validated": True,
             "note": "ผ่าน walk-forward validation (TRAIN +282%, TEST +42%)"},
}

# ใช้กับตัวที่ยังไม่เคยทดสอบเฉพาะทาง — ค่ากลางๆ ที่ไม่สุดโต่งไปทางไหน
DEFAULT_CONFIG = {"sl_atr_mult": 2.0, "tp_pct": 100, "validated": False,
                   "note": "ยังไม่ผ่าน walk-forward validation เฉพาะตัว ใช้ค่า default ไปก่อน"}


def get_config(ticker: str) -> dict:
    config = STRATEGY_CONFIG.get(ticker, DEFAULT_CONFIG).copy()
    config["ticker"] = ticker
    return config


if __name__ == "__main__":
    from watchlist import WATCHLIST

    print(f"\n{'='*90}")
    print("Config รายตัวหุ้นในปัจจุบัน")
    print(f"{'='*90}")
    header = f"{'Ticker':<10}{'SL(ATR)':>9}{'TP':>6}{'Validated':>11}   หมายเหตุ"
    print(header)
    print("-" * 90)
    for ticker in WATCHLIST:
        c = get_config(ticker)
        status = "✅" if c["validated"] else "⚠️ "
        print(f"{ticker:<10}{c['sl_atr_mult']:>8.1f}x{c['tp_pct']:>5d}%{status:>11}   {c['note']}")
    print(f"{'='*90}")
