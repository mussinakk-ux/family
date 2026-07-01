# 家庭資產管理系統 v6.0 Ultimate

這是永久保存正式版。資料不再只存在 Streamlit 暫存空間。

## 核心功能

- 按「儲存這一天」後，直接更新 GitHub `data.csv`
- 每次儲存自動建立 GitHub Commit
- 每次儲存自動備份到 `backup/data_年月日_時分秒.csv`
- 未設定 GitHub Secrets 時，會拒絕儲存，避免資料再次消失
- 讀取時優先讀 GitHub 最新 `data.csv`
- 支援基金／美股／台股，全部合併統計
- 支援負數
- 月報表、年報表顯示增減與成長率
- 月曆頁可依月份顯示當月增減與成長率
- App 名稱與 Emoji 可自訂
- 黑金／招財綠金主題

## Streamlit Secrets 設定

到 Streamlit Cloud：

`https://share.streamlit.io/`

進入你的 App → `Manage app` 或右上角 `⋮` → `Settings` → `Secrets`

貼上以下內容：

```toml
GITHUB_TOKEN="github_pat_你剛剛產生的Token"
GITHUB_OWNER="mussinakk-ux"
GITHUB_REPO="family"
GITHUB_BRANCH="main"
GITHUB_DATA_PATH="data.csv"
GITHUB_CONFIG_PATH="config.json"
GITHUB_ENABLE_BACKUP="true"
GITHUB_BACKUP_DIR="backup"
```

按 Save 後，回到 App 按 `Reboot app`。

> 不要把 Token 寫進 GitHub 檔案，也不要貼給任何人。

## 如何確認有永久保存成功

新增或修改一筆資料後，App 會出現成功訊息：

`已成功同步到 GitHub data.csv，並建立備份；資料已永久保存。`

再到 GitHub Repository：

`https://github.com/mussinakk-ux/family/commits/main/data.csv`

應該會看到新的 Commit。

## 上傳方式

把 ZIP 解壓縮後，將以下檔案覆蓋上傳到 GitHub Repository `family`：

- `app.py`
- `requirements.txt`
- `config.json`
- `.streamlit/config.toml`
- `data.csv`（第一次更新可上傳；之後日常使用不要手動改它）

Streamlit 主程式選：

`app.py`

## 重要提醒

以後更新版本時，原則上只覆蓋程式檔，不要手動覆蓋 `data.csv`，因為 `data.csv` 是你的正式資料庫。
