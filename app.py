import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import date, datetime
from io import BytesIO
import plotly.express as px

APP_TITLE = "家庭資產管理系統 v2.0"
PEOPLE = ["萱", "憲", "傑", "文"]
DATA_FILE = Path("data.csv")
COLUMNS = ["日期", *PEOPLE]

st.set_page_config(page_title=APP_TITLE, page_icon="💰", layout="wide", initial_sidebar_state="collapsed")

THEMES = {
    "黑金尊爵版": {
        "bg1": "#060606", "bg2": "#14100a", "card": "rgba(22,20,16,.92)", "border": "#c9a646",
        "text": "#f8f1d0", "muted": "#b6a876", "accent": "#f3cc58", "accent2": "#7d621c",
        "good": "#28d17c", "bad": "#ff5c5c", "input": "#111111"
    },
    "招財綠金版": {
        "bg1": "#021d16", "bg2": "#063827", "card": "rgba(5,47,34,.92)", "border": "#d8b85a",
        "text": "#fff6cf", "muted": "#cdbf80", "accent": "#ffd86b", "accent2": "#0f7b4d",
        "good": "#63f2a1", "bad": "#ff6868", "input": "#05281e"
    }
}

def money(v):
    try:
        return f"{int(round(float(v))):,}"
    except Exception:
        return "0"

def signed(v):
    try:
        v = int(round(float(v)))
        return ("+" if v >= 0 else "") + f"{v:,}"
    except Exception:
        return "+0"

def load_data():
    if DATA_FILE.exists() and DATA_FILE.stat().st_size > 0:
        df = pd.read_csv(DATA_FILE)
    else:
        df = pd.DataFrame(columns=COLUMNS)
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = 0 if col != "日期" else ""
    df = df[COLUMNS]
    if not df.empty:
        df["日期"] = pd.to_datetime(df["日期"], errors="coerce").dt.date
        df = df.dropna(subset=["日期"])
        for p in PEOPLE:
            df[p] = pd.to_numeric(df[p], errors="coerce").fillna(0).astype(int)
        df = df.sort_values("日期").drop_duplicates("日期", keep="last").reset_index(drop=True)
    return df

def save_data(df):
    out = df.copy()
    if not out.empty:
        out["日期"] = pd.to_datetime(out["日期"]).dt.strftime("%Y-%m-%d")
    out.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")

def enrich(df):
    if df.empty:
        return df.copy()
    out = df.copy()
    out["日期_dt"] = pd.to_datetime(out["日期"])
    out["總資產"] = out[PEOPLE].sum(axis=1)
    out["每日增減"] = out["總資產"].diff().fillna(0).astype(int)
    out["月份"] = out["日期_dt"].dt.strftime("%Y-%m")
    out["年度"] = out["日期_dt"].dt.year.astype(str)
    return out

def inject_css(theme_name):
    t = THEMES[theme_name]
    st.markdown(f"""
    <style>
    .stApp {{
        background: radial-gradient(circle at top left, {t['accent2']} 0, {t['bg2']} 28%, {t['bg1']} 100%);
        color: {t['text']};
    }}
    [data-testid="stHeader"] {{ background: transparent; }}
    [data-testid="stSidebar"] {{ background: {t['bg1']}; }}
    .main-title {{font-size: 2.1rem; font-weight: 900; color:{t['accent']}; letter-spacing:.04em; margin-bottom:.2rem;}}
    .subtle {{color:{t['muted']}; font-size:.95rem;}}
    .asset-card {{
        border: 1px solid {t['border']}; border-radius: 20px; padding: 18px 18px;
        background: linear-gradient(145deg, {t['card']}, rgba(0,0,0,.45));
        box-shadow: 0 10px 30px rgba(0,0,0,.28); margin-bottom: 12px;
    }}
    .metric-label {{color:{t['muted']}; font-size:.9rem;}}
    .metric-value {{color:{t['text']}; font-size:1.75rem; font-weight:900;}}
    .big-value {{color:{t['accent']}; font-size:2.45rem; font-weight:900;}}
    .good {{color:{t['good']}; font-weight:800;}}
    .bad {{color:{t['bad']}; font-weight:800;}}
    .stButton>button, .stDownloadButton>button {{
        background: linear-gradient(135deg, {t['accent']}, #9c7827); color:#17120a; border:0; border-radius:14px;
        font-weight:900; padding:.65rem 1rem;
    }}
    input, textarea, [data-baseweb="input"] {{ background:{t['input']} !important; color:{t['text']} !important; }}
    div[data-testid="stDataFrame"] {{ border: 1px solid {t['border']}; border-radius: 16px; overflow:hidden; }}
    </style>
    """, unsafe_allow_html=True)

