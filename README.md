# Trading Bot — คู่มือการใช้งาน

โฟลเดอร์นี้เก็บสคริปต์ทดลองสำหรับระบบเทรดอัตโนมัติ (อยู่ระหว่างรอ Webull OpenAPI อนุมัติ)

## เตรียมเครื่องก่อนใช้ (ทำครั้งเดียว)

ติดตั้งไลบรารีที่ต้องใช้ (ถ้ายังไม่มี):

```bash
python -m pip install yfinance pandas google-genai python-dotenv
```

ตั้งค่า Gemini API key:
1. คัดลอกไฟล์ `.env.example` เป็น `.env`
2. เปิด `.env` ด้วย Notepad แล้ววาง key จริงแทนข้อความตัวอย่าง
3. ห้ามแชร์ไฟล์ `.env` ให้ใคร (มี key จริงอยู่ในนั้น)

## สคริปต์ทั้งหมด เรียงตามลำดับที่ควรใช้

### 1. `backtest_ma_strategy.py` — ทดสอบกลยุทธ์เดียว
ทดสอบกลยุทธ์ MA Crossover ย้อนหลังกับหุ้น 1 ตัว ดู return, drawdown, win rate

```bash
python backtest_ma_strategy.py
```

แก้พารามิเตอร์ได้ที่ด้านบนไฟล์: `TICKER`, `FAST_MA`, `SLOW_MA`, `START`, `END`

### 2. `compare_strategies.py` — เทียบหลายกลยุทธ์ หุ้นเดียว
เทียบ MA Crossover / RSI / Bollinger Bands / Buy & Hold บนหุ้น 1 ตัวพร้อมกัน

```bash
python compare_strategies.py
```

### 3. `multi_ticker_compare.py` — เทียบกลยุทธ์ข้ามหลายหุ้น
รัน `compare_strategies.py` ซ้ำกับหุ้นหลายตัว (ปัจจุบันตั้งเป็นหุ้นเทค) ดูว่ากลยุทธ์ไหนเสถียรข้ามหุ้น

```bash
python multi_ticker_compare.py
```

แก้รายชื่อหุ้นได้ที่ตัวแปร `TICKERS`

### 4. `fetch_news_signal.py` — ดึงข่าว + สถานะเทคนิคปัจจุบัน
ดึงข่าวล่าสุดของหุ้น 1 ตัว พร้อมสถานะสัญญาณเทคนิคตอนนี้ (ยังไม่วิเคราะห์ sentiment)

```bash
python fetch_news_signal.py
```

### 5. `news_sentiment_signal.py` — วิเคราะห์ sentiment ด้วย Gemini + รวมสัญญาณ
ต่อยอดจากข้อ 4: ส่งข่าวให้ Gemini ให้คะแนน sentiment แล้วรวมกับสัญญาณเทคนิคเป็นคำแนะนำเดียว
**ต้องมี `.env` ที่ตั้งค่า key แล้ว**

```bash
python news_sentiment_signal.py
```

แก้หุ้นที่จะดูได้ที่ตัวแปร `TICKER` ในไฟล์ `fetch_news_signal.py`

### 6. `multi_sector_signal.py` — composite signal ข้ามหมวดอุตสาหกรรม
รันข้อ 5 ซ้ำกับหุ้นหลายหมวด (การเงิน, สุขภาพ, พลังงาน, ฯลฯ) แสดงตารางสรุปเทียบกัน

```bash
python multi_sector_signal.py
```

แก้รายชื่อหุ้น/หมวดได้ที่ตัวแปร `SECTOR_TICKERS`

## สถานะ Watchlist หลังผ่าน Walk-forward Validation

ดูรายชื่อและเหตุผลเต็มๆ ใน `watchlist.py` (มี 3 กลุ่ม: `WATCHLIST`, `REJECTED`, `PENDING_MORE_DATA`)

| หุ้น | สถานะ | SL | TP |
|---|---|---|---|
| DELTA.BK | ✅ ผ่านครบ (backtest+walk-forward+slippage) | ATR-based 3.0x | 100% |
| NVDA | ✅ ผ่าน walk-forward | ATR-based 1.5x | 50% |
| PLTR | ✅ ผ่าน walk-forward | ATR-based 1.0x | 75% |
| TRUE.BK | ✅ ผ่าน walk-forward | ATR-based 1.5x | 75% |
| META | ⚠️ คาบเส้น ไม่มี edge ชัดเจน — ใช้ default config | - | - |
| GOOGL | ⚠️ คาบเส้น TRAIN แทบเสมอตัว น่าสงสัยว่า TEST เป็น noise | - | - |
| AFRM | ❌ ตกรอบ (overfit — TRAIN +364% แต่ TEST -30%) | - | - |
| TSLA | ❌ ตกรอบ (overfit — TRAIN +1106% แต่ TEST -20%, ไม่มี config ไหนใช้ได้ใน TEST เลย) | - | - |
| MSFT | ❌ ตกรอบ (ติดลบสม่ำเสมอทั้ง TRAIN และ TEST) | - | - |
| GULF.BK | ⏳ รอข้อมูลเพิ่ม (มีแค่ ~323 วัน) | - | - |

Config รายตัวอยู่ใน `ticker_strategy_config.py` — รัน `run_watchlist_backtest.py` เพื่อ backtest ทั้ง
watchlist โดยแต่ละตัวใช้ SL/TP ของตัวเอง (ตัวที่ยังไม่ validate จะ fallback ไปใช้ค่า default อัตโนมัติ)

เครื่องมือทดสอบ: `delta_sl_optimization.py`, `sl_tp_grid_search.py`, `take_profit_test.py`,
`walk_forward_tp_validation.py`, `multi_ticker_walk_forward.py`, `multi_ticker_sl_tp_search.py`,
`entry_filter_test.py` (RSI entry filter — ทดสอบแล้วผลคาบเส้น ไม่ได้นำมาใช้),
`trade_log_detail.py` (ดูรายละเอียดทุกไม้ + ทดสอบ Profit Lock — ปิดไว้ ช่วยแค่ 1-7% ไม่คุ้มความเสี่ยงตั้งค่าผิด),
`profit_lock_grid_search.py` (grid search Trigger/Lock — ระวัง: เคยมี bug ให้ค่าผิดถ้า lock_pct > trigger_pct แก้แล้ว)

## สิ่งที่ยังไม่มี (รอทำต่อ)
- การยิงคำสั่งซื้อขายจริงผ่าน Webull API (รออนุมัติ)
- Risk guard หลายชั้น (budget cap, cash-only guard, circuit breaker ฯลฯ)
- Kill switch ผ่าน LINE bot
- Logging ลง Neon Postgres

## คำเตือน
ทุกสคริปต์ในนี้เป็นเครื่องมือ **วิเคราะห์/ทดสอบเท่านั้น ไม่ได้ยิงคำสั่งซื้อขายจริง**
ผลจาก backtest ไม่รับประกันผลในอนาคต ก่อนใช้เงินจริงต้องมี risk guard และ paper trade ให้มั่นใจก่อนเสมอ
