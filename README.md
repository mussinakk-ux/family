# 家庭資產管理系統 v7.0 Ultimate

這是以 v6.4 穩定資料格式為基礎的新版介面。**不改 data.csv 資料結構，因此不需要搬移既有紀錄。**

## 重要：更新 GitHub 時不要覆蓋 data.csv

本更新包刻意 **不包含 data.csv、config.json**。請只更新：

- `app.py`
- `requirements.txt`

Streamlit 會繼續從 GitHub 目前的 `data.csv` 讀取歷史資料。

## v7 首頁

- 家庭總資產列移到最上排
- 家庭總資產、今日增減、本月增減、本年增減、歷年增減一次看到
- 個人卡片固定順序：**憲、萱、傑、文**
- 四人卡片顯示總資產、今日、本月、本年、歷年增減與成長率
- 資產分布（基金 / 美股 / 台股）
- 家庭總資產近 12 個月走勢
- 最新記錄日、GitHub 同步與備份狀態
- **沒有資產排行榜**

## 新增 / 修改

- 預設日期為台灣當天日期
- 選擇已存在的日期時，會直接帶出該日期所有既有數值
- 可輸入正數、0、負數
- 憲 / 萱 / 傑 / 文皆可輸入基金、美股、台股
- 同一天再次儲存會更新該日，不會新增重複日期
- 每次儲存都會更新 GitHub `data.csv` 並建立 `backup/` 備份

## 匯入 / 匯出

保留你習慣的手動備份方式：

- 匯出完整 CSV
- 匯出完整 Excel
- 匯入 CSV / Excel
- 合併匯入
- 完整覆蓋還原
- 直接從 GitHub `backup/` 選擇歷史備份還原

## Streamlit Secrets

沿用你目前已設定的 Secrets：

```toml
GITHUB_TOKEN="你的 Fine-grained Token"
GITHUB_OWNER="mussinakk-ux"
GITHUB_REPO="family"
GITHUB_BRANCH="main"
```

Token 只需要 Repository `family` 的 Contents: Read and write 權限。

## 更新方式

1. 先保留 GitHub 現有 `data.csv`。
2. 將本包的 `app.py`、`requirements.txt` 上傳覆蓋 GitHub 同名檔案。
3. 不要刪除 `backup/`。
4. 不要上傳任何 Token 到 GitHub。
5. 等 Streamlit 自動重新部署；若沒有更新，到 Streamlit Cloud → Manage app → Reboot app。

## 驗證

開啟 App → 設定 → 系統狀態，應看到：

`v7.0 Ultimate`

再到「新增／修改」，選一個已有紀錄的日期，確認數值會自動帶入後再開始正式使用。
