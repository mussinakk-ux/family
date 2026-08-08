# 家庭資產管理系統 v7 Ultimate Final

## 更新方式
只需將 `app.py` 與 `requirements.txt` 覆蓋到目前的 GitHub Repository。

**不要刪除或覆蓋既有的 `data.csv`、`config.json`、`backup/`。**

## 第一次啟動會自動完成資料遷移
1. 先尋找 GitHub 的 `family_asset.db`。
2. 如果還沒有，App 會讀取你現在既有的 `data.csv`。
3. 自動建立 SQLite 正式主資料庫 `family_asset.db`。
4. 原本 `data.csv` 完整保留，不會刪除。

## 每次按「儲存這一天」
以同一個 GitHub Commit 一次保存：
- `family_asset.db`：SQLite 正式主資料庫
- `data.csv`：CSV 鏡像／備援
- `backup/data_時間_原因.csv`：自動版本備份

## Streamlit Secrets
沿用你現在已經設定好的內容即可：

```toml
GITHUB_TOKEN="github_pat_..."
GITHUB_OWNER="mussinakk-ux"
GITHUB_REPO="family"
GITHUB_BRANCH="main"
```

不需要增加新設定。`GITHUB_DB_PATH` 未設定時會自動使用 `family_asset.db`。

## 人工備份仍永久保留
「匯入／匯出」頁面可：
- 匯出完整 CSV
- 匯出完整 Excel
- 合併匯入 CSV / Excel
- 完整覆蓋還原 CSV / Excel
- 從 GitHub 自動備份還原

## 固定規則
- 所有基金／美股／台股金額均支援負數。
- 假日不紀錄不影響統計；每日增減與上一筆有紀錄日期比較。
- 選到已有紀錄的日期會自動帶出當天所有數值，可直接修改。
- 個人順序固定：憲、萱、傑、文。
- 個人卡統一黑底金框、無人像；正數綠色、負數紅色。
- 黑底文字固定使用高對比白字。
- 資產走勢「近30天／近3個月／近1年／全部」為白底黑字，選取為金底黑字。
- 資產分布的基金／美股／台股圖例固定白字。