def card(label, value, sub="", cls=""):
    st.markdown(f"""<div class='asset-card'><div class='metric-label'>{label}</div><div class='{cls or 'metric-value'}'>{value}</div><div class='subtle'>{sub}</div></div>""", unsafe_allow_html=True)

def to_excel_bytes(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        export = df.copy()
        if not export.empty and "日期_dt" in export.columns:
            export = export.drop(columns=["日期_dt"])
        export.to_excel(writer, index=False, sheet_name="資產紀錄")
    return output.getvalue()

def build_calendar(df, selected_month):
    if df.empty:
        return pd.DataFrame()
    mdf = df[df["月份"] == selected_month].copy()
    if mdf.empty:
        return pd.DataFrame()
    mdf["日"] = mdf["日期_dt"].dt.day
    return mdf[["日期", "日", *PEOPLE, "總資產", "每日增減"]]

theme = st.sidebar.radio("配色", list(THEMES.keys()), horizontal=False)
inject_css(theme)

st.markdown(f"<div class='main-title'>{APP_TITLE}</div><div class='subtle'>單純記錄四人資產數值：萱、憲、傑、文。可新增、修改、刪除、匯出。</div>", unsafe_allow_html=True)

df = load_data()
edf = enrich(df)

with st.sidebar:
    st.header("功能")
    page = st.radio("選單", ["總覽", "新增/修改", "歷史紀錄", "月曆", "匯入/匯出", "使用說明"])
    st.caption("部署到 Streamlit Cloud 後，用手機瀏覽器開啟網址即可加入主畫面。")

if page == "總覽":
    if edf.empty:
        st.info("目前沒有紀錄，請到「新增/修改」輸入第一筆資料。")
    else:
        last = edf.iloc[-1]
        today_delta = int(last["每日增減"])
        this_month = last["月份"]
        this_year = last["年度"]
        month_df = edf[edf["月份"] == this_month]
        year_df = edf[edf["年度"] == this_year]
        month_delta = int(month_df.iloc[-1]["總資產"] - month_df.iloc[0]["總資產"]) if len(month_df) > 1 else 0
        year_delta = int(year_df.iloc[-1]["總資產"] - year_df.iloc[0]["總資產"]) if len(year_df) > 1 else 0
        c1, c2, c3 = st.columns(3)
        with c1: card("目前總資產", money(last["總資產"]), f"最新日期：{last['日期']}", "big-value")
        with c2: card("今日增減", signed(today_delta), "與前一筆紀錄比較", "metric-value good" if today_delta >= 0 else "metric-value bad")
        with c3: card("本月 / 本年", f"{signed(month_delta)} / {signed(year_delta)}", f"{this_month} / {this_year}")
        cols = st.columns(4)
        for i, p in enumerate(PEOPLE):
            with cols[i]: card(p, money(last[p]), "個人目前資產")
        chart_df = edf[["日期_dt", "總資產", *PEOPLE]].melt(id_vars="日期_dt", var_name="項目", value_name="金額")
        fig = px.line(chart_df, x="日期_dt", y="金額", color="項目", markers=True, title="資產走勢")
        fig.update_layout(template="plotly_dark", height=420, margin=dict(l=10,r=10,t=50,b=10))
        st.plotly_chart(fig, use_container_width=True)

elif page == "新增/修改":
    st.subheader("新增或修改每日資產")
    default_date = date.today()
    if not df.empty:
        default_date = df.iloc[-1]["日期"]
    selected_date = st.date_input("日期", value=default_date)
    existing = df[df["日期"] == selected_date]
    values = {p: int(existing.iloc[0][p]) if not existing.empty else 0 for p in PEOPLE}
    c1, c2 = st.columns(2)
    with c1:
        v1 = st.number_input("萱", min_value=0, value=values["萱"], step=1000, format="%d")
        v3 = st.number_input("傑", min_value=0, value=values["傑"], step=1000, format="%d")
    with c2:
        v2 = st.number_input("憲", min_value=0, value=values["憲"], step=1000, format="%d")
        v4 = st.number_input("文", min_value=0, value=values["文"], step=1000, format="%d")
    st.markdown(f"### 本日總資產：{money(v1+v2+v3+v4)}")
    b1, b2 = st.columns(2)
    if b1.button("儲存 / 更新", use_container_width=True):
        new_row = pd.DataFrame([{"日期": selected_date, "萱": int(v1), "憲": int(v2), "傑": int(v3), "文": int(v4)}])
        nd = pd.concat([df[df["日期"] != selected_date], new_row], ignore_index=True)
        nd = nd.sort_values("日期").reset_index(drop=True)
        save_data(nd)
        st.success("已儲存。")
        st.rerun()
    if b2.button("刪除此日期", use_container_width=True):
        nd = df[df["日期"] != selected_date]
        save_data(nd)
        st.warning("已刪除。")
        st.rerun()

elif page == "歷史紀錄":
    st.subheader("歷史紀錄")
    if edf.empty:
        st.info("尚無資料。")
    else:
        show = edf[["日期", *PEOPLE, "總資產", "每日增減", "月份", "年度"]].copy()
        st.dataframe(show, use_container_width=True, hide_index=True)
        monthly = edf.groupby("月份").agg(月初資產=("總資產","first"), 月末資產=("總資產","last")).reset_index()
        monthly["月增減"] = monthly["月末資產"] - monthly["月初資產"]
        st.subheader("月總計")
        st.dataframe(monthly, use_container_width=True, hide_index=True)
        yearly = edf.groupby("年度").agg(年初資產=("總資產","first"), 年末資產=("總資產","last")).reset_index()
        yearly["年增減"] = yearly["年末資產"] - yearly["年初資產"]
        st.subheader("年總計")
        st.dataframe(yearly, use_container_width=True, hide_index=True)

elif page == "月曆":
    st.subheader("日曆顯示")
    if edf.empty:
        st.info("尚無資料。")
    else:
        months = sorted(edf["月份"].unique(), reverse=True)
        selected_month = st.selectbox("選擇月份", months)
        cal = build_calendar(edf, selected_month)
        st.dataframe(cal, use_container_width=True, hide_index=True)
        st.caption("每日增減是和前一筆紀錄比較，不是和同月第一天比較。")

elif page == "匯入/匯出":
    st.subheader("匯出備份")
    if edf.empty:
        st.info("尚無資料可匯出。")
    else:
        export_df = edf[["日期", *PEOPLE, "總資產", "每日增減", "月份", "年度"]]
        st.download_button("下載 CSV", export_df.to_csv(index=False, encoding="utf-8-sig"), "family_asset_records.csv", "text/csv")
        st.download_button("下載 Excel", to_excel_bytes(export_df), "family_asset_records.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.subheader("匯入 CSV")
    up = st.file_uploader("上傳 CSV，欄位需包含：日期、萱、憲、傑、文", type=["csv"])
    if up is not None:
        try:
            newdf = pd.read_csv(up)
            missing = [c for c in COLUMNS if c not in newdf.columns]
            if missing:
                st.error("缺少欄位：" + "、".join(missing))
            else:
                newdf = newdf[COLUMNS]
                newdf["日期"] = pd.to_datetime(newdf["日期"], errors="coerce").dt.date
                newdf = newdf.dropna(subset=["日期"])
                for p in PEOPLE:
                    newdf[p] = pd.to_numeric(newdf[p], errors="coerce").fillna(0).astype(int)
                if st.button("確認匯入並覆蓋目前資料"):
                    save_data(newdf)
                    st.success("匯入完成。")
                    st.rerun()
        except Exception as e:
            st.error(f"匯入失敗：{e}")

else:
    st.subheader("手機使用方式")
    st.markdown("""
1. 把整個專案上傳到 GitHub。
2. 到 Streamlit Cloud 建立 App，Main file 選 `app.py`。
3. 產生網址後，用手機 Safari / Chrome 打開。
4. iPhone：分享 → 加入主畫面。Android：選單 → 加到主畫面。

注意：免費 Streamlit Cloud 的本機 CSV 可能因重新部署而重置，建議定期使用「匯出 Excel / CSV」備份。
""")
