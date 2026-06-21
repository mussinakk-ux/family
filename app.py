from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path
import calendar
import json

import pandas as pd
import plotly.express as px
import streamlit as st

DEFAULT_APP_TITLE = "$億萬富翁家庭資產"
DEFAULT_APP_ICON = "💰"
CONFIG_FILE = Path("config.json")


def load_config() -> dict:
    default = {"app_name": DEFAULT_APP_TITLE, "app_icon": DEFAULT_APP_ICON, "theme": "黑金尊爵版"}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                default.update({k: v for k, v in data.items() if v is not None})
        except Exception:
            pass
    return default


def save_config(config: dict) -> None:
    CONFIG_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


APP_CONFIG = load_config()
APP_TITLE = str(APP_CONFIG.get("app_name") or DEFAULT_APP_TITLE)
APP_ICON = str(APP_CONFIG.get("app_icon") or DEFAULT_APP_ICON)
PEOPLE = ["憲", "萱", "傑", "文"]
PERSON_COLORS = {"憲": "#00C853", "萱": "#FFD700", "傑": "#42A5F5", "文": "#BA68C8"}
TOTAL_COLOR = "#FFD700"
COLUMNS = ["日期", *PEOPLE]
DATA_FILE = Path("data.csv")

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)

THEMES = {
    "黑金尊爵版": {
        "bg1": "#050505", "bg2": "#17120a", "card": "rgba(26, 22, 15, .94)",
        "border": "#c9a646", "text": "#fff3c4", "muted": "#b9a56b", "accent": "#f6d365",
        "accent2": "#8f6a19", "good": "#40e28a", "bad": "#ff6666", "input": "#111111"
    },
    "招財綠金版": {
        "bg1": "#021712", "bg2": "#063626", "card": "rgba(4, 45, 32, .95)",
        "border": "#d8b85a", "text": "#fff7d1", "muted": "#c9ba78", "accent": "#ffd86b",
        "accent2": "#0d7a4d", "good": "#62f0a5", "bad": "#ff6d6d", "input": "#05261d"
    },
}


def money(v) -> str:
    try:
        return f"{int(round(float(v))):,}"
    except Exception:
        return "0"


def signed(v) -> str:
    try:
        n = int(round(float(v)))
        return ("+" if n >= 0 else "") + f"{abs(n):,}" if n >= 0 else f"-{abs(n):,}"
    except Exception:
        return "+0"


def load_data() -> pd.DataFrame:
    if DATA_FILE.exists() and DATA_FILE.stat().st_size > 0:
        df = pd.read_csv(DATA_FILE, encoding="utf-8-sig")
    else:
        df = pd.DataFrame(columns=COLUMNS)

    # 清除多餘欄位，補齊必要欄位
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = 0 if col != "日期" else ""
    df = df[COLUMNS].copy()
    df["日期"] = pd.to_datetime(df["日期"], errors="coerce")
    df = df.dropna(subset=["日期"])
    for p in PEOPLE:
        df[p] = pd.to_numeric(df[p], errors="coerce").fillna(0).astype(int)
    if not df.empty:
        df = df.sort_values("日期").drop_duplicates("日期", keep="last").reset_index(drop=True)
        df["日期"] = df["日期"].dt.date
    return df


def save_data(df: pd.DataFrame) -> None:
    out = df[COLUMNS].copy() if not df.empty else pd.DataFrame(columns=COLUMNS)
    if not out.empty:
        out["日期"] = pd.to_datetime(out["日期"]).dt.strftime("%Y-%m-%d")
    out.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if out.empty:
        return out
    out["日期_dt"] = pd.to_datetime(out["日期"])
    out["總資產"] = out[PEOPLE].sum(axis=1)
    out["每日增減"] = out["總資產"].diff().fillna(0).astype(int)
    for p in PEOPLE:
        out[f"{p}增減"] = out[p].diff().fillna(0).astype(int)
    out["月份"] = out["日期_dt"].dt.strftime("%Y-%m")
    out["年度"] = out["日期_dt"].dt.year.astype(str)
    return out


def current_period_gain(edf: pd.DataFrame, period: str) -> int:
    if edf.empty:
        return 0
    latest = edf.iloc[-1]
    if period == "month":
        sub = edf[edf["月份"] == latest["月份"]]
    else:
        sub = edf[edf["年度"] == latest["年度"]]
    if len(sub) <= 1:
        return 0
    return int(sub.iloc[-1]["總資產"] - sub.iloc[0]["總資產"])



