# 家庭資產管理系統 v2.2

單純記錄四人資產數值：萱、憲、傑、文。

## v2.2 功能

- 新增 / 修改 / 刪除每日資產紀錄
- 同日期自動覆蓋
- 自動計算：總資產、較前一筆、本月增減、本年增減
- 四人個別資產卡片
- 總資產走勢圖
- 四人個別資產走勢圖
- 歷史紀錄表
- 月報表、年報表
- 月曆模式
- 黑金尊爵版 / 招財綠金版切換
- CSV 匯入 / 匯出
- Excel 匯出
- 手機與電腦皆可使用

## GitHub 上傳方式

1. 建立新的 GitHub Repository
2. 將整個資料夾內的檔案上傳
3. 確認有以下檔案：
   - `app.py`
   - `requirements.txt`
   - `data.csv`
   - `.streamlit/config.toml`
   - `README.md`

## Streamlit Cloud 部署方式

1. 到 Streamlit Cloud 建立 New app
2. 選擇你的 GitHub Repository
3. Main file path 填：`app.py`
4. Deploy

## 手機加入桌面

### iPhone
Safari 打開 Streamlit 網址 → 分享 → 加入主畫面

### Android
Chrome 打開 Streamlit 網址 → 右上角選單 → 加到主畫面

## 注意

Streamlit Cloud 免費版的本機 `data.csv` 可能在重新部署或休眠後重置。請定期使用匯出 CSV / Excel 備份。


## v2.2 更新
- 四人資產走勢圖改成不同顏色。
- 左側選單文字改白色，提高黑金/綠金主題辨識度。
- 首頁四人卡片加入每日變化歷史統計：今日變化、平均日變化、最大增加、最大減少、上升天數。
