"""
Watchlist ส่วนตัว — ใช้ ticker ตามนี้ในสคริปต์อื่นๆ แทนการพิมพ์แยกทีละไฟล์
"""

WATCHLIST = {
    "SPCX": "Space Exploration Technologies Corp (SpaceX) — เทรดได้จริงบน Webull TH ยืนยันแล้ว",
    "TISCO.BK": "TISCO Financial Group (หุ้นไทย ต้องมี .BK ต่อท้ายเสมอ)",
    "DELTA.BK": "Delta Electronics Thailand (หุ้นไทย ต้องมี .BK ต่อท้ายเสมอ) — ผ่าน walk-forward validation",
    "NVDA": "Nvidia — ผ่าน walk-forward validation (SL 1.5x ATR, TP 50%)",
    "PLTR": "Palantir — ผ่าน walk-forward validation (SL 1.0x ATR, TP 75%)",
    "TRUE.BK": "True Corporation (หุ้นไทย) — ผ่าน walk-forward validation (SL 1.5x ATR, TP 75%)",
}

# ตัวที่พิจารณาแล้วแต่ไม่ผ่านเกณฑ์ — เก็บไว้เตือนตัวเองไม่ให้เพิ่มกลับเข้าไปโดยไม่เช็คซ้ำ
REJECTED = {
    "AFRM": "ตกรอบ walk-forward validation — TRAIN ดูดีมาก (+364%) แต่ TEST ขาดทุน (-30%), แม้หา best config ใน TEST เองก็ยังขาดทุน แปลว่าไม่มี edge จริง",
    "TSLA": "ตกรอบ walk-forward validation — TRAIN +1106% แต่ TEST -20.19%, best config ใน TEST เองก็ยัง -20.19% เท่าเดิม ไม่มี config ไหนใช้ได้เลยในช่วงนี้",
    "MSFT": "ตกรอบ walk-forward validation — ติดลบสม่ำเสมอทั้ง TRAIN (-16.31%) และ TEST (-24.72%) กลยุทธ์ MA(5/15)+SL/TP ไม่เข้ากับหุ้นนี้",
    "META": "ตัดออก — ผลคาบเส้น (TRAIN -6%, TEST +7%) ไม่มี edge ชัดเจนพอจะเชื่อถือ พี่ตัดสินใจตัดออกเพื่อความชัดเจน",
    "GOOGL": "ตัดออก — ผลคาบเส้น (TRAIN -2%, TEST +47%) TRAIN แทบเสมอตัว สงสัยว่า TEST เป็นแค่ noise พี่ตัดสินใจตัดออกเพื่อความชัดเจน",
}

# ตัวที่รอข้อมูลเพิ่มก่อนตัดสินใจ — ยังใช้ backtest ไม่ได้อย่างน่าเชื่อถือ
PENDING_MORE_DATA = {
    "GULF.BK": "มีประวัติราคาแค่ ~323 วัน ไม่พอแบ่ง train/test ทำ walk-forward ได้",
}
