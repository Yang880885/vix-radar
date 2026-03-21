import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="獵人戰情室：波段導航儀 6.3", layout="wide")
st.title("🎯 台股波段轉折導航儀")
st.caption("雷達 6.3 動作回歸版 | 終極防卡死機制 + 戰術動作全數歸位")

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
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=5)
        if response.status_code == 200:
            return True
    except:
        pass
    return False

if st.sidebar.button("發送測試警報 🚀"):
    if line_token and line_user_id:
        if send_line_message("✅ 【戰情室廣播】指揮官，雷達 6.3 系統測試正常！", line_token, line_user_id):
            st.sidebar.success("✅ 測試警報已發射！請檢查 LINE。")
        else:
            st.sidebar.error("❌ 發送失敗，請檢查金鑰設定。")
    else:
        st.sidebar.warning("⚠️ 尚未設定金鑰。")

if "last_alert_msg" not in st.session_state:
    st.session_state.last_alert_msg = ""

# --- 核心優化 1：安全單檔抓取機制 + 強制超時 (Timeout) ---
@st.cache_data(ttl=300, show_spinner=False)
def fetch_market_data_safe(tickers, period="10d"):
    df_list = []
    for ticker in tickers:
        try:
            data = yf.download(ticker, period=period, progress=False, threads=False, timeout=5)
            if not data.empty and 'Close' in data.columns:
                series = data['Close']
                if isinstance(series, pd.DataFrame):
                    series = series.iloc[:, 0]
                series.name = ticker
                df_list.append(series)
        except Exception:
            continue 
    
    if df_list:
        combined_df = pd.concat(df_list, axis=1)
        return combined_df[combined_df.index.dayofweek < 5]
    return pd.DataFrame()

@st.cache_data(ttl=300, show_spinner=False)
def fetch_single_full_safe(ticker, period="2mo"):
    try:
        data = yf.download(ticker, period=period, progress=False, threads=False, timeout=5)
        if not data.empty:
            df = data.dropna(how='all')
            return df[df.index.dayofweek < 5]
    except Exception:
        pass
    return pd.DataFrame()

# --- 啟動畫面提示與資料抓取 ---
with st.spinner("📡 系統啟動中：正在與全球交易所建立安全連線..."):
    trad_tickers = ["^VIX", "^VIX3M", "^VVIX", "^SKEW", "^VIX9D", "^SOX", "^NDX", "TSM", "TWD=X", "^TNX"]
    trad_data = fetch_market_data_safe(trad_tickers, "10d")
    
    tw_tickers = ["^TWII", "^TWOII"]
    tw_data = fetch_market_data_safe(tw_tickers, "2mo")
    twii_data = fetch_single_full_safe("^TWII", "2mo")
    
    btc_full = fetch_single_full_safe("BTC-USD", "10d")

# --- 致命錯誤攔截器 ---
if trad_data.empty or tw_data.empty or twii_data.empty:
    st.error("🚨 嚴重錯誤：無法取得交易所即時數據！")
    st.warning("原因可能為：\n1. Yahoo API 伺服器暫時壅塞或阻擋連線\n2. 逢週末休市導致資料讀取異常\n\n👉 **系統已啟動防卡死機制，請稍等 1~2 分鐘後再重新整理網頁。**")
    st.stop()

# --- 數據計算區 ---
t_latest, t_prev = {}, {}
for col in trad_tickers:
    if col in trad_data.columns:
        valid_series = trad_data[col].dropna()
        if len(valid_series) >= 2:
            t_latest[col] = float(valid_series.iloc[-1])
            t_prev[col] = float(valid_series.iloc[-2])
            continue
    t_latest[col], t_prev[col] = 0.0001, 0.0001

tw_latest, tw_prev = {}, {}
for col in tw_tickers:
    if col in tw_data.columns:
        valid_series = tw_data[col].dropna()
        if len(valid_series) >= 2:
            tw_latest[col] = float(valid_series.iloc[-1])
            tw_prev[col] = float(valid_series.iloc[-2])
            continue
    tw_latest[col], tw_prev[col] = 0.0001, 0.0001

if not btc_full.empty and len(btc_full) >= 2:
    btc_latest = float(btc_full['Close'].iloc[-1])
    btc_prev = float(btc_full['Close'].iloc[-2])
else:
    btc_latest, btc_prev = 0.0001, 0.0001

ratio_vix_vix3m = t_latest['^VIX'] / t_latest['^VIX3M']
prev_ratio = t_prev['^VIX'] / t_prev['^VIX3M']
ratio_delta = ratio_vix_vix3m - prev_ratio

diff_vix9d_vix = t_latest['^VIX9D'] - t_latest['^VIX']
