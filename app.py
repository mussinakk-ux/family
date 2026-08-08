from __future__ import annotations

import base64
import calendar
import html
import json
import os
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

APP_VERSION = "v7.0 Ultimate"
DEFAULT_APP_TITLE = "$億萬富翁家庭資產"
DEFAULT_APP_ICON = "💰"
TAIPEI = ZoneInfo("Asia/Taipei")
PEOPLE = ["憲", "萱", "傑", "文"]
ASSET_TYPES = ["基金", "美股", "台股"]
DETAIL_COLUMNS = [f"{p}{a}" for p in PEOPLE for a in ASSET_TYPES]
COLUMNS = ["日期", *DETAIL_COLUMNS]
DATA_FILE = Path("data.csv")
CONFIG_FILE = Path("config.json")

PERSON_STYLE = {
    "憲": {"line": "#2f75b5", "soft": "#eef5ff", "dark": "#174a7e", "icon": "👤"},
    "萱": {"line": "#d54d73", "soft": "#fff0f4", "dark": "#8f2344", "icon": "👤"},
    "傑": {"line": "#5f8f44", "soft": "#f1f7ea", "dark": "#365a25", "icon": "👤"},
    "文": {"line": "#c48228", "soft": "#fff6e8", "dark": "#805114", "icon": "👤"},
}

THEMES = {
    "黑金尊爵版": {
        "bg": "#070707", "panel": "#11110f", "panel2": "#17150f", "gold": "#e4b843",
        "gold2": "#8f6b1f", "text": "#f7f0dd", "muted": "#b9ab83", "good": "#7bd85b",
        "bad": "#ff6b6b", "border": "rgba(228,184,67,.70)"
    },
    "招財綠金版": {
        "bg": "#04130e", "panel": "#0b2118", "panel2": "#103123", "gold": "#e2bd58",
        "gold2": "#1d7550", "text": "#fff7d8", "muted": "#cabd8c", "good": "#73e7a8",
        "bad": "#ff7777", "border": "rgba(226,189,88,.72)"
    },
}

# ---------- 基本工具 ----------
def now_tw() -> datetime:
    return datetime.now(TAIPEI)


def _secret(name: str, default: str = "") -> str:
    try:
        if name in st.secrets:
            return str(st.secrets.get(name, default)).strip()
    except Exception:
        pass
    return str(os.environ.get(name, default)).strip()


def github_settings() -> dict:
    owner = _secret("GITHUB_OWNER")
    repo_value = _secret("GITHUB_REPO")
    repo_name = _secret("GITHUB_REPO_NAME")
    if repo_value and "/" in repo_value:
        repo_full = repo_value
    elif owner and repo_value:
        repo_full = f"{owner}/{repo_value}"
    elif owner and repo_name:
        repo_full = f"{owner}/{repo_name}"
    else:
        repo_full = repo_value
    return {
        "token": _secret("GITHUB_TOKEN"),
        "repo": repo_full,
        "branch": _secret("GITHUB_BRANCH", "main") or "main",
        "data_path": _secret("GITHUB_DATA_PATH", "data.csv") or "data.csv",
        "config_path": _secret("GITHUB_CONFIG_PATH", "config.json") or "config.json",
        "backup_dir": _secret("GITHUB_BACKUP_DIR", "backup") or "backup",
    }


def github_enabled() -> bool:
    g = github_settings()
    return bool(g["token"] and g["repo"])


