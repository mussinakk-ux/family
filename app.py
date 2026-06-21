
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
from pathlib import Path

try:
    import yfinance as yf
except Exception:
    yf = None

DB_PATH = Path("investment_data.db")
DEFAULT_PASSWORD = "1688"

DEFAULT_HOLDINGS = [
    {"account":"富邦銀行｜退休帳戶","purpose":"退休長期","market":"TW","currency":"TWD","symbol":"00947","name":"台新臺灣IC設計動能ETF","shares":1004.0,"cost":25.78,"price":25.78},
    {"account":"富邦銀行｜退休帳戶","purpose":"退休長期","market":"US","currency":"USD","symbol":"SOXQ","name":"Invesco費城半導體ETF","shares":2.0,"cost":94.685,"price":94.685},
    {"account":"國泰銀行｜價差帳戶","purpose":"價差操作","market":"TW","currency":"TWD","symbol":"1310","name":"台苯","shares":1000.0,"cost":9.52,"price":9.52},
    {"account":"國泰銀行｜價差帳戶","purpose":"核心長期","market":"TW","currency":"TWD","symbol":"2330","name":"台積電","shares":20.0,"cost":1778.5,"price":1778.5},
    {"account":"國泰銀行｜價差帳戶","purpose":"現金","market":"CASH","currency":"TWD","symbol":"CASH_CTBC","name":"國泰價差戶現金","shares":1.0,"cost":0.0,"price":0.0},
    {"account":"永豐銀行｜核心帳戶","purpose":"核心長期","market":"TW","currency":"TWD","symbol":"00631L","name":"元大台灣50正2","shares":4070.0,"cost":26.66,"price":38.33},
    {"account":"永豐銀行｜核心帳戶","purpose":"價差操作","market":"TW","currency":"TWD","symbol":"00830","name":"國泰費城半導體ETF","shares":1056.0,"cost":81.77,"price":81.77},
    {"account":"永豐銀行｜核心帳戶","purpose":"價差操作","market":"TW","currency":"TWD","symbol":"2302","name":"麗正","shares":1000.0,"cost":19.53,"price":19.53},
    {"account":"永豐銀行｜核心帳戶","purpose":"核心長期","market":"TW","currency":"TWD","symbol":"2330","name":"台積電","shares":510.0,"cost":489.14,"price":1778.5},
    {"account":"永豐銀行｜核心帳戶","purpose":"價差操作","market":"TW","currency":"TWD","symbol":"2337","name":"旺宏","shares":1000.0,"cost":149.71,"price":149.71},
    {"account":"永豐銀行｜核心帳戶","purpose":"價差操作","market":"TW","currency":"TWD","symbol":"2408","name":"南亞科","shares":200.0,"cost":227.32,"price":227.32},
    {"account":"永豐銀行｜核心帳戶","purpose":"價差操作","market":"TW","currency":"TWD","symbol":"3491","name":"昇達科","shares":5.0,"cost":1557.20,"price":1557.20},
    {"account":"永豐銀行｜核心帳戶","purpose":"價差操作","market":"TW","currency":"TWD","symbol":"6116","name":"彩晶","shares":3000.0,"cost":10.31,"price":10.31},
    {"account":"永豐銀行｜核心帳戶","purpose":"價差操作","market":"TW","currency":"TWD","symbol":"6558","name":"興能高","shares":2000.0,"cost":36.0,"price":36.0},
    {"account":"永豐銀行｜核心帳戶","purpose":"價差操作","market":"TW","currency":"TWD","symbol":"6603","name":"富強鑫","shares":1000.0,"cost":26.64,"price":26.64},
    {"account":"永豐銀行｜核心帳戶","purpose":"價差操作","market":"TW","currency":"TWD","symbol":"6770","name":"力積電","shares":1000.0,"cost":63.79,"price":63.79},
    {"account":"永豐銀行｜核心帳戶","purpose":"核心長期","market":"US","currency":"USD","symbol":"NVDA","name":"NVIDIA","shares":1.0,"cost":142.95,"price":142.95},
    {"account":"永豐銀行｜核心帳戶","purpose":"退休長期","market":"US","currency":"USD","symbol":"QQQ","name":"Invesco QQQ","shares":1.55011,"cost":645.15,"price":645.15},
]

