import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="獵人戰情室：波段導航儀 5.6", layout="wide")
st.title("🎯 台股波段轉折導航儀")
st.caption("雷達 5.6 核心版 | 手機介面優化 | 週末抗干擾")

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
        requests.post(url, headers=headers, data=json.dumps(payload))
    except:
        pass

# --- 抓取所有戰區資料 (🔥 徹底剔除週末幽靈數據) ---
# 1. 傳統資產 (只保留週一到週五)
trad_tickers = ["^VIX", "^VIX3M", "^VVIX", "^SKEW", "^VIX9D", "^SOX", "^NDX", "TSM", "TWD=X", "^TNX"]
trad_data = yf.download(trad_tickers, period="10d")['Close'].dropna(how='all')
trad_data = trad_data[trad_data.index.dayofweek < 5].ffill()

# 2. 比特幣 (24小時無休)
btc_data = yf.download("BTC-USD", period="10d")['Close'].dropna()

# 3. 台股大盤與櫃買 (只保留週一到週五)
tw_tickers = ["^TWII", "^TWOII"]
tw_data = yf.download(tw_tickers, period="2mo")['Close'].dropna(how='all')
tw_data = tw_data[tw_data.index.dayofweek < 5].ffill()
twii_data = yf.download("^TWII", period="2mo").dropna(how='all')
twii_data = twii_data[twii_data.index.dayofweek < 5]

# --- 數據計算區 ---
trad_latest = trad_data.iloc[-1]
trad_prev = trad_data.iloc[-2]

btc_latest = float(btc_data.iloc[-1])
btc_prev = float(btc_data.iloc[-2])

ratio_vix_vix3m = trad_latest['^VIX'] / trad_latest['^VIX3M']
prev_ratio = trad_prev['^VIX'] / trad_prev['^VIX3M']
ratio_delta = ratio_vix_vix3m - prev_ratio

diff_vix9d_vix = trad_latest['^VIX9D'] - trad_latest['^VIX']
prev_diff = trad_prev['^VIX9D'] - trad_prev['^VIX']
diff_delta = diff_vix9d_vix - prev_diff

vvix_delta = trad_latest['^VVIX'] - trad_prev['^VVIX']
skew_delta = trad_latest['^SKEW'] - trad_prev['^SKEW']

sox_pct = ((trad_latest['^SOX'] / trad_prev['^SOX']) - 1) * 100
ndx_pct = ((trad_latest['^NDX'] / trad_prev['^NDX']) - 1) * 100
tsm_pct = ((trad_latest['TSM'] / trad_prev['TSM']) - 1) * 100

twd_latest = trad_latest['TWD=X']
twd_delta = twd_latest - trad_prev['TWD=X']
twd_ma5 = trad_data['TWD=X'].tail(5).mean()

tnx_latest = trad_latest['^TNX']
tnx_delta = tnx_latest - trad_prev['^TNX']

btc_pct = ((btc_latest / btc_prev) - 1) * 100

twii_pct = ((tw_data['^TWII'].iloc[-1] / tw_data['^TWII'].iloc[-2]) - 1) * 100
twoii_pct = ((tw_data['^TWOII'].iloc[-1] / tw_data['^TWOII'].iloc[-2]) - 1) * 100
spread = twii_pct - twoii_pct 

# 技術面計算
delta = twii_data['Close'].diff()
gain = (delta.where(delta > 0, 0)).fillna(0)
loss = (-delta.where(delta < 0, 0)).fillna(0)
rs = gain.rolling(window=14, min_periods=1).mean() / loss.rolling(window=14, min_periods=1).mean()
rsi_14 = 100 - (100 / (1 + rs))

latest_rsi = float(rsi_14.iloc[-1])
rsi_delta = latest_rsi - float(rsi_14.iloc[-2])

tw_open, tw_close = float(twii_data['Open'].iloc[-1]), float(twii_data['Close'].iloc[-1])
tw_high, tw_low = float(twii_data['High'].iloc[-1]), float(twii_data['Low'].iloc[-1])
body = abs(tw_open - tw_close)
lower_shadow = min(tw_open, tw_close) - tw_low
is_long_lower_shadow = (lower_shadow > body * 2) and (lower_shadow > (tw_high - max(tw_open, tw_close))) and (body > 0)

# --- AI 戰術大腦：綜合計分 ---
score = 0
if ratio_vix_vix3m > 1.0: score += 3
if latest_rsi < 30: score += 2
if is_long_lower_shadow: score += 2
if twd_latest < twd_ma5: score += 1
if trad_latest['^SKEW'] > 140: score -= 2
if latest_rsi > 70: score -= 2
if twd_latest > twd_ma5: score -= 1
if tnx_latest > 4.5: score -= 1

# --- 🏆 頂部：綜合決策計分板 ---
st.markdown("## 🧠 AI 戰術總分")
if score >= 4:
    st.success(f"### 🟢 強烈買進 ({score} 分)\n天時地利齊聚！請立刻鎖定強勢 ETF 分批重倉！")
