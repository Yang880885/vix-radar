import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime

st.set_page_config(page_title="獵人戰情室：波段導航儀 7.1", layout="wide")
st.title("🎯 台股波段轉折導航儀")
st.caption("雷達 7.1 完整修復版 | 折線圖全面歸位 + 強化籌碼突破引擎")

# --- 防連發引擎 ---
@st.cache_resource
def get_alert_memory():
    return {"last_state": "NONE"}
alert_memory = get_alert_memory()

# --- 側邊欄：純粹的通訊引擎 ---
st.sidebar.header("🤖 LINE 警報引擎")
try:
    line_token = st.secrets["LINE_TOKEN"]
    line_user_id = st.secrets["LINE_USER_ID"]
    st.sidebar.success("🔒 雲端警報待命中")
except:
    line_token = st.sidebar.text_input("LINE Token", type="password")
    line_user_id = st.sidebar.text_input("User ID", type="password")

def send_line_message(message, token, user_id):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    payload = {"to": user_id, "messages": [{"type": "text", "text": message}]}
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=5)
        if response.status_code == 200: return True
    except: pass
    return False

if st.sidebar.button("發送測試警報 🚀"):
    if line_token and line_user_id:
        if send_line_message("✅ 【戰情室廣播】指揮官，雷達 7.1 系統測試正常！", line_token, line_user_id):
            st.sidebar.success("✅ 測試警報已發射！")
        else: st.sidebar.error("❌ 發送失敗，請檢查金鑰。")
    else: st.sidebar.warning("⚠️ 尚未設定金鑰。")

# ==========================================
# 核心資料抓取 1：全球金融與宏觀數據
# ==========================================
@st.cache_data(ttl=300, show_spinner=False)
def fetch_master_data():
    tickers = ["^VIX", "^VIX3M", "^VVIX", "^SKEW", "^VIX9D", "^SOX", "^NDX", "TSM", "TWD=X", "^TNX", "^TWII", "^TWOII", "BTC-USD"]
    results = {}
    for t in tickers:
        try:
            hist = yf.Ticker(t).history(period="2mo")
            if not hist.empty and 'Close' in hist.columns: results[t] = hist['Close']
        except Exception: continue
    if results:
        df = pd.DataFrame(results)
        return df[df.index.dayofweek < 5].ffill()
    return pd.DataFrame()

@st.cache_data(ttl=300, show_spinner=False)
def fetch_twii_kline():
    try:
        hist = yf.Ticker("^TWII").history(period="2mo")
        if not hist.empty: return hist[hist.index.dayofweek < 5].ffill()
    except: pass
    return pd.DataFrame()

# ==========================================
# 核心資料抓取 2：台灣證交所盤後籌碼 (每日 15:30 後更新)
# ==========================================
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_twse_chips():
    # 強化偽裝參數，避免被證交所擋下
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": "https://www.twse.com.tw/"
    }
    macro_data, trust_data, foreign_data = [], [], []
    try:
        r1 = requests.get("https://www.twse.com.tw/rwd/zh/fund/BFI82U?response=json", headers=headers, timeout=8).json()
        if 'data' in r1: macro_data = r1['data']
        
        r2 = requests.get("https://www.twse.com.tw/rwd/zh/fund/TWT44U?response=json", headers=headers, timeout=8).json()
        if 'data' in r2: trust_data = r2['data']
        
        r3 = requests.get("https://www.twse.com.tw/rwd/zh/fund/TWT38U?response=json", headers=headers, timeout=8).json()
        if 'data' in r3: foreign_data = r3['data']
    except Exception:
        pass
    return macro_data, trust_data, foreign_data

with st.spinner("📡 系統啟動中：讀取全球交易所與籌碼數據..."):
    master_data = fetch_master_data()
    twii_data = fetch_twii_kline()
    macro_chips, trust_chips, foreign_chips = fetch_twse_chips()

# --- 系統健康檢查燈號 ---
st.markdown("### 🚦 系統診斷面板")
health_col1, health_col2, health_col3 = st.columns(3)
data_error = master_data.empty or twii_data.empty