st.set_page_config(page_title="投資總控 Pro v3", page_icon="💼", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
.stApp{background:#F8F5EF;}
.block-container{padding-top:1rem;padding-bottom:4rem;}
[data-testid="stMetric"]{background:#FFFDF8;padding:18px;border-radius:20px;border:1px solid #E8E0D0;box-shadow:0 4px 14px rgba(0,0,0,.05);}
section[data-testid="stSidebar"]{background:#F3EEE4;}
div[data-testid="stDataFrame"]{background:#FFFDF8;border-radius:16px;}
h1{color:#4B443C;font-weight:800;} h2{color:#5A5248;} h3{color:#6B6258;}
p,label,span{color:#5A5248;}
.stTabs [data-baseweb="tab-list"]{gap:8px;}
.stTabs [data-baseweb="tab"]{background:#FFFDF8;border-radius:999px;padding:9px 18px;color:#5A5248;border:1px solid #E8E0D0;}
.stTabs [aria-selected="true"]{background:#EADCC4!important;color:#3F382F!important;}
.stButton>button{background:#D9C8A9;color:white;border:none;border-radius:15px;font-weight:700;padding:.6rem 1rem;}
.stButton>button:hover{background:#CDB894;color:white;border:none;}
.stDownloadButton>button{background:#C8B28A;color:white;border:none;border-radius:15px;font-weight:700;}
.stDownloadButton>button:hover{background:#B89E74;color:white;}
input,textarea,select{border-radius:12px!important;}
div[data-testid="stAlert"]{border-radius:15px;}
@media(max-width:768px){.block-container{padding-left:.8rem;padding-right:.8rem;}}
</style>
""", unsafe_allow_html=True)

def app_password():
    try:
        return st.secrets.get("APP_PASSWORD", DEFAULT_PASSWORD)
    except Exception:
        return DEFAULT_PASSWORD

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if st.session_state.authenticated:
        return True
    st.title("💼 投資總控 Pro v3")
    st.info("請輸入密碼後使用。預設密碼是 1688。")
    pw = st.text_input("密碼", type="password")
    if st.button("登入"):
        if pw == app_password():
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("密碼錯誤")
    return False

def connect():
    return sqlite3.connect(DB_PATH)

def ensure_columns(conn):
    cur = conn.cursor()
    for table, additions in {
        "trade_logs": {
            "qty":"REAL DEFAULT 0", "price":"REAL DEFAULT 0", "buy_fee":"REAL DEFAULT 0",
            "sell_fee":"REAL DEFAULT 0", "tax":"REAL DEFAULT 0", "realized_profit":"REAL DEFAULT 0",
            "cash_flow":"REAL DEFAULT 0"
        },
        "daily_assets": {
            "realized_profit":"REAL DEFAULT 0", "unrealized_profit":"REAL DEFAULT 0",
            "total_fee":"REAL DEFAULT 0", "dividend_income":"REAL DEFAULT 0", "cash_total":"REAL DEFAULT 0"
        }
    }.items():
        cur.execute(f"PRAGMA table_info({table})")
        cols = [x[1] for x in cur.fetchall()]
        for c, spec in additions.items():
            if c not in cols:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {c} {spec}")
    conn.commit()

def init_db():
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS holdings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account TEXT,purpose TEXT,market TEXT,currency TEXT,symbol TEXT,name TEXT,
        shares REAL,cost REAL,price REAL,last_update TEXT
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS daily_assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        record_date TEXT UNIQUE,total_asset REAL,total_cost REAL,total_profit REAL,
        realized_profit REAL DEFAULT 0,unrealized_profit REAL DEFAULT 0,total_fee REAL DEFAULT 0,
        dividend_income REAL DEFAULT 0,cash_total REAL DEFAULT 0
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS trade_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        log_date TEXT,account TEXT,symbol TEXT,action TEXT,note TEXT,
        qty REAL DEFAULT 0,price REAL DEFAULT 0,buy_fee REAL DEFAULT 0,
        sell_fee REAL DEFAULT 0,tax REAL DEFAULT 0,realized_profit REAL DEFAULT 0,cash_flow REAL DEFAULT 0
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS dividends (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pay_date TEXT,account TEXT,symbol TEXT,amount REAL,tax REAL DEFAULT 0,note TEXT
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS family_assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        record_date TEXT UNIQUE,
        xuan REAL DEFAULT 0,
        xian REAL DEFAULT 0,
        jie REAL DEFAULT 0,
        wen REAL DEFAULT 0,
        total REAL DEFAULT 0
    )""")
    cur.execute("SELECT COUNT(*) FROM family_assets")
    if cur.fetchone()[0] == 0 and Path("family_asset_records.csv").exists():
        try:
            fam = pd.read_csv("family_asset_records.csv")
            fam = fam.dropna(subset=["日期"])
            for _, r in fam.iterrows():
                total = float(r.get("萱",0) or 0) + float(r.get("憲",0) or 0) + float(r.get("傑",0) or 0) + float(r.get("文",0) or 0)
                cur.execute("""
                INSERT OR REPLACE INTO family_assets (record_date,xuan,xian,jie,wen,total)
                VALUES (?,?,?,?,?,?)
                """, (str(r.get("日期")), float(r.get("萱",0) or 0), float(r.get("憲",0) or 0), float(r.get("傑",0) or 0), float(r.get("文",0) or 0), total))
        except Exception:
            pass
    ensure_columns(conn)
    cur.execute("SELECT COUNT(*) FROM holdings")
    if cur.fetchone()[0] == 0:
        for h in DEFAULT_HOLDINGS:
            cur.execute("""
            INSERT INTO holdings (account,purpose,market,currency,symbol,name,shares,cost,price,last_update)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (h["account"],h["purpose"],h["market"],h["currency"],h["symbol"],h["name"],h["shares"],h["cost"],h["price"],"預設"))
    conn.commit()
    conn.close()

def load_table(table, order="id DESC"):
    conn = connect()
    df = pd.read_sql_query(f"SELECT * FROM {table} ORDER BY {order}", conn)
    conn.close()
    return df

def load_family_assets():
    conn = connect()
    df = pd.read_sql_query("SELECT * FROM family_assets ORDER BY record_date DESC", conn)
    conn.close()
    return df

def upsert_family_asset(record_date, xuan, xian, jie, wen):
    total = float(xuan) + float(xian) + float(jie) + float(wen)
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO family_assets (record_date,xuan,xian,jie,wen,total)
    VALUES (?,?,?,?,?,?)
    ON CONFLICT(record_date) DO UPDATE SET
      xuan=excluded.xuan,
      xian=excluded.xian,
      jie=excluded.jie,
      wen=excluded.wen,
      total=excluded.total
    """, (record_date, xuan, xian, jie, wen, total))
    conn.commit()
    conn.close()

def load_holdings():
    conn = connect()
    df = pd.read_sql_query("SELECT * FROM holdings", conn)
    conn.close()
    return df

def save_holdings(df):
    conn = connect()
    df.to_sql("holdings", conn, if_exists="replace", index=False)
    conn.close()

def add_log(log_date, account, symbol, action, note, qty, price, buy_fee, sell_fee, tax, realized_profit, cash_flow):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO trade_logs (log_date,account,symbol,action,note,qty,price,buy_fee,sell_fee,tax,realized_profit,cash_flow)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
    (log_date,account,symbol,action,note,qty,price,buy_fee,sell_fee,tax,realized_profit,cash_flow))
    conn.commit()
    conn.close()

def add_dividend(pay_date, account, symbol, amount, tax, note):
    conn = connect()
    cur = conn.cursor()
    cur.execute("INSERT INTO dividends (pay_date,account,symbol,amount,tax,note) VALUES (?,?,?,?,?,?)",
                (pay_date,account,symbol,amount,tax,note))
    conn.commit()
    conn.close()

def save_daily_asset(total_asset,total_cost,total_profit,realized_profit,unrealized_profit,total_fee,dividend_income,cash_total):
    conn = connect()
    cur = conn.cursor()
    d = date.today().isoformat()
    cur.execute("""
    INSERT INTO daily_assets (record_date,total_asset,total_cost,total_profit,realized_profit,unrealized_profit,total_fee,dividend_income,cash_total)
    VALUES (?,?,?,?,?,?,?,?,?)
    ON CONFLICT(record_date) DO UPDATE SET
      total_asset=excluded.total_asset,total_cost=excluded.total_cost,total_profit=excluded.total_profit,
      realized_profit=excluded.realized_profit,unrealized_profit=excluded.unrealized_profit,total_fee=excluded.total_fee,
      dividend_income=excluded.dividend_income,cash_total=excluded.cash_total
    """,(d,total_asset,total_cost,total_profit,realized_profit,unrealized_profit,total_fee,dividend_income,cash_total))
    conn.commit()
    conn.close()

def yahoo_symbol(row):
    sym = str(row["symbol"]).upper().strip()
    if row["market"] == "US":
        return sym
    if row["market"] == "CASH":
        return None
    return f"{sym}.TW"

def fetch_price(row):
    if yf is None or row["market"] == "CASH":
        return None
    try:
        data = yf.Ticker(yahoo_symbol(row)).history(period="5d")
        if not data.empty:
            return float(data["Close"].dropna().iloc[-1])
    except Exception:
        pass
    if row["market"] == "TW":
        try:
            data = yf.Ticker(f'{str(row["symbol"]).upper().strip()}.TWO').history(period="5d")
            if not data.empty:
                return float(data["Close"].dropna().iloc[-1])
        except Exception:
            pass
    return None

def fetch_usd_twd():
    if yf is None:
        return 32.0
    try:
        data = yf.Ticker("TWD=X").history(period="5d")
        if not data.empty:
            return float(data["Close"].dropna().iloc[-1])
    except Exception:
        pass
    return 32.0

def calc_values(df, usd_twd):
    df = df.copy()
    fx = df["currency"].map(lambda x: usd_twd if x == "USD" else 1.0)
    df["台幣市值"] = df["shares"] * df["price"] * fx
    df["台幣成本"] = df["shares"] * df["cost"] * fx
    cash_mask = df["market"].eq("CASH")
    df.loc[cash_mask, "台幣市值"] = df.loc[cash_mask, "price"] * fx[cash_mask]
    df.loc[cash_mask, "台幣成本"] = df.loc[cash_mask, "cost"] * fx[cash_mask]
    df["未實現損益"] = df["台幣市值"] - df["台幣成本"]
    df["報酬率"] = df["未實現損益"] / df["台幣成本"].replace(0, pd.NA) * 100
    return df

def money(x):
    return f"{x:,.0f}"

def realized_summary(logs):
    if logs.empty:
        return 0,0,0,0,0
    realized = logs["realized_profit"].fillna(0).sum()
    total_fee = logs["buy_fee"].fillna(0).sum() + logs["sell_fee"].fillna(0).sum() + logs["tax"].fillna(0).sum()
    tax = logs["tax"].fillna(0).sum()
    net = realized - total_fee
    cash_flow = logs["cash_flow"].fillna(0).sum()
    return realized,total_fee,tax,net,cash_flow

def dividend_summary(divs):
    if divs.empty:
        return 0,0,0
    gross = divs["amount"].fillna(0).sum()
    tax = divs["tax"].fillna(0).sum()
    net = gross - tax
    return gross,tax,net

if not check_password():
    st.stop()

init_db()
df = load_holdings()
logs = load_table("trade_logs", "log_date DESC,id DESC")
divs = load_table("dividends", "pay_date DESC,id DESC")

with st.sidebar:
    st.header("設定")
    usd_twd = st.number_input("USD/TWD 匯率", value=float(fetch_usd_twd()), step=0.01)
    if st.button("🔄 更新全部市價", use_container_width=True):
        progress = st.progress(0)
        updates = []
        status = st.empty()
        for i, row in df.iterrows():
            p = fetch_price(row)
            if p:
                df.loc[i,"price"] = p
                df.loc[i,"last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                updates.append(f"✅ {row['symbol']} → {p:.2f}")
            else:
                updates.append(f"⚠️ {row['symbol']} 保留 {row['price']}")
            progress.progress((i+1)/len(df))
        save_holdings(df)
        status.write("\n".join(updates))
        st.success("市價更新完成")
        st.rerun()

st.title("💼 投資總控 Pro v3｜個人資產管理系統")
st.caption("總資產・已實現/未實現損益・手續費・現金部位・股息・月年統計・價差戶績效")

dfv = calc_values(df, usd_twd)
gross_realized,total_fee,total_tax,net_realized,cash_flow = realized_summary(logs)
gross_dividend,dividend_tax,net_dividend = dividend_summary(divs)
total_asset = dfv["台幣市值"].sum()
total_cost = dfv["台幣成本"].sum()
unrealized_profit = dfv["未實現損益"].sum()
cash_total = dfv.loc[dfv["purpose"].eq("現金"), "台幣市值"].sum()
total_profit = unrealized_profit + net_realized + net_dividend

c1,c2,c3,c4 = st.columns(4)
c1.metric("目前總資產", f"{money(total_asset)} 元")
c2.metric("未實現損益", f"{money(unrealized_profit)} 元")
c3.metric("已實現損益淨額", f"{money(net_realized)} 元")
c4.metric("現金部位", f"{money(cash_total)} 元")

c5,c6,c7,c8 = st.columns(4)
c5.metric("總成本", f"{money(total_cost)} 元")
c6.metric("股息淨收入", f"{money(net_dividend)} 元")
c7.metric("累計手續費/稅", f"{money(total_fee + dividend_tax)} 元")
c8.metric("總損益估算", f"{money(total_profit)} 元")

if st.button("📌 儲存今日資產紀錄", use_container_width=True):
    save_daily_asset(total_asset,total_cost,total_profit,net_realized,unrealized_profit,total_fee,net_dividend,cash_total)
    st.success("已儲存今日資產紀錄")

backup = {
    "holdings": df.to_dict(orient="records"),
    "trade_logs": logs.to_dict(orient="records"),
    "dividends": divs.to_dict(orient="records"),
    "daily_assets": load_table("daily_assets","record_date DESC").to_dict(orient="records"),
    "family_assets": load_family_assets().to_dict(orient="records"),
}
st.download_button("⬇️ 匯出完整備份 JSON", data=pd.Series(backup).to_json(force_ascii=False, indent=2),
                   file_name="投資總控Pro_v3備份.json", mime="application/json", use_container_width=True)

tabs = st.tabs(["總覽","持股管理","00631L操作","交易/已實現","股息收入","每日資產","損益分析","資產配置","家庭資產"])

with tabs[0]:
    st.subheader("各帳戶金額")
    acct = dfv.groupby("account")[["台幣市值","台幣成本","未實現損益"]].sum().reset_index()
    acct["報酬率"] = acct["未實現損益"] / acct["台幣成本"].replace(0,pd.NA) * 100
    st.dataframe(acct, use_container_width=True, hide_index=True)
    st.subheader("用途分類")
    purpose = dfv.groupby("purpose")[["台幣市值","台幣成本","未實現損益"]].sum().reset_index()
    purpose["報酬率"] = purpose["未實現損益"] / purpose["台幣成本"].replace(0,pd.NA) * 100
    st.dataframe(purpose, use_container_width=True, hide_index=True)

with tabs[1]:
    st.subheader("持股總表")
    show_cols = ["id","account","purpose","market","currency","symbol","name","shares","cost","price","台幣市值","台幣成本","未實現損益","報酬率","last_update"]
    edited = st.data_editor(dfv[show_cols], use_container_width=True, num_rows="dynamic", hide_index=True)
    if st.button("💾 儲存持股修改"):
        save_cols = ["id","account","purpose","market","currency","symbol","name","shares","cost","price","last_update"]
        save_holdings(edited[save_cols])
        st.success("已儲存")
        st.rerun()

with tabs[2]:
    st.subheader("00631L 分批獲利計畫")
    target = df[df["symbol"].str.upper()=="00631L"]
    if target.empty:
        st.warning("找不到00631L")
    else:
        h = target.iloc[0]
        a,b,c,d = st.columns(4)
        sell1 = a.number_input("第一批賣出價", value=39.0, step=0.1)
        sell2 = b.number_input("第二批賣出價", value=44.0, step=0.1)
        sell3 = c.number_input("第三批賣出價", value=50.0, step=0.1)
        sell_ratio = d.number_input("每批賣出比例%", value=20.0, step=1.0)/100
        sell_shares = int(h["shares"] * sell_ratio)
        remain = h["shares"]
        rows, alloc = [], []
        for n, sp in enumerate([sell1,sell2,sell3],1):
            amount = sell_shares * sp
            profit = sell_shares * (sp - h["cost"])
            remain -= sell_shares
            rows.append({"批次":f"第{n}批","目標價":sp,"賣出股數":sell_shares,"賣出金額":amount,"預估毛獲利":profit,"剩餘股數":remain,"狀態":"已達標" if h["price"]>=sp else "未達標"})
            alloc.append({"批次":f"第{n}批","毛獲利":profit,"QQQ 30%":profit*.3,"SMH 20%":profit*.2,"保留現金 30%":profit*.3,"價差戶 20%":profit*.2})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.subheader("獲利分配")
        st.dataframe(pd.DataFrame(alloc), use_container_width=True, hide_index=True)
        nxt = [r for r in rows if r["狀態"]=="未達標"]
        if nxt:
            st.info(f"下一步：00631L 到 {nxt[0]['目標價']} 元，賣出 {nxt[0]['賣出股數']} 股。")
        else:
            st.success("三批目標都已達標。")
        high = st.number_input("最近高點/下跌加碼參考價", value=50.0, step=0.1)
        st.dataframe(pd.DataFrame([
            {"跌幅":"-10%","參考價":high*.9,"動作":"投入保留現金30%"},
            {"跌幅":"-15%","參考價":high*.85,"動作":"再投入保留現金30%"},
            {"跌幅":"-20%","參考價":high*.8,"動作":"投入剩餘保留現金40%"},
        ]), use_container_width=True, hide_index=True)

with tabs[3]:
    st.subheader("新增交易紀錄 / 已實現損益")
    with st.form("trade_form"):
        c1,c2,c3 = st.columns(3)
        ldate = c1.date_input("日期", value=date.today())
        laccount = c2.selectbox("帳戶", sorted(df["account"].unique()))
        lsymbol = c3.text_input("標的", value="00631L")
        c4,c5,c6 = st.columns(3)
        action = c4.selectbox("動作", ["買進","賣出","加碼","停利","停損","轉入長期帳戶","轉入價差帳戶","現金轉入","現金轉出"])
        qty = c5.number_input("股數/數量", value=0.0, step=1.0)
        trade_price = c6.number_input("成交價", value=0.0, step=0.01)
        c7,c8,c9,c10 = st.columns(4)
        buy_fee = c7.number_input("買進手續費", value=0.0, step=1.0)
        sell_fee = c8.number_input("賣出手續費", value=0.0, step=1.0)
        tax = c9.number_input("證交稅/交易稅", value=0.0, step=1.0)
        realized_profit = c10.number_input("已實現毛損益", value=0.0, step=1.0)
        cash_flow = st.number_input("現金流入/流出（流入正數、流出負數）", value=0.0, step=1.0)
        note = st.text_area("內容")
        submitted = st.form_submit_button("新增交易")
        if submitted:
            add_log(ldate.isoformat(),laccount,lsymbol,action,note,qty,trade_price,buy_fee,sell_fee,tax,realized_profit,cash_flow)
            st.success("已新增")
            st.rerun()
    logs_show = load_table("trade_logs","log_date DESC,id DESC")
    if not logs_show.empty:
        logs_show["淨已實現損益"] = logs_show["realized_profit"].fillna(0)-logs_show["buy_fee"].fillna(0)-logs_show["sell_fee"].fillna(0)-logs_show["tax"].fillna(0)
        kw = st.text_input("搜尋交易紀錄（代碼/備註/帳戶）")
        if kw:
            mask = logs_show.astype(str).apply(lambda col: col.str.contains(kw, case=False, na=False)).any(axis=1)
            logs_show = logs_show[mask]
    st.dataframe(logs_show, use_container_width=True, hide_index=True)

with tabs[4]:
    st.subheader("新增股息收入")
    with st.form("div_form"):
        c1,c2,c3 = st.columns(3)
        pdate = c1.date_input("入帳日", value=date.today())
        acc = c2.selectbox("帳戶", sorted(df["account"].unique()), key="divacc")
        sym = c3.text_input("標的", value="2330")
        c4,c5 = st.columns(2)
        amount = c4.number_input("股息金額", value=0.0, step=1.0)
        tax = c5.number_input("扣稅/匯費", value=0.0, step=1.0)
        note = st.text_area("備註", key="divnote")
        if st.form_submit_button("新增股息"):
            add_dividend(pdate.isoformat(),acc,sym,amount,tax,note)
            st.success("已新增股息")
            st.rerun()
    divs_show = load_table("dividends","pay_date DESC,id DESC")
    if not divs_show.empty:
        divs_show["股息淨額"] = divs_show["amount"].fillna(0)-divs_show["tax"].fillna(0)
    st.dataframe(divs_show, use_container_width=True, hide_index=True)

with tabs[5]:
    st.subheader("每日資產變化")
    daily = load_table("daily_assets","record_date DESC")
    if not daily.empty:
        daily["較前次變化"] = daily["total_asset"].diff(-1)
        st.dataframe(daily, use_container_width=True, hide_index=True)
        chart_df = daily.sort_values("record_date")
        st.line_chart(chart_df.set_index("record_date")[["total_asset","unrealized_profit","realized_profit"]])
    else:
        st.info("尚未有每日資產紀錄。")

with tabs[6]:
    st.subheader("損益分析")
    logs2 = load_table("trade_logs","log_date DESC,id DESC")
    if not logs2.empty:
        logs2["淨已實現損益"] = logs2["realized_profit"].fillna(0)-logs2["buy_fee"].fillna(0)-logs2["sell_fee"].fillna(0)-logs2["tax"].fillna(0)
        logs2["月份"] = pd.to_datetime(logs2["log_date"]).dt.to_period("M").astype(str)
        logs2["年度"] = pd.to_datetime(logs2["log_date"]).dt.year.astype(str)
        st.write("依標的")
        st.dataframe(logs2.groupby("symbol")[["realized_profit","buy_fee","sell_fee","tax","淨已實現損益"]].sum().reset_index(), use_container_width=True, hide_index=True)
        st.write("依帳戶")
        st.dataframe(logs2.groupby("account")[["realized_profit","buy_fee","sell_fee","tax","淨已實現損益"]].sum().reset_index(), use_container_width=True, hide_index=True)
        st.write("依月份")
        st.dataframe(logs2.groupby("月份")[["realized_profit","buy_fee","sell_fee","tax","淨已實現損益"]].sum().reset_index(), use_container_width=True, hide_index=True)
        st.write("依年度")
        st.dataframe(logs2.groupby("年度")[["realized_profit","buy_fee","sell_fee","tax","淨已實現損益"]].sum().reset_index(), use_container_width=True, hide_index=True)
    else:
        st.info("尚未有交易紀錄。")

with tabs[7]:
    st.subheader("資產配置")
    st.write("依帳戶")
    acct_chart = dfv.groupby("account")["台幣市值"].sum()
    st.bar_chart(acct_chart)
    st.write("依用途")
    purpose_chart = dfv.groupby("purpose")["台幣市值"].sum()
    st.bar_chart(purpose_chart)
    st.write("前十大持股")
    top = dfv[dfv["purpose"]!="現金"].sort_values("台幣市值", ascending=False).head(10)
    st.dataframe(top[["symbol","name","account","purpose","台幣市值","未實現損益","報酬率"]], use_container_width=True, hide_index=True)


with tabs[8]:
    st.subheader("家庭資產紀錄")
    st.caption("已匯入 family_asset_records.csv，可新增每日紀錄並查看每位成員與家庭總資產變化。")

    fam = load_family_assets()

    with st.form("family_asset_form"):
        c1, c2, c3, c4, c5 = st.columns(5)
        fdate = c1.date_input("日期", value=date.today(), key="family_date")
        xuan = c2.number_input("萱", value=0.0, step=1000.0)
        xian = c3.number_input("憲", value=0.0, step=1000.0)
        jie = c4.number_input("傑", value=0.0, step=1000.0)
        wen = c5.number_input("文", value=0.0, step=1000.0)
        if st.form_submit_button("新增 / 更新家庭資產紀錄"):
            upsert_family_asset(fdate.isoformat(), xuan, xian, jie, wen)
            st.success("已新增 / 更新家庭資產紀錄")
            st.rerun()

    fam = load_family_assets()
    if not fam.empty:
        show = fam.copy()
        show = show.rename(columns={
            "record_date": "日期",
            "xuan": "萱",
            "xian": "憲",
            "jie": "傑",
            "wen": "文",
            "total": "家庭總資產"
        })
        show["較前次變化"] = show["家庭總資產"].diff(-1)
        st.dataframe(show[["日期","萱","憲","傑","文","家庭總資產","較前次變化"]], use_container_width=True, hide_index=True)

        chart = show.sort_values("日期").set_index("日期")[["萱","憲","傑","文","家庭總資產"]]
        st.line_chart(chart)

        latest = show.sort_values("日期").iloc[-1]
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("萱", f"{latest['萱']:,.0f} 元")
        c2.metric("憲", f"{latest['憲']:,.0f} 元")
        c3.metric("傑", f"{latest['傑']:,.0f} 元")
        c4.metric("文", f"{latest['文']:,.0f} 元")
        c5.metric("家庭總資產", f"{latest['家庭總資產']:,.0f} 元")

        csv = show.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ 匯出家庭資產紀錄 CSV", data=csv, file_name="家庭資產紀錄.csv", mime="text/csv", use_container_width=True)
    else:
        st.info("尚未有家庭資產紀錄。")
