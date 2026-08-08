# v6.4 修正版

只更新 `app.py`，不要覆蓋 `data.csv`。

本版將「選擇已有紀錄日期後自動帶入數值」改為：
- 直接從 GitHub `data.csv` 找該日期資料。
- 每個日期使用獨立 widget key。
- `st.number_input` 直接指定該日既有數值為 `value`，不再依賴 session_state 灌值。
- 畫面會顯示「已讀取資料：憲…｜萱…｜傑…｜文…」供確認。