def github_headers() -> dict:
    g = github_settings()
    return {
        "Authorization": f"Bearer {g['token']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def github_get_file(path: str) -> tuple[bytes | None, str | None, str | None]:
    if not github_enabled():
        return None, None, "尚未設定 GitHub 同步"
    g = github_settings()
    url = f"https://api.github.com/repos/{g['repo']}/contents/{quote(path, safe='/')}"
    try:
        r = requests.get(url, headers=github_headers(), params={"ref": g["branch"]}, timeout=20)
        if r.status_code == 404:
            return None, None, None
        if r.status_code >= 400:
            return None, None, f"GitHub 讀取失敗：{r.status_code} {r.text[:280]}"
        payload = r.json()
        content = base64.b64decode(payload.get("content", "")) if payload.get("content") else b""
        return content, payload.get("sha"), None
    except Exception as exc:
        return None, None, f"GitHub 讀取錯誤：{exc}"


def github_put_file(path: str, content: bytes, message: str, retry: bool = True) -> tuple[bool, str]:
    if not github_enabled():
        return False, "尚未設定 GitHub Secrets；為避免資料只存在暫存空間，本版本拒絕儲存。"
    g = github_settings()
    _, sha, err = github_get_file(path)
    if err:
        return False, err
    url = f"https://api.github.com/repos/{g['repo']}/contents/{quote(path, safe='/')}"
    body = {
        "message": message,
        "content": base64.b64encode(content).decode("ascii"),
        "branch": g["branch"],
    }
    if sha:
        body["sha"] = sha
    try:
        r = requests.put(url, headers=github_headers(), json=body, timeout=30)
        if r.status_code in (409, 422) and retry:
            return github_put_file(path, content, message + " (retry)", retry=False)
        if r.status_code >= 400:
            return False, f"GitHub 儲存失敗：{r.status_code} {r.text[:420]}"
        return True, "已同步 GitHub 並永久保存"
    except Exception as exc:
        return False, f"GitHub 儲存錯誤：{exc}"


def github_list_backups() -> tuple[list[dict], str | None]:
    if not github_enabled():
        return [], "尚未設定 GitHub 同步"
    g = github_settings()
    url = f"https://api.github.com/repos/{g['repo']}/contents/{quote(g['backup_dir'], safe='/')}"
    try:
        r = requests.get(url, headers=github_headers(), params={"ref": g["branch"]}, timeout=20)
        if r.status_code == 404:
            return [], None
        if r.status_code >= 400:
            return [], f"備份清單讀取失敗：{r.status_code}"
        rows = [x for x in r.json() if x.get("type") == "file" and x.get("name", "").lower().endswith(".csv")]
        rows.sort(key=lambda x: x.get("name", ""), reverse=True)
        return rows, None
    except Exception as exc:
        return [], f"備份清單讀取錯誤：{exc}"


def make_backup(csv_bytes: bytes, reason: str = "save") -> tuple[bool, str]:
    if not github_enabled():
        return False, "尚未設定 GitHub 同步"
    g = github_settings()
    stamp = now_tw().strftime("%Y%m%d_%H%M%S")
    path = f"{g['backup_dir']}/data_{stamp}_{reason}.csv"
    return github_put_file(path, csv_bytes, f"Backup family asset data {stamp} ({reason})", retry=False)


def load_config() -> dict:
    cfg = {"app_name": DEFAULT_APP_TITLE, "app_icon": DEFAULT_APP_ICON, "theme": "黑金尊爵版"}
    if github_enabled():
        content, _, err = github_get_file(github_settings()["config_path"])
        if content and not err:
            try:
                cfg.update(json.loads(content.decode("utf-8")))
                CONFIG_FILE.write_bytes(content)
                return cfg
            except Exception:
                pass
    if CONFIG_FILE.exists():
        try:
            cfg.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass
    return cfg


def save_config(cfg: dict) -> tuple[bool, str]:
    raw = json.dumps(cfg, ensure_ascii=False, indent=2).encode("utf-8")
    CONFIG_FILE.write_bytes(raw)
    if not github_enabled():
        return False, "設定只寫入暫存空間；請先設定 GitHub Secrets。"
    return github_put_file(github_settings()["config_path"], raw, "Update family asset app config")


def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=COLUMNS)
    df = df.copy()
    if "日期" not in df.columns:
        raise ValueError("匯入檔缺少『日期』欄位")

    # 相容最早期只有四人總數值的資料：視為基金。
    for p in PEOPLE:
        fund = f"{p}基金"
        if fund not in df.columns:
            df[fund] = df[p] if p in df.columns else 0
        for a in ("美股", "台股"):
            col = f"{p}{a}"
            if col not in df.columns:
                df[col] = 0

    df = df[COLUMNS].copy()
    df["日期"] = pd.to_datetime(df["日期"], errors="coerce")
    df = df.dropna(subset=["日期"])
    for col in DETAIL_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).round().astype(int)
    if df.empty:
        return pd.DataFrame(columns=COLUMNS)
    df = df.sort_values("日期").drop_duplicates("日期", keep="last").reset_index(drop=True)
    df["日期"] = df["日期"].dt.date
    return df


def load_data() -> pd.DataFrame:
    if github_enabled():
        content, _, err = github_get_file(github_settings()["data_path"])
        if content and not err:
            DATA_FILE.write_bytes(content)
            try:
                return normalize_df(pd.read_csv(BytesIO(content), encoding="utf-8-sig"))
            except UnicodeDecodeError:
                return normalize_df(pd.read_csv(BytesIO(content)))
    if DATA_FILE.exists() and DATA_FILE.stat().st_size:
        return normalize_df(pd.read_csv(DATA_FILE, encoding="utf-8-sig"))
    return pd.DataFrame(columns=COLUMNS)


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    out = normalize_df(df)
    if not out.empty:
        out = out.copy()
        out["日期"] = pd.to_datetime(out["日期"]).dt.strftime("%Y-%m-%d")
    # utf-8-sig 是 Excel 中文相容格式。
    return out.to_csv(index=False).encode("utf-8-sig")


def save_data(df: pd.DataFrame, reason: str = "save") -> tuple[bool, str]:
    if not github_enabled():
        return False, "GitHub 永久保存未啟用，為避免再次遺失資料，本版本不允許儲存。"
    clean = normalize_df(df)
    raw = dataframe_to_csv_bytes(clean)
    ok, msg = github_put_file(
        github_settings()["data_path"],
        raw,
        f"Update family asset data {now_tw().strftime('%Y-%m-%d %H:%M:%S')}",
    )
    if not ok:
        return False, msg
    DATA_FILE.write_bytes(raw)
    backup_ok, backup_msg = make_backup(raw, reason)
    if backup_ok:
        return True, f"{msg}；已建立自動備份"
    return True, f"{msg}；主要資料已保存（備份提示：{backup_msg}）"


def money(v) -> str:
    try:
        return f"{int(round(float(v))):,}"
    except Exception:
        return "0"


def signed(v) -> str:
    try:
        n = int(round(float(v)))
    except Exception:
        n = 0
    return f"+{n:,}" if n >= 0 else f"-{abs(n):,}"


