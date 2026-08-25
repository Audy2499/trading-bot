"""
ตัดสินใจว่าสัญญาณที่ได้จาก combine_signal() ควร "ยิงอัตโนมัติ" หรือ "รอคนยืนยันก่อน"
ปรับ EXECUTION_MODE ได้ตามบริบท โดยไม่ต้องแก้โค้ดส่วนอื่น

โหมดที่มี:
- "full_auto"  : ยิงอัตโนมัติทุกครั้งที่สัญญาณไม่ขัดแย้งกัน (เร็วสุด เสี่ยงสุด)
- "semi_auto"  : ทุกสัญญาณต้องรอคนกดยืนยันก่อนเสมอ (ช้าสุด ปลอดภัยสุด)
- "adaptive"   : ยิงอัตโนมัติเฉพาะสัญญาณที่ "มั่นใจสูง" เท่านั้น
                 ส่วนสัญญาณที่ไม่มั่นใจ/ขัดแย้งกัน ต้องรอคนยืนยัน (ค่าเริ่มต้นที่แนะนำ)
"""

EXECUTION_MODE = "adaptive"  # เปลี่ยนได้ตามบริบท: "full_auto" | "semi_auto" | "adaptive"

# ใช้เฉพาะตอน EXECUTION_MODE = "adaptive"
# สัญญาณจะถือว่า "มั่นใจสูง" ก็ต่อเมื่อ |avg_sentiment| >= threshold นี้ และ technical ไม่ขัดแย้งกับข่าว
CONFIDENCE_THRESHOLD = 0.30


def decide(combined: dict, mode: str = None) -> dict:
    """
    รับผลจาก combine_signal() แล้วบอกว่า "auto_execute" (True/False)
    พร้อมเหตุผลประกอบ ไว้ log หรือส่งแจ้งเตือน
    """
    mode = mode or EXECUTION_MODE
    is_conflicted = combined["conflicted"]
    confidence = abs(combined["avg_sentiment"])

    if mode == "full_auto":
        auto = not is_conflicted
        reason = "full_auto: ยิงทันทีถ้าไม่ขัดแย้งกัน"

    elif mode == "semi_auto":
        auto = False
        reason = "semi_auto: ทุกสัญญาณต้องรอคนยืนยันเสมอ"

    elif mode == "adaptive":
        auto = (not is_conflicted) and (confidence >= CONFIDENCE_THRESHOLD)
        if is_conflicted:
            reason = f"adaptive: สัญญาณขัดแย้งกัน -> รอคนยืนยัน"
        elif confidence < CONFIDENCE_THRESHOLD:
            reason = f"adaptive: มั่นใจแค่ {confidence:.2f} (ต่ำกว่า {CONFIDENCE_THRESHOLD}) -> รอคนยืนยัน"
        else:
            reason = f"adaptive: มั่นใจ {confidence:.2f} (>= {CONFIDENCE_THRESHOLD}) -> ยิงอัตโนมัติ"

    else:
        raise ValueError(f"ไม่รู้จักโหมด: {mode}")

    return {
        "auto_execute": auto,
        "mode": mode,
        "reason": reason,
        "action": combined["action"],
    }


if __name__ == "__main__":
    # ตัวอย่างสัญญาณสมมติ ไว้ทดสอบ logic โดยไม่ต้องรอข้อมูลจริง
    examples = [
        {"avg_sentiment": 0.45, "technical_bullish": True, "action": "เข้า/ถือ (technical + ข่าวไม่ขัดแย้งกัน)", "conflicted": False},
        {"avg_sentiment": 0.05, "technical_bullish": True, "action": "เข้า/ถือ (technical + ข่าวไม่ขัดแย้งกัน)", "conflicted": False},
        {"avg_sentiment": 0.80, "technical_bullish": False, "action": "สัญญาณขัดแย้งกัน — ควรระวัง ไม่ควรเข้าเต็มไม้", "conflicted": True},
    ]

    for mode in ["full_auto", "semi_auto", "adaptive"]:
        print(f"\n=== โหมด: {mode} ===")
        for ex in examples:
            result = decide(ex, mode=mode)
            print(f"  action={ex['action'][:35]:<35} -> auto_execute={result['auto_execute']:<5} | {result['reason']}")
