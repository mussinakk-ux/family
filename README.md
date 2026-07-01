# 家庭資產管理系統 v4.1（GitHub 永久保存正式版）

這版修正成真正的「永久保存」流程：只要 Streamlit Cloud Secrets 設定正確，每次按「儲存這一天」、刪除、匯入 CSV，都會自動更新 GitHub 上的 `data.csv`，並額外建立備份檔到 `backup/`。

## 這版重點

- 每人可輸入：基金、美股、台股
- 支援正數與負數
- 日期自動帶出今天
- 月報表、年報表顯示成長率 %
- 月曆可依月份顯示當月增減與成長率
- APP 名稱 / Emoji 可自訂
- 黑金 / 招財綠金切換
- 新增、修改、刪除、匯入後，自動同步到 GitHub
- 每次儲存會自動建立 `backup/data_年月日_時分秒.csv`
- 如果沒有設定 GitHub Secrets，系統會拒絕儲存，避免資料只存在 Streamlit 暫存空間

## 必做：設定 Streamlit Secrets

到 Streamlit Cloud：

`App → Settings → Secrets`

貼上：

```toml
GITHUB_TOKEN = "你的 GitHub Personal Access Token"
GITHUB_REPO = "mussinakk-ux/family"
GITHUB_BRANCH = "main"
GITHUB_DATA_PATH = "data.csv"
GITHUB_CONFIG_PATH = "config.json"
GITHUB_ENABLE_BACKUP = "true"
GITHUB_BACKUP_DIR = "backup"
```

## GitHub Token 權限

建議使用 Fine-grained token：

1. GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens
2. Generate new token
3. Repository access 選 `mussinakk-ux/family`
4. Permissions → Repository permissions → Contents 選 `Read and write`
5. Generate token
6. 複製 token 貼到 Streamlit Secrets 的 `GITHUB_TOKEN`

## 使用方式

1. 解壓縮 ZIP
2. 將內容上傳 / 覆蓋到 GitHub repo：`mussinakk-ux/family`
3. 到 Streamlit Cloud 部署或重新啟動 app
4. 確認首頁「GitHub 永久保存狀態」顯示已啟用
5. 之後每天按「儲存這一天」後，資料會永久寫入 GitHub

## 重要提醒

v4.1 以 GitHub 上的 `data.csv` 作為資料來源。只要 Secrets 設定正確，電腦關機、手機關閉、Streamlit 重新啟動、重新部署，都會讀取 GitHub 最新資料。
