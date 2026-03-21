import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="獵人戰情室：波段導航儀 6.0", layout="wide")
st.title("🎯 台股波段轉折導航儀")
st.caption("雷達 6.0 升級版 | 修復執行緒崩潰、加入快取機制、進階 VIX 避險與 LINE 防擾民系統")

# --- 側邊欄：純粹的通訊引擎 ---
st.sidebar.header("🤖 LINE 警報引擎")
try:
    line_token = st.secrets["LINE_TOKEN"]
    line_user_id = st.secrets["LINE_USER_ID"]
    st.sidebar.success("🔒 雲端警報待命中 (機密金鑰已受保護)")
except:
    line_token = st.sidebar.text_input("LINE Token", type="password")
    line_user_id = st.sidebar.text_input("User ID", type="password")

def send_line_message(message, token, user_id):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    payload = {"to": user_id, "messages": [{"type": "text", "text": message}]}
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            return True
    except:
        pass
    return False

if st.sidebar.button("發送測試警報 🚀"):
    if line_token and line_user_id:
        if send_line_message("✅ 【戰情室廣播】指揮官，雷達 6.0 系統測試正常！通訊管道 100% 暢通！", line_token, line_user_id):
            st.sidebar.success("✅ 測試警報已發射！請檢查 LINE。")
        else:
            st.sidebar.error("❌ 發送失敗，請檢查金鑰設定。")
    else:
        st.sidebar.warning("⚠️ 尚未設定金鑰。")

# --- 初始化 Session State 防止 LINE 重複發送 ---
if "last_alert_msg" not in st.session_state:
    st.session_state.last_alert_msg = ""

# --- 核心優化 1：加入快取機制並關閉多執行緒 ---
@st.cache_data(ttl=300) # 5分鐘更新一次，避免被 Yahoo 封鎖
def fetch_market_data(tickers, period="10d"):
    # threads=False 徹底解決 RuntimeError 崩潰問題
    raw_data = yf.download(tickers, period=period, threads=False)['Close'].dropna(how='all')
    return raw_data[raw_data.index.dayofweek < 5]

@st.cache_data(ttl=300)
def fetch_twii_full(period="2mo"):
    twii_data = yf.download("^TWII", period=period, threads=False).dropna(how='all')
    return twii_data[twii_data.index.dayofweek < 5]

@st.cache_data(ttl=300)
def fetch_btc():
    return yf.download("BTC-USD", period="10d", threads=False)['Close'].dropna()

# --- 抓取所有戰區資料 ---
trad_tickers = ["^VIX", "^VIX3M", "^VVIX", "^SKEW", "^VIX9D", "^SOX", "^NDX", "TSM", "TWD=X", "^TNX"]
trad_data = fetch_market_data(trad_tickers, "10d")

btc_data = fetch_btc()

tw_tickers = ["^TWII", "^TWOII"]
tw_data = fetch_market_data(tw_tickers, "2mo")
twii_data = fetch_twii_full("2mo")

# --- 數據計算區 ---
t_latest, t_prev = {}, {}
for col in trad_data.columns:
    valid_series = trad_data[col].dropna()
    if len(valid_series) >= 2:
        t_latest[col] = float(valid_series.iloc[-1])
        t_prev[col] = float(valid_series.iloc[-2])
    else:
        t_latest[col], t_prev[col] = 0.0001, 0.0001

btc_latest = float(btc_data.iloc[-1])
btc_prev = float(btc_data.iloc[-2])

tw_latest, tw_prev = {}, {}
for col in tw_data.columns:
    valid_series = tw_data[col].dropna()
    if len(valid_series) >= 2:
        tw_latest[col] = float(valid_series.iloc[-1])
        tw_prev[col] = float(valid_series.iloc[-2])
    else:
        tw_latest[col], tw_prev[col] = 0.0001, 0.0001

ratio_vix_vix3m = t_latest['^VIX'] / t_latest['^VIX3M']
prev_ratio = t_prev['^VIX'] / t_prev['^VIX3M']
ratio_delta = ratio_vix_vix3m - prev_ratio

diff_vix9d_vix = t_latest['^VIX9D'] - t_latest['^VIX']
prev_diff = t_prev['^VIX9D'] - t_prev['^VIX']
diff_delta = diff_vix9d_vix - prev_diff

vvix_delta = t_latest['^VVIX'] - t_prev['^VVIX']
skew_delta = t_latest['^SKEW'] - t_prev['^SKEW']

sox_pct = ((t_latest['^SOX'] / t_prev['^SOX']) - 1) * 100
ndx_pct = ((t_latest['^NDX'] / t_prev['^NDX']) - 1) * 100
tsm_pct = ((t_latest['TSM'] / t_prev['TSM']) - 1) * 100

twd_latest = t_latest['TWD=X']
twd_delta = twd_latest - t_prev['TWD=X']
twd_ma5 = trad_data['TWD=X'].dropna().tail(5).mean()

tnx_latest = t_latest['^TNX']
tnx_delta = tnx_latest - t_prev['^TNX']

btc_pct = ((btc_latest / btc_prev) - 1) * 100

twii_pct = ((tw_latest['^TWII'] / tw_prev['^TWII']) - 1) * 100
twoii_pct = ((tw_latest['^TWOII'] / tw_prev['^TWOII']) - 1) * 100
spread = twii_pct - twoii_pct 

delta = twii_data['Close'].diff()
gain = (delta.where(delta > 0, 0)).fillna(0)
loss = (-delta.where(delta < 0, 0)).fillna(0)
rs = gain.rolling(window=14, min_periods=1).mean() / loss.rolling(window=14, min_periods=1).mean()
rsi_14 = 100 - (100 / (1 + rs))
latest_rsi = float(rsi_14.iloc[-1])
rsi_delta = latest_rsi - float(rsi_14.iloc[-2])

tw_open, tw_close = float(twii_data['Open'].iloc[-1]), float(tw