def pct(change, base) -> float:
    try:
        b = float(base)
        return (float(change) / b * 100) if b else 0.0
    except Exception:
        return 0.0


def pct_text(v) -> str:
    try:
        n = float(v)
    except Exception:
        n = 0.0
    return f"{n:+.2f}%"


def html_change(v) -> str:
    cls = "gain" if float(v) >= 0 else "loss"
    return f'<span class="{cls}">{signed(v)}</span>'


def person_total_series(df: pd.DataFrame, person: str) -> pd.Series:
    cols = [f"{person}{a}" for a in ASSET_TYPES]
    return df[cols].sum(axis=1)


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        cols = [*COLUMNS, *[f"{p}總資產" for p in PEOPLE], "總資產", "每日增減", "日期_dt", "月份", "年份"]
        return pd.DataFrame(columns=cols)
    out = normalize_df(df).copy()
    for p in PEOPLE:
        out[f"{p}總資產"] = person_total_series(out, p)
    out["總資產"] = out[[f"{p}總資產" for p in PEOPLE]].sum(axis=1)
    out["每日增減"] = out["總資產"].diff().fillna(0).round().astype(int)
    for p in PEOPLE:
        out[f"{p}每日增減"] = out[f"{p}總資產"].diff().fillna(0).round().astype(int)
    out["日期_dt"] = pd.to_datetime(out["日期"])
    out["月份"] = out["日期_dt"].dt.strftime("%Y-%m")
    out["年份"] = out["日期_dt"].dt.year.astype(int)
    return out


def previous_close(edf: pd.DataFrame, start: date, value_col: str) -> float | None:
    prior = edf[edf["日期"] < start]
    if prior.empty:
        return None
    return float(prior.iloc[-1][value_col])


def period_stats(edf: pd.DataFrame, value_col: str, start: date, end: date) -> dict:
    part = edf[(edf["日期"] >= start) & (edf["日期"] <= end)]
    if part.empty:
        return {"start": 0, "end": 0, "change": 0, "growth": 0.0}
    end_value = float(part.iloc[-1][value_col])
    base = previous_close(edf, start, value_col)
    if base is None:
        base = float(part.iloc[0][value_col])
    change = end_value - base
    return {"start": base, "end": end_value, "change": change, "growth": pct(change, base)}


def current_stats(edf: pd.DataFrame, value_col: str) -> dict:
    if edf.empty:
        return {"current": 0, "daily": 0, "daily_pct": 0, "month": 0, "month_pct": 0, "year": 0, "year_pct": 0, "history": 0, "history_pct": 0}
    latest = edf.iloc[-1]
    current = float(latest[value_col])
    prev = float(edf.iloc[-2][value_col]) if len(edf) > 1 else current
    daily = current - prev
    latest_date: date = latest["日期"]
    month_start = date(latest_date.year, latest_date.month, 1)
    year_start = date(latest_date.year, 1, 1)
    month = period_stats(edf, value_col, month_start, latest_date)
    year = period_stats(edf, value_col, year_start, latest_date)
    first = float(edf.iloc[0][value_col])
    hist = current - first
    return {
        "current": current,
        "daily": daily, "daily_pct": pct(daily, prev),
        "month": month["change"], "month_pct": month["growth"],
        "year": year["change"], "year_pct": year["growth"],
        "history": hist, "history_pct": pct(hist, first),
    }


def monthly_report(edf: pd.DataFrame) -> pd.DataFrame:
    if edf.empty:
        return pd.DataFrame(columns=["月份", "月末總資產", "增減", "成長率"])
    rows = []
    months = sorted(edf["月份"].unique())
    for ym in months:
        y, m = map(int, ym.split("-"))
        start = date(y, m, 1)
        last_day = calendar.monthrange(y, m)[1]
        end = date(y, m, last_day)
        s = period_stats(edf, "總資產", start, end)
        rows.append({"月份": ym, "月末總資產": int(s["end"]), "增減": int(s["change"]), "成長率": s["growth"]})
    return pd.DataFrame(rows)


def yearly_report(edf: pd.DataFrame) -> pd.DataFrame:
    if edf.empty:
        return pd.DataFrame(columns=["年度", "年末總資產", "增減", "成長率"])
    rows = []
    for y in sorted(edf["年份"].unique()):
        start, end = date(int(y), 1, 1), date(int(y), 12, 31)
        s = period_stats(edf, "總資產", start, end)
        rows.append({"年度": int(y), "年末總資產": int(s["end"]), "增減": int(s["change"]), "成長率": s["growth"]})
    return pd.DataFrame(rows)


def excel_bytes(df: pd.DataFrame) -> bytes:
    edf = enrich(df)
    daily = edf.copy()
    if not daily.empty:
        daily["日期"] = daily["日期"].astype(str)
        daily = daily[["日期", *DETAIL_COLUMNS, *[f"{p}總資產" for p in PEOPLE], "總資產", "每日增減"]]
    month = monthly_report(edf)
    year = yearly_report(edf)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        daily.to_excel(writer, index=False, sheet_name="每日紀錄")
        month.to_excel(writer, index=False, sheet_name="月報表")
        year.to_excel(writer, index=False, sheet_name="年報表")
    return output.getvalue()