def all_history_gain(edf: pd.DataFrame) -> int:
    """從第一筆紀錄開始，累計所有「與前一天相比」的增減。
    第一筆沒有前一天，視為 0；結果等同於最新總資產 - 第一筆總資產。
    """
    if edf.empty or len(edf) <= 1:
        return 0
    return int(pd.to_numeric(edf["每日增減"], errors="coerce").fillna(0).sum())


def person_history_gain(edf: pd.DataFrame, person: str) -> int:
    """每個人從第一筆紀錄開始，逐日累計與前一天相比的總變化。"""
    col = f"{person}增減"
    if edf.empty or len(edf) <= 1 or col not in edf.columns:
        return 0
    return int(pd.to_numeric(edf[col], errors="coerce").fillna(0).sum())


def annual_total_changes(edf: pd.DataFrame) -> pd.DataFrame:
    """每年度總資產增減表。"""
    if edf.empty:
        return pd.DataFrame(columns=["年度", "年初總資產", "年末總資產", "年增減"])
    year = edf.groupby("年度").agg(年初總資產=("總資產", "first"), 年末總資產=("總資產", "last"))
    year["年增減"] = year["年末總資產"] - year["年初總資產"]
    return year.reset_index()

def to_excel_bytes(df: pd.DataFrame) -> bytes:
    output = BytesIO()
    edf = enrich(df)
    export_df = edf[["日期", *PEOPLE, "總資產", "每日增減"]].copy() if not edf.empty else pd.DataFrame(columns=["日期", *PEOPLE, "總資產", "每日增減"])
    export_df["日期"] = pd.to_datetime(export_df["日期"], errors="coerce").dt.strftime("%Y-%m-%d") if not export_df.empty else export_df.get("日期", pd.Series(dtype=str))
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        export_df.to_excel(writer, index=False, sheet_name="每日紀錄")
        if not edf.empty:
            month = edf.groupby("月份").agg(月初總資產=("總資產", "first"), 月末總資產=("總資產", "last"))
            month["月增減"] = month["月末總資產"] - month["月初總資產"]
            year = edf.groupby("年度").agg(年初總資產=("總資產", "first"), 年末總資產=("總資產", "last"))
            year["年增減"] = year["年末總資產"] - year["年初總資產"]
            month.reset_index().to_excel(writer, index=False, sheet_name="月報表")
            year.reset_index().to_excel(writer, index=False, sheet_name="年報表")
    return output.getvalue()


def inject_css(theme_name: str) -> None:
    t = THEMES[theme_name]
    st.markdown(f"""
    <style>
    .stApp {{
        background: radial-gradient(circle at top left, {t['accent2']} 0, {t['bg2']} 28%, {t['bg1']} 100%);
        color: {t['text']};
    }}
    section[data-testid="stSidebar"] {{ background: rgba(0,0,0,.30); }}
    section[data-testid="stSidebar"], section[data-testid="stSidebar"] * {{ color: #FFFFFF !important; }}
    section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span {{ color: #FFFFFF !important; }}
    section[data-testid="stSidebar"] [role="radiogroup"] label {{ color: #FFFFFF !important; }}
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] * {{ color: #FFFFFF !important; }}
    h1, h2, h3, label, .stMarkdown, .stText, .stCaption {{ color: {t['text']} !important; }}
    .asset-card {{
        padding: 18px 18px;
        border: 1px solid {t['border']};
        border-radius: 20px;
        background: linear-gradient(145deg, {t['card']}, rgba(0,0,0,.25));
        box-shadow: 0 12px 32px rgba(0,0,0,.30);
        margin-bottom: 14px;
    }}
    .asset-label {{ color: {t['muted']}; font-size: 14px; margin-bottom: 8px; }}
    .asset-value {{ color: {t['accent']}; font-size: 30px; font-weight: 800; line-height: 1.15; }}
    .asset-small {{ color: {t['text']}; font-size: 18px; font-weight: 700; }}
    .gain {{ color: {t['good']}; font-weight: 800; }}
    .loss {{ color: {t['bad']}; font-weight: 800; }}
    div[data-testid="stMetric"] {{
        border: 1px solid {t['border']};
        background: {t['card']};
        border-radius: 18px;
        padding: 14px;
        box-shadow: 0 8px 26px rgba(0,0,0,.28);
    }}
    div[data-testid="stMetricValue"] {{ color: {t['accent']}; }}
    .stButton > button, .stDownloadButton > button {{
        border-radius: 14px;
        border: 1px solid {t['border']};
        background: linear-gradient(135deg, {t['accent']}, {t['accent2']});
        color: #101010;
        font-weight: 800;
        min-height: 44px;
    }}
    .calendar-grid {{ display:grid; grid-template-columns: repeat(7, 1fr); gap: 8px; }}
    .cal-head {{ text-align:center; color:{t['muted']}; font-weight:700; padding: 4px 0; }}
    .cal-cell {{
        min-height: 92px;
        border:1px solid rgba(216,184,90,.45);
        border-radius:14px;
        padding:8px;
        background:{t['card']};
        font-size: 13px;
        overflow:hidden;
    }}
    .cal-day {{ color:{t['accent']}; font-weight:800; margin-bottom:6px; }}
    .cal-empty {{ opacity:.25; }}
    .person-grid {{
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 14px;
        width: 100%;
    }}
    .person-grid .asset-card {{
        margin-bottom: 0;
        min-width: 0;
    }}
    @media (max-width: 768px) {{
        .asset-value {{font-size: 22px;}}
        .asset-small {{font-size: 13px !important;}}
        .person-grid {{
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 8px;
        }}
        .person-grid .asset-card {{
            padding: 12px 10px;
            border-radius: 16px;
        }}
        .calendar-grid {{ gap: 5px; }}
        .cal-cell {{ min-height: 74px; padding: 6px; font-size: 11px; }}
    }}
    </style>
    """, unsafe_allow_html=True)