elif score >= 1:
    st.info(f"### 🟡 偏多震盪 ({score} 分)\n環境偏樂觀，可小資金試單，嚴設停損。")
elif score <= -3:
    st.error(f"### 🔴 極度危險 ({score} 分)\n空襲警報！千萬不可接刀，滿手現金觀望。")
else:
    st.warning(f"### ⚪ 多空交戰 ({score} 分)\n多空訊號抵銷，耐心等待轉折浮現。")

st.divider()

# --- 📈 戰區 1：台股結構 ---
st.markdown("### 📈 戰區 1：台股結構")
t1, t2, t3 = st.columns(3)
with t1:
    st.metric(label="大盤 RSI", value=f"{latest_rsi:.1f}", delta=f"{rsi_delta:.1f}")
    if latest_rsi < 30: st.error("🚨 嚴重超賣，準備搶反彈")
    elif latest_rsi > 70: st.warning("⚠️ 高檔超買，勿追高")
    else: st.success("✅ 指標位階適中")
with t2:
    if is_long_lower_shadow:
        st.metric(label="主力護盤", value="長下影線", delta="強力支撐", delta_color="off")
        st.error("🎯 洗盤結束，準備抄底")
    else:
        st.metric(label="主力護盤", value="無", delta="一般", delta_color="off")
        st.success("✅ 尚無單日反轉訊號")
with t3:
    st.metric(label="櫃買指數", value=f"{tw_data['^TWOII'].iloc[-1]:.2f}", delta=f"{twoii_pct:.2f}%")
    if spread > 1.0 and twii_pct > 0: st.error("🚨 拉積盤！避開中小型")
    elif twoii_pct > twii_pct and twoii_pct > 0: st.success("🔥 內資噴發！做多中小型")
    else: st.info("⚖️ 結構正常同步")

st.divider()

# --- 🌐 戰區 2：恐慌波動 ---
st.markdown("### 🌐 戰區 2：恐慌波動 (⚠️紅向上=危險)")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("VIX 比值", f"{ratio_vix_vix3m:.2f}", delta=f"{ratio_delta:.2f}", delta_color="inverse")
with c2:
    st.metric("VVIX 避險", f"{trad_latest['^VVIX']:.1f}", delta=f"{vvix_delta:.1f}", delta_color="inverse")
with c3:
    st.metric("SKEW 尾部", f"{trad_latest['^SKEW']:.1f}", delta=f"{skew_delta:.1f}", delta_color="inverse")
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
    st.metric("費半指數", f"{trad_latest['^SOX']:.2f}", f"{sox_pct:.2f}%")
with u2:
    st.metric("那斯達克", f"{trad_latest['^NDX']:.2f}", f"{ndx_pct:.2f}%")
with u3:
    st.metric("台積電 ADR", f"{trad_latest['TSM']:.2f}", f"{tsm_pct:.2f}%")

st.divider()

# --- 🔭 戰區 5：歷史回測 ---
st.markdown("### 🔭 戰區 5：鑑古知今")
hist_data = yf.download(["^VIX", "^VIX3M", "^TWII", "TWD=X"], period="6mo")['Close'].dropna(how='all')
hist_data = hist_data[hist_data.index.dayofweek < 5].ffill()

c_chart1, c_chart2 = st.columns(2)
with c_chart1:
    st.markdown("#### 恐慌 vs 台股")
    fig1 = make_subplots(specs=[[{"secondary_y": True}]])
    fig1.add_trace(go.Scatter(x=hist_data.index, y=hist_data['^TWII'], name="台股", line=dict(color='#2962ff')), secondary_y=False)
    fig1.add_trace(go.Scatter(x=hist_data.index, y=hist_data['^VIX']/hist_data['^VIX3M'], name="恐慌", line=dict(color='#ff3b3b', dash='dot')), secondary_y=True)
    fig1.add_hline(y=1.0, line_dash="solid", line_color="red", secondary_y=True)
    fig1.update_layout(height=350, margin=dict(l=0, r=0, t=30, b=0), hovermode="x unified", legend=dict(yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig1, use_container_width=True)

with c_chart2:
    st.markdown("#### 熱錢 vs 台股")
    fig2 = make_subplots(specs=[[{"secondary_y": True}]])
    fig2.add_trace(go.Scatter(x=hist_data.index, y=hist_data['^TWII'], name="台股", line=dict(color='#2962ff')), secondary_y=False)
    fig2.add_trace(go.Scatter(x=hist_data.index, y=hist_data['TWD=X'], name="匯率", line=dict(color='#00c853', dash='dot')), secondary_y=True)
    fig2.update_layout(height=350, margin=dict(l=0, r=0, t=30, b=0), hovermode="x unified", legend=dict(yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig2, use_container_width=True)