def parse_import(uploaded) -> pd.DataFrame:
    name = uploaded.name.lower()
    raw = uploaded.getvalue()
    if name.endswith(".csv"):
        try:
            df = pd.read_csv(BytesIO(raw), encoding="utf-8-sig")
        except UnicodeDecodeError:
            df = pd.read_csv(BytesIO(raw))
    elif name.endswith(".xlsx") or name.endswith(".xls"):
        df = pd.read_excel(BytesIO(raw))
    else:
        raise ValueError("只支援 CSV 或 Excel (.xlsx) 檔")
    # 若匯入的是本 App 匯出的每日紀錄，忽略計算欄位即可。
    return normalize_df(df)


def upsert_record(df: pd.DataFrame, record_date: date, values: dict[str, int]) -> pd.DataFrame:
    current = normalize_df(df)
    new = pd.DataFrame([{"日期": record_date, **values}])
    return normalize_df(pd.concat([current, new], ignore_index=True))


def merge_import(existing: pd.DataFrame, incoming: pd.DataFrame) -> pd.DataFrame:
    return normalize_df(pd.concat([normalize_df(existing), normalize_df(incoming)], ignore_index=True))

# ---------- CSS / UI ----------
def inject_css(theme_name: str) -> None:
    t = THEMES[theme_name]
    st.markdown(f"""
    <style>
      .stApp {{ background: {t['bg']}; color:{t['text']}; }}
      .block-container {{ max-width: 1540px; padding-top: 1.0rem; padding-bottom: 2rem; }}
      h1,h2,h3,label,p,span,.stCaption,.stMarkdown {{ color:{t['text']}; }}
      [data-testid="stHeader"] {{ background:rgba(0,0,0,0); }}
      .app-head {{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-bottom:8px;}}
      .app-title {{font-size:34px;font-weight:900;color:{t['gold']};letter-spacing:.3px;}}
      .sync-top {{text-align:right;color:{t['muted']};font-size:13px;line-height:1.5;}}
      .sync-dot {{color:#65d36e;}}
      .top-nav {{margin:4px 0 12px;}}
      .stButton>button {{border:1px solid {t['border']};border-radius:10px;background:{t['panel']};color:{t['text']};font-weight:800;min-height:42px;}}
      .stButton>button:hover {{border-color:{t['gold']};color:{t['gold']};box-shadow:0 0 14px rgba(228,184,67,.25);}}
      div[data-testid="stFormSubmitButton"] button {{background:linear-gradient(135deg,#00e676,#ffd54f)!important;color:#000!important;border:2px solid #fff!important;font-size:19px!important;font-weight:900!important;min-height:56px!important;}}
      .family-strip {{display:grid;grid-template-columns:1.35fr repeat(4,1fr);border:1px solid {t['border']};border-radius:16px;overflow:hidden;background:linear-gradient(120deg,{t['panel2']},{t['panel']});margin:6px 0 16px;}}
      .family-cell {{padding:18px 18px;border-right:1px solid rgba(228,184,67,.35);text-align:center;}}
      .family-cell:last-child {{border-right:0;}}
      .family-label {{font-size:15px;color:{t['muted']};font-weight:800;margin-bottom:8px;}}
      .family-main {{font-size:34px;color:{t['gold']};font-weight:950;letter-spacing:.5px;}}
      .metric-main {{font-size:24px;font-weight:900;}}
      .metric-pct {{font-size:15px;font-weight:900;margin-top:4px;}}
      .gain {{color:{t['good']}!important;font-weight:850;}}
      .loss {{color:{t['bad']}!important;font-weight:850;}}
      .person-card {{border-radius:16px;overflow:hidden;border:1px solid rgba(255,255,255,.65);box-shadow:0 9px 22px rgba(0,0,0,.22);margin-bottom:8px;color:#101010;}}
      .person-head {{padding:13px 18px;font-size:25px;font-weight:950;display:flex;gap:10px;align-items:center;}}
      .person-body {{padding:10px 18px 14px;}}
      .person-body * {{color:#171717!important;}}
      .person-asset {{font-size:31px;font-weight:950;margin:3px 0 9px;}}
      .person-row {{display:grid;grid-template-columns:1fr 1fr 1fr;gap:4px;border-top:1px solid rgba(0,0,0,.11);padding:7px 0;font-size:14px;}}
      .person-row .v {{text-align:right;font-weight:850;}}
      .person-row .p {{text-align:right;font-weight:850;color:#24743a!important;}}
      .panel {{border:1px solid {t['border']};border-radius:16px;background:{t['panel']};padding:14px 16px;margin-bottom:12px;}}
      .panel-title {{color:{t['gold']};font-size:17px;font-weight:900;margin-bottom:8px;}}
      .status-grid {{display:grid;grid-template-columns:repeat(4,1fr);gap:0;border:1px solid {t['border']};border-radius:16px;background:{t['panel']};overflow:hidden;}}
      .status-item {{padding:15px;border-right:1px solid rgba(228,184,67,.28);min-height:104px;}}
      .status-item:last-child {{border-right:0;}}
      .status-title {{color:{t['gold']};font-weight:850;margin-bottom:8px;}}
      .status-big {{font-size:19px;font-weight:900;}}
      div[data-testid="stMetric"] {{border:1px solid {t['border']};background:{t['panel']};border-radius:14px;padding:12px;}}
      div[data-testid="stMetricValue"] {{color:{t['gold']};}}
      .calendar-grid {{display:grid;grid-template-columns:repeat(7,1fr);gap:7px;}}
      .cal-head {{text-align:center;color:{t['muted']};font-weight:800;padding:5px;}}
      .cal-cell {{min-height:94px;border:1px solid rgba(228,184,67,.35);border-radius:12px;padding:7px;background:{t['panel']};font-size:12px;}}
      .cal-day {{color:{t['gold']};font-weight:900;font-size:14px;margin-bottom:5px;}}
      .stDownloadButton>button {{width:100%;border:1px solid {t['border']};border-radius:10px;background:{t['panel2']};color:{t['text']};font-weight:850;}}
      @media (max-width: 850px) {{
        .app-title {{font-size:26px;}}
        .family-strip {{grid-template-columns:1fr 1fr;}}
        .family-cell {{border-bottom:1px solid rgba(228,184,67,.3);}}
        .family-cell:first-child {{grid-column:1/-1;}}
        .family-main {{font-size:30px;}}
        .status-grid {{grid-template-columns:1fr 1fr;}}
        .status-item {{border-bottom:1px solid rgba(228,184,67,.25);}}
        .person-asset {{font-size:25px;}}
        .calendar-grid {{gap:4px;}}
        .cal-cell {{min-height:72px;padding:5px;font-size:10px;}}
      }}
    </style>
    """, unsafe_allow_html=True)