def card(label: str, value: str, sub: str = "", positive: bool | None = None) -> None:
    cls = "gain" if positive is True else "loss" if positive is False else "asset-small"
    st.markdown(f"""
    <div class="asset-card">
        <div class="asset-label">{label}</div>
        <div class="asset-value">{value}</div>
        {f'<div class="{cls}">{sub}</div>' if sub else ''}
    </div>
    """, unsafe_allow_html=True)


def person_daily_stats(edf: pd.DataFrame, person: str) -> dict[str, int | float]:
    """回傳每個人每日變化的歷史統計。"""
    col = f"{person}增減"
    if edf.empty or col not in edf.columns:
        return {"today": 0, "history_gain": 0, "avg": 0, "max_up": 0, "max_down": 0, "positive_days": 0, "total_days": 0}
    changes = pd.to_numeric(edf[col], errors="coerce").fillna(0)
    # 第一筆通常是 0，統計時排除第一筆，較接近真正每日變化
    if len(changes) > 1:
        history = changes.iloc[1:]
    else:
        history = changes
    return {
        "today": int(changes.iloc[-1]) if len(changes) else 0,
        "history_gain": person_history_gain(edf, person),
        "avg": float(history.mean()) if len(history) else 0,
        "max_up": int(history.max()) if len(history) else 0,
        "max_down": int(history.min()) if len(history) else 0,
        "positive_days": int((history > 0).sum()) if len(history) else 0,
        "total_days": int(len(history)),
    }


def person_card_html(label: str, value: str, stats: dict[str, int | float]) -> str:
    today = int(stats.get("today", 0))
    history_gain = int(stats.get("history_gain", 0))
    avg = int(round(float(stats.get("avg", 0))))
    max_up = int(stats.get("max_up", 0))
    max_down = int(stats.get("max_down", 0))
    positive_days = int(stats.get("positive_days", 0))
    total_days = int(stats.get("total_days", 0))
    today_cls = "gain" if today >= 0 else "loss"
    return f"""
    <div class="asset-card">
        <div class="asset-label">{label}｜每日變化歷史統計</div>
        <div class="asset-value">{value}</div>
        <div class="{today_cls}">今日變化 {signed(today)}</div>
        <div class="asset-small" style="font-size:14px; line-height:1.65; margin-top:8px;">
            歷年累計增減：{signed(history_gain)}<br>
            平均日變化：{signed(avg)}<br>
            最大增加：{signed(max_up)}<br>
            最大減少：{signed(max_down)}<br>
            上升天數：{positive_days}/{total_days}
        </div>
    </div>
    """


def person_card(label: str, value: str, stats: dict[str, int | float]) -> None:
    st.markdown(person_card_html(label, value, stats), unsafe_allow_html=True)

def upsert_record(df: pd.DataFrame, record_date: date, values: dict[str, int]) -> pd.DataFrame:
    new = pd.DataFrame([{ "日期": record_date, **values }])
    out = pd.concat([df, new], ignore_index=True)
    out = out.sort_values("日期").drop_duplicates("日期", keep="last").reset_index(drop=True)
    return out[COLUMNS]


