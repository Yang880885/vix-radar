import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="獵人戰情室：波段導航儀 6.2", layout="wide")
st.title("🎯 台股波段轉折導航儀")
st.caption("雷達 6.2 終極防卡死版 | 導入強制超時機制，徹底消滅殭屍執行緒")

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
        # 【關鍵修復】：加入 timeout=5，最多只等 5 秒，防止 LINE API 卡死伺服器
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=5)
        if response.status_code == 200:
            return True
    except:
        pass
    return False

if st.sidebar.button("發送測試警報 🚀"):
    if line_token and line_user_id:
        if send_line_message("✅ 【戰情室廣播】指揮官，雷達 6.2 系統測試正常！", line_token, line_user_id):
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
            # 【關鍵修復】：加入 timeout=5 與 threads=False，5 秒抓不到就放棄，絕不卡死
            data = yf.download(ticker, period=period, progress=False, threads=False, timeout=5)
            if not data.empty and 'Close' in data.columns:
                series = data['Close']
                if isinstance(series, pd.DataFrame):
                    series = series.iloc[:, 0]
                series.name = ticker
                df_list.append(series)
        except Exception:
            continue # 發生錯誤或超時就跳過這檔，繼續抓下一檔
    
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
prev_diff = t_prev['^VIX9D'] - t_prev['^VIX']
diff_delta = diff_vix9d_vix - prev_diff

vvix_delta = t_latest['^VVIX'] - t_prev['^VVIX']
skew_delta = t_latest['^SKEW'] - t_prev['^SKEW']

sox_pct = ((t_latest['^SOX'] / t_prev['^SOX']) - 1) * 100
ndx_pct = ((t_latest['^NDX'] / t_prev['^NDX']) - 1) * 100
tsm_pct = ((t_latest['TSM'] / t_prev['TSM']) - 1) * 100

twd_latest = t_latest['TWD=X']
twd_delta = twd_latest - t_prev['TWD=X']
twd_ma5 = trad_data['TWD=X'].dropna().tail(5).mean() if 'TWD=X' in trad_data.columns else twd_latest

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
latest_rsi = float(rsi_14.iloc[-1]) if not rsi_14.dropna().empty else 50
rsi_delta = latest_rsi - float(rsi_14.iloc[-2]) if len(rsi_14.dropna()) >= 2 else 0

tw_open, tw_close = float(twii_data['Open'].iloc[-1]), float(twii_data['Close'].iloc[-1])
tw_high, tw_low = float(twii_data['High'].iloc[-1]), float(twii_data['Low'].iloc[-1])
body = abs(tw_open - tw_close)
lower_shadow = min(tw_open, tw_close) - tw_low
is_long_lower_shadow = (lower_shadow > body * 2) and (lower_shadow > (tw_high - max(tw_open, tw_close))) and (body > 0)

# --- 核心優化 2：進階 VIX 即時避險訊號邏輯 ---
is_vix_inverted = ratio_vix_vix3m > 1.05
is_short_panic = diff_vix9d_vix > 2.0

score = 0
if ratio_vix_vix3m > 1.0: score += 3
if latest_rsi < 30: score += 2
if is_long_lower_shadow: score += 2
if twd_latest < twd_ma5: score += 1
if t_latest['^SKEW'] > 140: score -= 2
if latest_rsi > 70: score -= 2
if twd_latest > twd_ma5: score -= 1
if tnx_latest > 4.5: score -= 1
if is_vix_inverted: score -= 3
if is_short_panic: score -= 2

# --- 自動警報觸發邏輯 ---
current_alert_msg = ""
if score >= 4:
    current_alert_msg = f"\n🚨【獵人紅色警報】\n🟢 強烈買進訊號！\n自動戰力評估高達 {score} 分！絕佳抄底買點已浮現，請立刻開啟雷達確認指令！"
elif score <= -4:
    current_alert_msg = f"\n🚨【獵人紅色警報】\n🔴 極度危險訊號！\n空方戰力高達 {abs(score)} 分！系統偵測到多重暴跌風險或 VIX 嚴重倒掛，請立刻確認避險部位！"

if current_alert_msg and line_token and line_user_id:
    if st.session_state.last_alert_msg != current_alert_msg:
        if send_line_message(current_alert_msg, line_token, line_user_id):
            st.session_state.last_alert_msg = current_alert_msg

# --- 🏆 頂部：綜合決策計分板 ---
st.markdown("## 🧠 AI 戰術總分")
if score >= 4:
    st.success(f"### 🟢 強烈買進 ({score} 分)\n**🎯 總部指令**：天時地利齊聚！血流成河中的絕佳買點，請鎖定強勢 ETF 分批重倉！")
elif score >= 1:
    st.info(f"### 🟡 偏多震盪 ({score} 分)\n**🎯 總部指令**：環境偏樂觀，可小資金試單，嚴防假突破。")
elif score <= -4:
    st.error(f"### 🔴 極度危險 ({score} 分)\n**🎯 總部指令**：空襲警報！外資撤退加風險飆升或 VIX 結構倒掛，千萬不可接刀。")