def family_strip(stats: dict) -> None:
    items = [
        ("家庭總資產", money(stats["current"]), None, "family"),
        ("今日增減", signed(stats["daily"]), pct_text(stats["daily_pct"]), "normal"),
        ("本月增減", signed(stats["month"]), pct_text(stats["month_pct"]), "normal"),
        ("本年增減", signed(stats["year"]), pct_text(stats["year_pct"]), "normal"),
        ("歷年增減", signed(stats["history"]), pct_text(stats["history_pct"]), "normal"),
    ]
    cells = []
    for label, val, ptxt, kind in items:
        if kind == "family":
            cells.append(f'<div class="family-cell"><div class="family-label">{label}</div><div class="family-main">$ {val}</div></div>')
        else:
            cls = "gain" if not val.startswith("-") else "loss"
            cells.append(f'<div class="family-cell"><div class="family-label">{label}</div><div class="metric-main {cls}">{val}</div><div class="metric-pct {cls}">{ptxt}</div></div>')
    st.markdown('<div class="family-strip">' + ''.join(cells) + '</div>', unsafe_allow_html=True)


def person_card(person: str, s: dict) -> None:
    sty = PERSON_STYLE[person]
    rows = []
    for label, key, pkey in [
        ("今日增減", "daily", "daily_pct"),
        ("本月增減", "month", "month_pct"),
        ("本年增減", "year", "year_pct"),
        ("歷年增減", "history", "history_pct"),
    ]:
        cls = "gain" if s[key] >= 0 else "loss"
        rows.append(f'<div class="person-row"><div>{label}</div><div class="v {cls}">{signed(s[key])}</div><div class="p">{pct_text(s[pkey])}</div></div>')
    st.markdown(f"""
    <div class="person-card" style="background:{sty['soft']};border-color:{sty['line']}55;">
      <div class="person-head" style="color:{sty['dark']};border-bottom:1px solid {sty['line']}44;">
        <span style="width:36px;height:36px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;background:{sty['line']};color:white!important;font-size:19px;">{sty['icon']}</span>{person}
      </div>
      <div class="person-body">
        <div style="font-size:13px;">總資產</div>
        <div class="person-asset">$ {money(s['current'])}</div>
        {''.join(rows)}
      </div>
    </div>
    """, unsafe_allow_html=True)