def render_calendar(edf: pd.DataFrame) -> None:
    if edf.empty:
        st.info("尚無資料可以顯示月曆。")
        return
    months = sorted(edf["月份"].unique().tolist(), reverse=True)
    selected_month = st.selectbox("選擇月份", months, index=0)
    y, m = map(int, selected_month.split("-"))
    month_df = edf[edf["月份"] == selected_month].copy()
    lookup = {int(row["日期_dt"].day): row for _, row in month_df.iterrows()}
    weeks = calendar.Calendar(firstweekday=6).monthdayscalendar(y, m)  # Sunday first
    st.markdown('<div class="calendar-grid">' + ''.join([f'<div class="cal-head">{d}</div>' for d in ["日","一","二","三","四","五","六"]]) + '</div>', unsafe_allow_html=True)
    html = '<div class="calendar-grid">'
    for week in weeks:
        for d in week:
            if d == 0:
                html += '<div class="cal-cell cal-empty"></div>'
            elif d in lookup:
                row = lookup[d]
                gain = int(row["每日增減"])
                gain_cls = "gain" if gain >= 0 else "loss"
                html += f'<div class="cal-cell"><div class="cal-day">{d}</div><div>總：{money(row["總資產"])}</div><div class="{gain_cls}">{signed(gain)}</div></div>'
            else:
                html += f'<div class="cal-cell"><div class="cal-day">{d}</div></div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


# State / top navigation
if "theme" not in st.session_state:
    st.session_state.theme = APP_CONFIG.get("theme", "黑金尊爵版") if APP_CONFIG.get("theme") in THEMES else "黑金尊爵版"
if "page" not in st.session_state:
    st.session_state.page = "首頁總覽"

inject_css(st.session_state.theme)

# Load fresh each rerun
raw_df = load_data()
edf = enrich(raw_df)

st.title(f"{APP_ICON} {APP_TITLE}")
nav_pages = ["首頁總覽", "新增／修改", "歷史紀錄", "月曆", "匯入／匯出", "設定", "使用說明"]
st.markdown('<div class="top-nav-wrap">', unsafe_allow_html=True)
# 手機版固定 2 個按鈕一排，避免選單橫向擠壓或變成側邊欄。
for start_idx in range(0, len(nav_pages), 2):
    nav_cols = st.columns(2)
    for offset, nav in enumerate(nav_pages[start_idx:start_idx + 2]):
        with nav_cols[offset]:
            label = ("✅ " if st.session_state.page == nav else "") + nav
            if st.button(label, key=f"nav_{nav}", use_container_width=True):
                st.session_state.page = nav
                st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

with st.expander("🎨 介面配色", expanded=False):
    theme_choice = st.radio("選擇配色", list(THEMES.keys()), index=list(THEMES.keys()).index(st.session_state.theme), horizontal=True)
    if theme_choice != st.session_state.theme:
        st.session_state.theme = theme_choice
        cfg = load_config()
        cfg["theme"] = theme_choice
        save_config(cfg)
        st.rerun()

page = st.session_state.page