else:
    st.warning(f"### ⚪ 多空交戰 ({score} 分)\n**🎯 總部指令**：多空訊號抵銷，市場尋找方向，耐心等待。")

st.divider()

# --- 📈 戰區 1：台股結構 ---
st.markdown("### 📈 戰區 1：台股結構")
t1, t2, t3 = st.columns(3)
with t1:
    st.metric(label="大盤 RSI", value=f"{latest_rsi:.1f}", delta=f"{rsi_delta:.1f}")
with t2:
    if is_long_lower_shadow:
        st.metric(label="主力護盤", value="長下影線", delta="強力支撐", delta_color="off")
    else:
        st.metric(label="主力護盤", value="無", delta="一般", delta_color="off")
with t3:
    st.metric(label="櫃買指數", value=f"{tw_latest['^TWOII']:.2f}", delta=f"{twoii_pct:.2f}%")

st.divider()

# --- 🌐 戰區 2：恐慌波動 ---
st.markdown("### 🌐 戰區 2：恐慌波動 (⚠️紅向上=危險)")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("VIX 比值", f"{ratio_vix_vix3m:.2f}", delta=f"{ratio_delta:.2f}", delta_color="inverse")
with c2:
    st.metric("VVIX 避險", f"{t_latest['^VVIX']:.1f}", delta=f"{vvix_delta:.1f}", delta_color="inverse")
with c3:
    st.metric("SKEW 尾部", f"{t_latest['^SKEW']:.1f}", delta=f"{skew_delta:.1f}", delta_color="inverse")
with c4:
    st.metric("VIX 乖離", f"{diff_vix9d_vix:.2f}", delta=f"{diff_delta:.2f}", delta_color="inverse")

st.divider()

# --- 💸 戰區 3：資金風險 ---
st.markdown("### 💸 戰區 3：資金風險 (⚠️紅向上=撤退)")
f1, f2, f3 = st.columns(3)
with f1:
    st.metric("台幣匯率", f"{twd_latest:.2f}", delta=f"{twd_delta:.2f}", delta_color="inverse")
with f2:
    st.metric("美債殖利率", f"{tnx_latest:.2f}%", delta=f"{tnx_delta:.2f}%", delta_color="inverse")
with f3:
    st.metric("比特幣(USD)", f"{btc_latest:,.0f}", f"{btc_pct:.2f}%")

st.divider()

# --- 🦅 戰區 4：美股風向 ---
st.markdown("### 🦅 戰區 4：美股風向")
u1, u2, u3 = st.columns(3)
with u1:
    st.metric("費半指數", f"{t_latest['^SOX']:.2f}", f"{sox_pct:.2f}%")
with u2:
    st.metric("那斯達克", f"{t_latest['^NDX']:.2f}", f"{ndx_pct:.2f}%")
with u3:
    st.metric("台積電 ADR", f"{t_latest['TSM']:.2f}", f"{tsm_pct:.2f}%")

st.divider()

# --- 🔭 戰區 5：歷史回測 ---
st.markdown("### 🔭 戰區 5：鑑古知今")
@st.cache_data(ttl=300, show_spinner=False)
def fetch_hist_data():
    try:
        data = fetch_market_data_safe(["^VIX", "^VIX3M", "^TWII", "TWD=X"], "6mo")
        if not data.empty:
            return data.ffill()
    except:
        pass
    return pd.DataFrame()

hist_data = fetch_hist_data()

if not hist_data.empty and '^TWII' in hist_data.columns and '^VIX' in hist_data.columns and '^VIX3M' in hist_data.columns:
    c_chart1, c_chart2 = st.columns(2)
    with c_chart1:
        st.markdown("#### 恐慌 vs 台股")
        fig1 = make_subplots(specs=[[{"secondary_y": True}]])
        fig1.add_trace(go.Scatter(x=hist_data.index, y=hist_data['^TWII'], name="台股", line=dict(color='#2962ff')), secondary_y=False)
        fig1.add_trace(go.Scatter(x=hist_data.index, y=hist_data['^VIX']/hist_data['^VIX3M'], name="恐慌", line=dict(color='#ff3b3b', dash='dot')), secondary_y=True)
        fig1.add_hline(y=1.0, line_dash="solid", line_color="red", secondary_y=True)
        fig1.update_layout(height=350, margin=dict(l=0, r=0, t=30, b=0), hovermode="x unified")
        st.plotly_chart(fig1, use_container_width=True)

    if 'TWD=X' in hist_data.columns:
        with c_chart2:
            st.markdown("#### 熱錢 vs 台股")
            fig2 = make_subplots(specs=[[{"secondary_y": True}]])
            fig2.add_trace(go.Scatter(x=hist_data.index, y=hist_data['^TWII'], name="台股", line=dict(color='#2962ff')), secondary_y=False)
            fig2.add_trace(go.Scatter(x=hist_data.index, y=hist_data['TWD=X'], name="匯率", line=dict(color='#00c853', dash='dot')), secondary_y=True)
            fig2.update_layout(height=350, margin=dict(l=0, r=0, t=30, b=0), hovermode="x unified")
            st.plotly_chart(fig2, use_container_width=True)