with health_col1:
    if not data_error: st.success("🟢 全球 API 連線正常")
    else: st.error("🔴 交易所 API 遭阻擋")
with health_col2:
    if macro_chips: st.success("🟢 證交所籌碼連線正常")
    else: st.warning("🟡 籌碼尚未更新 (或證交所阻擋海外IP)")
with health_col3:
    if not data_error:
        last_date = master_data.index[-1].strftime("%Y-%m-%d")
        st.success(f"🟢 數據更新至: {last_date}")
    else: st.error("🔴 啟動備用假數據模式")

st.divider()

if data_error:
    dates = pd.date_range(end=pd.Timestamp.today(), periods=6, freq='B')
    dummy_dict = {t: [100.0]*6 for t in ["^VIX", "^VIX3M", "^VVIX", "^SKEW", "^VIX9D", "^SOX", "^NDX", "TSM", "TWD=X", "^TNX", "^TWII", "^TWOII", "BTC-USD"]}
    master_data = pd.DataFrame(dummy_dict, index=dates)
    twii_data = pd.DataFrame({'Open': [100]*6, 'High': [100]*6, 'Low': [100]*6, 'Close': [100]*6, 'Volume': [1000]*6}, index=dates)

# ==========================================
# 數據安全讀取與運算區
# ==========================================
t_latest, t_prev = {}, {}
for col in master_data.columns:
    valid_series = master_data[col].dropna()
    if len(valid_series) >= 2:
        t_latest[col], t_prev[col] = float(valid_series.iloc[-1]), float(valid_series.iloc[-2])
    else: t_latest[col], t_prev[col] = 0.0001, 0.0001

def get_val(ticker, latest=True): return t_latest.get(ticker, 0.0001) if latest else t_prev.get(ticker, 0.0001)

ratio_vix_vix3m = get_val('^VIX') / get_val('^VIX3M')
ratio_delta = ratio_vix_vix3m - (get_val('^VIX', False) / get_val('^VIX3M', False))
diff_vix9d_vix = get_val('^VIX9D') - get_val('^VIX')
diff_delta = diff_vix9d_vix - (get_val('^VIX9D', False) - get_val('^VIX', False))
vvix_latest = get_val('^VVIX')
vvix_delta = vvix_latest - get_val('^VVIX', False)
skew_delta = get_val('^SKEW') - get_val('^SKEW', False)
sox_pct = ((get_val('^SOX') / get_val('^SOX', False)) - 1) * 100
ndx_pct = ((get_val('^NDX') / get_val('^NDX', False)) - 1) * 100
tsm_pct = ((get_val('TSM') / get_val('TSM', False)) - 1) * 100
twd_latest = get_val('TWD=X')
twd_delta = twd_latest - get_val('TWD=X', False)
twd_ma5 = master_data['TWD=X'].dropna().tail(5).mean() if 'TWD=X' in master_data.columns and len(master_data['TWD=X'].dropna()) >= 5 else twd_latest
tnx_latest = get_val('^TNX')
tnx_delta = tnx_latest - get_val('^TNX', False)
btc_pct = ((get_val('BTC-USD') / get_val('BTC-USD', False)) - 1) * 100
twii_pct = ((get_val('^TWII') / get_val('^TWII', False)) - 1) * 100
twoii_pct = ((get_val('^TWOII') / get_val('^TWOII', False)) - 1) * 100
spread = twii_pct - twoii_pct 

delta = twii_data['Close'].diff()
gain, loss = (delta.where(delta > 0, 0)).fillna(0), (-delta.where(delta < 0, 0)).fillna(0)
rs = gain.rolling(window=14, min_periods=1).mean() / loss.rolling(window=14, min_periods=1).mean()
rsi_14 = 100 - (100 / (1 + rs))
latest_rsi = float(rsi_14.iloc[-1]) if not rsi_14.dropna().empty else 50
rsi_delta = latest_rsi - float(rsi_14.iloc[-2]) if len(rsi_14.dropna()) >= 2 else 0

tw_open, tw_close = float(twii_data['Open'].iloc[-