def plot_asset_distribution(edf: pd.DataFrame):
    if edf.empty:
        return None
    last = edf.iloc[-1]
    vals = {a: sum(int(last[f"{p}{a}"]) for p in PEOPLE) for a in ASSET_TYPES}
    dfp = pd.DataFrame({"類別": list(vals.keys()), "金額": list(vals.values())})
    fig = px.pie(dfp, names="類別", values="金額", hole=.58, color="類別",
                 color_discrete_map={"基金":"#d5547c","美股":"#5e934e","台股":"#3d83c5"})
    fig.update_traces(textposition="outside", textinfo="percent+label", hovertemplate="%{label}<br>%{value:,.0f}<br>%{percent}<extra></extra>")
    fig.update_layout(height=300, margin=dict(l=8,r=8,t=8,b=8), showlegend=True, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#f7f0dd")
    return fig


def plot_total_trend(edf: pd.DataFrame, months: int | None = 12):
    if edf.empty:
        return None
    d = edf.copy()
    if months:
        latest = d["日期_dt"].max()
        cutoff = latest - pd.DateOffset(months=months)
        d = d[d["日期_dt"] >= cutoff]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d["日期_dt"], y=d["總資產"], mode="lines+markers", name="家庭總資產", line=dict(color="#e4b843", width=3), marker=dict(size=5)))
    fig.update_layout(height=300, margin=dict(l=12,r=12,t=10,b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#f7f0dd", xaxis=dict(gridcolor="rgba(255,255,255,.08)"), yaxis=dict(gridcolor="rgba(255,255,255,.08)", tickformat=","), showlegend=False)
    return fig


def plot_people(edf: pd.DataFrame, months: int | None = 12):
    if edf.empty:
        return None
    d = edf.copy()
    if months:
        latest = d["日期_dt"].max()
        d = d[d["日期_dt"] >= latest - pd.DateOffset(months=months)]
    fig = go.Figure()
    for p in PEOPLE:
        fig.add_trace(go.Scatter(x=d["日期_dt"], y=d[f"{p}總資產"], mode="lines", name=p, line=dict(color=PERSON_STYLE[p]["line"], width=2.6)))
    fig.update_layout(height=420, margin=dict(l=12,r=12,t=15,b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#f7f0dd", xaxis=dict(gridcolor="rgba(255,255,255,.08)"), yaxis=dict(gridcolor="rgba(255,255,255,.08)", tickformat=","), legend=dict(orientation="h", y=1.08))
    return fig


def render_calendar(edf: pd.DataFrame) -> None:
    if edf.empty:
        st.info("尚無資料可以顯示月曆。")
        return
    months = sorted(edf["月份"].unique().tolist(), reverse=True)
    selected = st.selectbox("選擇月份", months, key="calendar_month")
    y, m = map(int, selected.split("-"))
    month_df = edf[edf["月份"] == selected]
    month_end_date = date(y, m, calendar.monthrange(y, m)[1])
    s = period_stats(edf, "總資產", date(y,m,1), month_end_date)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("月初基準資產", money(s["start"]))
    c2.metric("月末／最新資產", money(s["end"]))
    c3.metric("當月增減", signed(s["change"]))
    c4.metric("當月成長率", pct_text(s["growth"]))

    lookup = {int(r["日期_dt"].day): r for _, r in month_df.iterrows()}
    weeks = calendar.Calendar(firstweekday=6).monthdayscalendar(y, m)
    heads = ''.join(f'<div class="cal-head">{x}</div>' for x in ["日","一","二","三","四","五","六"])
    html_cells = []
    for week in weeks:
        for d in week:
            if d == 0:
                html_cells.append('<div class="cal-cell" style="opacity:.22"></div>')
            elif d in lookup:
                r = lookup[d]
                cls = "gain" if int(r["每日增減"]) >= 0 else "loss"
                html_cells.append(f'<div class="cal-cell"><div class="cal-day">{d}</div><div>總 {money(r["總資產"])}</div><div class="{cls}">{signed(r["每日增減"])}</div></div>')
            else:
                html_cells.append(f'<div class="cal-cell"><div class="cal-day">{d}</div></div>')
    st.markdown(f'<div class="calendar-grid">{heads}{"".join(html_cells)}</div>', unsafe_allow_html=True)

# ---------- App 啟動 ----------
cfg = load_config()
APP_TITLE = str(cfg.get("app_name") or DEFAULT_APP_TITLE)
APP_ICON = str(cfg.get("app_icon") or DEFAULT_APP_ICON)
THEME = cfg.get("theme") if cfg.get("theme") in THEMES else "黑金尊爵版"

st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide", initial_sidebar_state="collapsed")
inject_css(THEME)

if "page" not in st.session_state:
    st.session_state.page = "首頁"
if "edit_date" not in st.session_state:
    st.session_state.edit_date = now_tw().date()

raw_df = load_data()
edf = enrich(raw_df)
last_record_date = edf.iloc[-1]["日期"] if not edf.empty else None
sync_text = "已同步" if github_enabled() else "未設定"

st.markdown(f"""
<div class="app-head">
  <div class="app-title">{html.escape(APP_ICON)} {html.escape(APP_TITLE)}</div>
  <div class="sync-top">{now_tw().strftime('%Y/%m/%d %H:%M')}<br>永久保存：GitHub <span class="sync-dot">●</span></div>
</div>
""", unsafe_allow_html=True)

NAV = ["首頁", "新增／修改", "月報表", "年報表", "日曆", "圖表", "匯入／匯出", "設定"]
nav_cols = st.columns(len(NAV))
for i, label in enumerate(NAV):
    with nav_cols[i]:
        show = ("🏠 " if label == "首頁" else "") + label
        if st.button(show, key=f"nav_{label}", use_container_width=True, type="primary" if st.session_state.page == label else "secondary"):
            st.session_state.page = label
            st.rerun()

page = st.session_state.page

# ---------- 首頁 ----------
if page == "首頁":
    if edf.empty:
        st.warning("目前尚無資產紀錄。請到『新增／修改』建立第一筆資料。")
    else:
        fam = current_stats(edf, "總資產")
        family_strip(fam)

        person_stats = {p: current_stats(edf, f"{p}總資產") for p in PEOPLE}
        cols = st.columns(4)
        for col, p in zip(cols, PEOPLE):
            with col:
                person_card(p, person_stats[p])
                with st.expander("查看明細"):
                    latest = edf.iloc[-1]
                    st.write(f"基金：{money(latest[f'{p}基金'])}")
                    st.write(f"美股：{money(latest[f'{p}美股'])}")
                    st.write(f"台股：{money(latest[f'{p}台股'])}")
                    if st.button("更新這一天", key=f"home_edit_{p}", use_container_width=True):
                        st.session_state.edit_date = last_record_date or now_tw().date()
                        st.session_state.page = "新增／修改"
                        st.rerun()

        chart_left, chart_right = st.columns([1, 2])
        with chart_left:
            st.markdown('<div class="panel"><div class="panel-title">資產分布（依類別）</div>', unsafe_allow_html=True)
            fig = plot_asset_distribution(edf)
            if fig:
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            st.markdown('</div>', unsafe_allow_html=True)
        with chart_right:
            st.markdown('<div class="panel"><div class="panel-title">家庭總資產走勢（近 12 個月）</div>', unsafe_allow_html=True)
            fig = plot_total_trend(edf, 12)
            if fig:
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            st.markdown('</div>', unsafe_allow_html=True)

        # 記錄狀態：最新一日四人都視為已紀錄，因為每筆日資料包含四人欄位。
        latest = edf.iloc[-1]
        recorded_people = sum(any(int(latest[f"{p}{a}"]) != 0 for a in ASSET_TYPES) for p in PEOPLE)
        last_backup = "自動建立"
        st.markdown(f"""
        <div class="status-grid">
          <div class="status-item"><div class="status-title">今日記錄狀態</div><div class="status-big">已記錄：{recorded_people} 人</div><div>未記錄：{4-recorded_people} 人</div></div>
          <div class="status-item"><div class="status-title">最新記錄日</div><div class="status-big">{last_record_date.strftime('%Y/%m/%d')}</div><div>點日期可修改</div></div>
          <div class="status-item"><div class="status-title">GitHub 同步狀態</div><div class="status-big">{sync_text}</div><div>{now_tw().strftime('%Y/%m/%d %H:%M')}</div></div>
          <div class="status-item"><div class="status-title">備份狀態</div><div class="status-big">每次儲存自動備份</div><div>另可手動匯出至電腦</div></div>
        </div>
        """, unsafe_allow_html=True)
        st.caption("資料永久保存於 GitHub・每次儲存自動備份・歷史版本可還原")

# ---------- 新增 / 修改 ----------
elif page == "新增／修改":
    st.subheader("新增／修改每日資產")
    selected_date = st.date_input("日期", value=st.session_state.edit_date, key="record_date", format="YYYY/MM/DD")
    st.session_state.edit_date = selected_date

    existing = raw_df[raw_df["日期"] == selected_date]
    has_existing = not existing.empty
    existing_row = existing.iloc[-1] if has_existing else None
    if has_existing:
        st.success(f"已載入 {selected_date.strftime('%Y/%m/%d')} 的既有紀錄，可直接修改。")
    else:
        st.info("這一天尚無紀錄，將建立新資料。")

    values: dict[str, int] = {}
    with st.form(f"asset_form_{selected_date.isoformat()}"):
        for p in PEOPLE:
            st.markdown(f"### {p}")
            c1, c2, c3 = st.columns(3)
            for col, asset in zip((c1,c2,c3), ASSET_TYPES):
                key = f"{p}{asset}"
                default = int(existing_row[key]) if has_existing else 0
                with col:
                    values[key] = int(st.number_input(f"{p}｜{asset}金額", value=default, step=1000, key=f"input_{selected_date.isoformat()}_{key}"))
            st.caption(f"{p} 小計：{money(sum(values[f'{p}{a}'] for a in ASSET_TYPES))}")
        submitted = st.form_submit_button("更新這一天" if has_existing else "儲存這一天", use_container_width=True)

    if submitted:
        new_df = upsert_record(raw_df, selected_date, values)
        ok, msg = save_data(new_df, "update" if has_existing else "new")
        if ok:
            st.success(msg)
            st.session_state.edit_date = selected_date
            st.cache_data.clear()
            st.rerun()
        else:
            st.error(msg)

    if has_existing:
        st.divider()
        st.warning("刪除會影響所有統計；系統會先建立備份再刪除。")
        if st.button("刪除這一天紀錄", key=f"delete_{selected_date.isoformat()}"):
            deleted = raw_df[raw_df["日期"] != selected_date]
            ok, msg = save_data(deleted, "delete")
            if ok:
                st.success("已刪除並完成永久保存與備份。")
                st.rerun()
            else:
                st.error(msg)

# ---------- 月報表 ----------
elif page == "月報表":
    st.subheader("月報表")
    report = monthly_report(edf)
    if report.empty:
        st.info("尚無資料。")
    else:
        show = report.copy()
        show["月末總資產"] = show["月末總資產"].map(money)
        show["增減"] = show["增減"].map(signed)
        show["成長率"] = show["成長率"].map(pct_text)
        st.dataframe(show.iloc[::-1], use_container_width=True, hide_index=True)
        fig = px.bar(report, x="月份", y="增減", text=report["成長率"].map(pct_text))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#f7f0dd", height=380)
        st.plotly_chart(fig, use_container_width=True)

# ---------- 年報表 ----------
elif page == "年報表":
    st.subheader("年報表")
    report = yearly_report(edf)
    if report.empty:
        st.info("尚無資料。")
    else:
        show = report.copy()
        show["年末總資產"] = show["年末總資產"].map(money)
        show["增減"] = show["增減"].map(signed)
        show["成長率"] = show["成長率"].map(pct_text)
        st.dataframe(show.iloc[::-1], use_container_width=True, hide_index=True)
        fig = px.bar(report, x="年度", y="增減", text=report["成長率"].map(pct_text))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#f7f0dd", height=380)
        st.plotly_chart(fig, use_container_width=True)

# ---------- 日曆 ----------
elif page == "日曆":
    st.subheader("資產日曆")
    if st.button("📍 回到今天"):
        st.session_state.page = "新增／修改"
        st.session_state.edit_date = now_tw().date()
        st.rerun()
    render_calendar(edf)
    st.caption("假日沒有紀錄不影響統計；每日增減會與『上一筆有紀錄的日期』比較。")

# ---------- 圖表 ----------
elif page == "圖表":
    st.subheader("資產走勢")
    period_label = st.segmented_control("顯示範圍", ["近30天", "近3個月", "近1年", "全部"], default="近1年")
    months_map = {"近30天": 1, "近3個月": 3, "近1年": 12, "全部": None}
    months = months_map.get(period_label, 12)
    st.markdown("### 家庭總資產")
    fig = plot_total_trend(edf, months)
    if fig:
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("### 四人資產走勢")
    fig = plot_people(edf, months)
    if fig:
        st.plotly_chart(fig, use_container_width=True)

# ---------- 匯入 / 匯出 ----------
elif page == "匯入／匯出":
    st.subheader("匯出備份")
    st.caption("建議每週至少下載一次完整備份到自己的電腦。")
    e1, e2 = st.columns(2)
    with e1:
        st.download_button("下載完整 CSV 備份", data=dataframe_to_csv_bytes(raw_df), file_name=f"family_asset_backup_{now_tw().strftime('%Y%m%d_%H%M%S')}.csv", mime="text/csv", use_container_width=True)
    with e2:
        st.download_button("下載完整 Excel 備份", data=excel_bytes(raw_df), file_name=f"family_asset_backup_{now_tw().strftime('%Y%m%d_%H%M%S')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    st.divider()
    st.subheader("匯入 / 還原")
    uploaded = st.file_uploader("選擇 CSV 或 Excel 備份檔", type=["csv", "xlsx", "xls"])
    mode = st.radio("匯入方式", ["合併匯入（同日期以匯入檔為準）", "完整覆蓋還原"], horizontal=True)
    if uploaded is not None:
        try:
            incoming = parse_import(uploaded)
            st.info(f"已讀取 {len(incoming)} 筆日期資料：{incoming['日期'].min() if not incoming.empty else '-'} ～ {incoming['日期'].max() if not incoming.empty else '-'}")
            if st.button("確認匯入並永久保存", type="primary"):
                target = merge_import(raw_df, incoming) if mode.startswith("合併") else incoming
                ok, msg = save_data(target, "import")
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
        except Exception as exc:
            st.error(f"匯入失敗：{exc}")

    st.divider()
    st.subheader("GitHub 自動備份還原")
    backups, err = github_list_backups()
    if err:
        st.warning(err)
    elif not backups:
        st.info("目前 GitHub backup/ 尚無備份檔。")
    else:
        options = {x["name"]: x["path"] for x in backups[:100]}
        picked = st.selectbox("選擇歷史備份", list(options.keys()))
        st.warning("還原歷史備份會取代目前 data.csv；執行前系統會先備份目前資料。")
        if st.button("還原這份 GitHub 備份"):
            path = options[picked]
            content, _, get_err = github_get_file(path)
            if get_err or not content:
                st.error(get_err or "無法讀取備份")
            else:
                try:
                    old_df = normalize_df(pd.read_csv(BytesIO(content), encoding="utf-8-sig"))
                    # 先額外備份目前資料，再覆蓋。
                    make_backup(dataframe_to_csv_bytes(raw_df), "before_restore")
                    ok, msg = save_data(old_df, "restore")
                    if ok:
                        st.success(f"已還原：{picked}")
                        st.rerun()
                    else:
                        st.error(msg)
                except Exception as exc:
                    st.error(f"還原失敗：{exc}")

# ---------- 設定 ----------
elif page == "設定":
    st.subheader("系統設定")
    with st.form("settings_form"):
        new_name = st.text_input("APP 名稱", value=APP_TITLE)
        new_icon = st.text_input("APP 圖示 Emoji", value=APP_ICON, max_chars=4)
        new_theme = st.radio("介面配色", list(THEMES.keys()), index=list(THEMES.keys()).index(THEME), horizontal=True)
        save_settings = st.form_submit_button("儲存設定")
    if save_settings:
        new_cfg = {"app_name": new_name.strip() or DEFAULT_APP_TITLE, "app_icon": new_icon.strip() or DEFAULT_APP_ICON, "theme": new_theme}
        ok, msg = save_config(new_cfg)
        if ok:
            st.success("設定已永久保存，重新整理後套用。")
            st.rerun()
        else:
            st.error(msg)

    st.divider()
    st.subheader("系統狀態")
    st.write(f"版本：**{APP_VERSION}**")
    if github_enabled():
        g = github_settings()
        st.success(f"GitHub 永久保存已啟用：{g['repo']} / {g['branch']} / {g['data_path']}")
    else:
        st.error("GitHub 永久保存未啟用。")
    st.caption("此版本沿用既有 data.csv 欄位，不需要搬移或重建歷史資料。")
