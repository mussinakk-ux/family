# 家庭資產管理系統 v5.0 永久保存正式版

這一版的重點是：**按下儲存後，資料一定要寫回 GitHub 的 `data.csv` 才算成功**。  
如果 GitHub Secrets 沒有設定完成，系統會拒絕儲存，避免資料只存在 Streamlit 暫存空間而再次消失。

---

## 功能

- APP 名稱與 Emoji 可自訂
- 黑金 / 招財綠金主題切換
- 四人資產：憲、萱、傑、文
- 每人可輸入：基金、美股、台股
- 金額可輸入正數或負數
- 統計維持加總：基金 + 美股 + 台股
- 自動帶出今天日期
- 新增 / 修改 / 刪除資料
- 月報表、年報表顯示增減與成長率 %
- 月曆選擇月份後顯示當月增減與成長率
- CSV / Excel 匯出
- 匯入 CSV
- GitHub 自動同步永久保存
- 每次儲存自動建立 `backup/` 備份

---

## 上傳 GitHub

把 ZIP 解壓縮後，將資料夾內容上傳到你的 GitHub Repository：

```text
app.py
requirements.txt
README.md
config.json
data.csv
.streamlit/config.toml
```

你的 Repository 是：

```text
mussinakk-ux/family
```

---

## Streamlit Cloud 設定

Streamlit 主程式選：

```text
app.py
```

---

## 必做：設定 Streamlit Secrets

到 Streamlit Community Cloud：

```text
https://share.streamlit.io/
```

進入你的 App → 右上角 Settings → Secrets，貼上：

```toml
GITHUB_TOKEN = "請貼上你的 GitHub Personal Access Token"
GITHUB_REPO = "mussinakk-ux/family"
GITHUB_BRANCH = "main"
GITHUB_DATA_PATH = "data.csv"
GITHUB_CONFIG_PATH = "config.json"
GITHUB_ENABLE_BACKUP = "true"
GITHUB_BACKUP_DIR = "backup"
```

按 Save 後，請重新啟動 Streamlit App。

---

## GitHub Token 權限

到 GitHub 建立 Personal Access Token。

建議使用 Fine-grained token，Repository 選 `mussinakk-ux/family`，權限設定：

```text
Contents: Read and write
Metadata: Read-only
```

Token 只會顯示一次，請複製後貼到 Streamlit Secrets 的 `GITHUB_TOKEN`。

---

## 重要保護機制

v5.0 不再允許「只儲存到 Streamlit 暫存空間」。

如果 Secrets 沒設定好，新增 / 修改 / 刪除 / 匯入時會顯示錯誤，且不會儲存。  
這是為了避免再次發生：看起來有存，但關機或 Streamlit 重啟後資料消失。

---

## 如何確認真的有永久保存

每次儲存成功後，到 GitHub Repository 檢查：

1. `data.csv` 的更新時間是否變成剛剛
2. Commit 紀錄是否出現 `Update family asset data ...`
3. `backup/` 資料夾是否新增備份檔

有看到以上紀錄，代表資料已永久保存。