if page == "首頁總覽":
    if edf.empty:
        st.warning("目前沒有資料，請先到『新增／修改』輸入第一筆紀錄。")
    else:
        latest = edf.iloc[-1]
        today_gain = int(latest["每日增減"])
        month_gain = current_period_gain(edf, "month")
        year_gain = current_period_gain(edf, "year")
        history_gain = all_history_gain(edf)
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("目前總資產", money(latest["總資產"]))
        c2.metric("較前一筆", signed(today_gain))
        c3.metric("本月增減", signed(month_gain))
        c4.metric("本年增減", signed(year_gain))
        c5.metric("歷年累計增減", signed(history_gain))

        st.caption("歷年累計增減＝從第一筆紀錄開始，逐日累計『與前一天相比』的總變化；第一筆沒有前一天，因此從 0 開始計算。")

        st.markdown("### 四人資產與每日變化歷史統計")
        # 手機與電腦都固定 2×2：第一排 憲、萱；第二排 傑、文
        cards_html = '<div class="person-grid">' + ''.join([
            person_card_html(p, money(latest[p]), person_daily_stats(edf, p)) for p in PEOPLE
        ]) + '</div>'
        st.markdown(cards_html, unsafe_allow_html=True)

        st.markdown("### 總資產走勢")
        fig = px.line(edf, x="日期_dt", y="總資產", markers=True, labels={"日期_dt":"日期", "總資產":"總資產"})
        fig.update_traces(line=dict(color=TOTAL_COLOR, width=3), marker=dict(size=7, color=TOTAL_COLOR))
        fig.update_layout(height=420, margin=dict(l=10, r=10, t=20, b=10), template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 總資產歷年增減")
        year_summary = annual_total_changes(edf)
        if not year_summary.empty:
            fig_year = px.bar(year_summary, x="年度", y="年增減", text="年增減", labels={"年增減":"年度增減"})
            fig_year.update_traces(marker_color=TOTAL_COLOR, texttemplate="%{text:,}", textposition="outside")
            fig_year.update_layout(height=320, margin=dict(l=10, r=10, t=20, b=10), template="plotly_dark")
            st.plotly_chart(fig_year, use_container_width=True)

        st.markdown("### 個人資產走勢")
        long = edf.melt(id_vars=["日期_dt"], value_vars=PEOPLE, var_name="姓名", value_name="資產")
        fig2 = px.line(long, x="日期_dt", y="資產", color="姓名", markers=True, labels={"日期_dt":"日期"}, color_discrete_map=PERSON_COLORS)
        fig2.update_layout(height=420, margin=dict(l=10, r=10, t=20, b=10), template="plotly_dark")
        st.plotly_chart(fig2, use_container_width=True)

        st.markdown("### 個人歷年累計增減")
        person_history = pd.DataFrame([{"姓名": p, "歷年累計增減": person_history_gain(edf, p)} for p in PEOPLE])
        fig3 = px.bar(person_history, x="姓名", y="歷年累計增減", text="歷年累計增減", color="姓名", color_discrete_map=PERSON_COLORS)
        fig3.update_traces(texttemplate="%{text:,}", textposition="outside")
        fig3.update_layout(height=320, margin=dict(l=10, r=10, t=20, b=10), template="plotly_dark", showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)
        st.dataframe(person_history, use_container_width=True, hide_index=True)

elif page == "新增／修改":
    st.subheader("新增或修改每日紀錄")
    st.info("同一天重新儲存會自動覆蓋舊資料。")
    default_date = raw_df.iloc[-1]["日期"] if not raw_df.empty else date.today()
    selected_date = st.date_input("日期", value=default_date)
    existing = raw_df[raw_df["日期"] == selected_date]
    defaults = {p: int(existing.iloc[0][p]) if not existing.empty else 0 for p in PEOPLE}

    with st.form("edit_form"):
        cols = st.columns(4)
        inputs = {}
        for i, p in enumerate(PEOPLE):
            with cols[i]:
                inputs[p] = st.number_input(p, min_value=0, step=1, value=defaults[p], format="%d")
        submitted = st.form_submit_button("儲存這一天")
        if submitted:
            new_df = upsert_record(raw_df, selected_date, {p: int(inputs[p]) for p in PEOPLE})
            save_data(new_df)
            st.success("已儲存，資料已更新。")
            st.rerun()

    st.divider()
    st.subheader("刪除單日紀錄")
    if raw_df.empty:
        st.caption("目前沒有資料可刪除。")
    else:
        dates = [d.strftime("%Y-%m-%d") for d in raw_df["日期"]]
        del_date = st.selectbox("選擇要刪除的日期", dates, index=len(dates)-1)
        if st.button("刪除選取日期", type="secondary"):
            new_df = raw_df[pd.to_datetime(raw_df["日期"]).dt.strftime("%Y-%m-%d") != del_date]
            save_data(new_df)
            st.success(f"已刪除 {del_date}")
            st.rerun()

elif page == "歷史紀錄":
    st.subheader("歷史紀錄與報表")
    if edf.empty:
        st.info("尚無資料。")
    else:
        show = edf[["日期", *PEOPLE, "總資產", "每日增減"]].copy()
        show["日期"] = pd.to_datetime(show["日期"]).dt.strftime("%Y-%m-%d")
        st.dataframe(show.sort_values("日期", ascending=False), use_container_width=True, hide_index=True)
        st.markdown("### 月報表")
        month = edf.groupby("月份").agg(月初總資產=("總資產", "first"), 月末總資產=("總資產", "last"))
        month["月增減"] = month["月末總資產"] - month["月初總資產"]
        st.dataframe(month.reset_index().sort_values("月份", ascending=False), use_container_width=True, hide_index=True)
        st.markdown("### 年報表")
        year = annual_total_changes(edf)
        st.dataframe(year.sort_values("年度", ascending=False), use_container_width=True, hide_index=True)

        st.markdown("### 從第一筆紀錄開始的每日增減累計")
        cumulative = edf[["日期", "總資產", "每日增減", *[f"{p}增減" for p in PEOPLE]]].copy()
        cumulative["總資產累計增減"] = cumulative["每日增減"].cumsum()
        for p in PEOPLE:
            cumulative[f"{p}累計增減"] = cumulative[f"{p}增減"].cumsum()
        cumulative["日期"] = pd.to_datetime(cumulative["日期"]).dt.strftime("%Y-%m-%d")
        st.dataframe(cumulative.sort_values("日期", ascending=False), use_container_width=True, hide_index=True)

elif page == "月曆":
    st.subheader("月曆顯示")
    render_calendar(edf)

elif page == "匯入／匯出":
    st.subheader("匯出備份")
    if raw_df.empty:
        st.info("尚無資料可匯出。")
    else:
        csv_bytes = raw_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("下載 CSV", csv_bytes, file_name="family_asset_records.csv", mime="text/csv")
        st.download_button("下載 Excel", to_excel_bytes(raw_df), file_name="family_asset_records.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.divider()
    st.subheader("匯入 CSV")
    st.warning("匯入後會覆蓋目前 data.csv。請先下載備份。")
    uploaded = st.file_uploader("選擇 CSV 檔，欄位需包含：日期、憲、萱、傑、文", type=["csv"])
    if uploaded is not None:
        if st.button("確認匯入並覆蓋"):
            content = uploaded.getvalue()
            imported = None
            for enc in ["utf-8-sig", "utf-8", "big5", "cp950"]:
                try:
                    imported = pd.read_csv(BytesIO(content), encoding=enc)
                    break
                except Exception:
                    continue
            if imported is None:
                st.error("讀取失敗，請確認 CSV 編碼。")
            else:
                missing = [c for c in COLUMNS if c not in imported.columns]
                if missing:
                    st.error(f"缺少欄位：{', '.join(missing)}")
                else:
                    imported = imported[COLUMNS].copy()
                    imported["日期"] = pd.to_datetime(imported["日期"], errors="coerce").dt.date
                    imported = imported.dropna(subset=["日期"])
                    for p in PEOPLE:
                        imported[p] = pd.to_numeric(imported[p], errors="coerce").fillna(0).astype(int)
                    imported = imported.sort_values("日期").drop_duplicates("日期", keep="last").reset_index(drop=True)
                    save_data(imported)
                    st.success("匯入完成。")
                    st.rerun()

elif page == "設定":
    st.subheader("APP 名稱設定")
    st.caption("可以自己命名首頁標題，也可以更換前方 Emoji。儲存後會同步到瀏覽器標題，手機加入主畫面時也會用新的名稱。")
    cfg = load_config()
    with st.form("app_config_form"):
        new_icon = st.text_input("APP 圖示 Emoji", value=str(cfg.get("app_icon", DEFAULT_APP_ICON)), max_chars=4)
        new_name = st.text_input("APP 名稱", value=str(cfg.get("app_name", DEFAULT_APP_TITLE)))
        save_btn = st.form_submit_button("儲存 APP 名稱")
        if save_btn:
            cfg["app_icon"] = new_icon.strip() or DEFAULT_APP_ICON
            cfg["app_name"] = new_name.strip() or DEFAULT_APP_TITLE
            cfg["theme"] = st.session_state.theme
            save_config(cfg)
            st.success("已儲存 APP 名稱。頁面即將重新整理。")
            st.rerun()

    st.markdown("### 預覽")
    card("目前 APP 標題", f"{str(cfg.get('app_icon', DEFAULT_APP_ICON))} {str(cfg.get('app_name', DEFAULT_APP_TITLE))}")

else:
    st.subheader("使用說明")
    st.markdown("""
    1. 到 **新增／修改** 輸入每天四個人的資產：憲、萱、傑、文。  
    2. 同一天重新儲存會直接覆蓋舊數字。  
    3. 首頁會自動計算總資產、較前一筆、本月、本年增減。  
    4. **匯入／匯出** 可下載 CSV / Excel 備份。  
    5. 部署到 Streamlit Cloud 後，手機用 Safari / Chrome 打開網址即可加入主畫面。  

    注意：Streamlit Cloud 免費版本機檔案可能因重新部署而重置，建議固定下載 CSV 或 Excel 備份。
    """)
