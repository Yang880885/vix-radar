import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="獵人戰情室：波段導航儀 5.8.1", layout="wide")
st.title("🎯 台股波段轉折導航儀")
st.caption("雷達 5.8.1 裝甲強化版 | 盤中斷線修復 + 獨立洗價引擎")

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

if st.sidebar.button("發送測試警報 🚀"):
    if line_token and line_user_id:
        send_line_message("✅ 【戰情室廣播】指揮官，雷達 5.8.1 裝甲強化版測試正常！", line_token, line_user_id)
        st.sidebar.success("✅ 測試警報已發射！")

# ==========================================
# 🔥 裝甲強化：獨立抓取，防禦 Yahoo 斷線
# ==========================================

# 1. 傳統資產 (美股/總經)
trad_tickers = ["^VIX", "^VIX3M", "^VVIX", "^SKEW", "^VIX9D", "^SOX", "^NDX", "TSM", "TWD=X", "^TNX"]
trad_data = yf.download(trad_tickers, period="10d")['Close'].dropna(how='all')
trad_data = trad_data[trad_data.index.dayofweek < 5].ffill()

btc_data = yf.Ticker("BTC-USD").history(period="10d")['Close'].dropna()

# 2. 台股與櫃買 (⚠️ 改用 Ticker history 獨立抓取，避免互相干擾導致 KeyError)
twii_df = yf.Ticker("^TWII").history(period="2mo").dropna(how='all')
twii_df = twii_df[twii_df.index.dayofweek < 5].ffill()

twoii_df = yf.Ticker("^TWOII").history(period="2mo").dropna(how='all')
twoii_df = twoii_df[twoii_df.index.dayofweek < 5].ffill()

# ==========================================
# 🛡️ 安全數據計算區
# ==========================================
trad_latest = trad_data.iloc[-1]
trad_prev = trad_data.iloc[-2]

btc_latest = float(btc_data.iloc[-1])
btc_prev = float(btc_data.iloc[-2])
btc_pct = ((btc_latest / btc_prev) - 1) * 100

# 防呆機制：確保某個美股代號消失時，不會引發當機
def get_safe_val(ticker):
    try: return trad_latest[ticker], trad_prev[ticker]
    except: return 0.0, 0.0

vix_l, vix_p = get_safe_val('^VIX')
vix3m_l, vix3m_p = get_safe_val('^VIX3M')
ratio_vix_vix3m = vix_l / vix3m_l if vix3m_l != 0 else 0
ratio_delta = ratio_vix_vix3m - (vix_p / vix3m_p if vix3m_p != 0 else 0)

vix9d_l, vix9d_p = get_safe_val('^VIX9D')
diff_vix9d_vix = vix9d_l - vix_l
diff_delta = diff_vix9d_vix - (vix9d_p - vix_p)

vvix_l, vvix_p = get_safe_val('^VVIX')
vvix_delta = vvix_l - vvix_p

skew_l, skew_p = get_safe_val('^SKEW')
skew_delta = skew_l - skew_p

sox_l, sox_p = get_safe_val('^SOX')
sox_pct = ((sox_l / sox_p) - 1) * 100 if sox_p != 0 else 0

ndx_l, ndx_p = get_safe_val('^NDX')
ndx_pct = ((ndx_l / ndx_p) - 1) * 100 if ndx_p != 0 else 0

tsm_l, tsm_p = get_safe_val('TSM')
tsm_pct = ((tsm_l / tsm_p) - 1) * 100 if tsm_p != 0 else 0

twd_l, twd_p = get_safe_val('TWD=X')
twd_delta = twd_l - twd_p
try: twd_ma5 = trad_data['TWD=X'].tail(5).mean()
except: twd_ma5 = twd_l

tnx_l, tnx_p = get_safe_val('^TNX')
tnx_delta = tnx_l - tnx_p

# ⚠️ 台股與櫃買計算 (加上長度防護，避免 Yahoo 沒給資料)
if len(twii_df) >= 2:
    twii_pct = ((twii_df['Close'].iloc[-1] / twii_df['Close'].iloc[-2]) - 1) * 100
    tw_open, tw_close = float(twii_df['Open'].iloc[-1]), float(twii_df['Close'].iloc[-1])
    tw_high, tw_low = float(twii_df['High'].iloc[-1]), float(twii_df['Low'].iloc[-1])
    
    delta = twii_df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    rs = gain.rolling(window=14, min_periods=1).mean() / loss.rolling(window=14, min_periods=1).mean()
    rsi_14 = 100 - (100 / (1 + rs))
    latest_rsi = float(rsi_14.iloc[-1])
    rsi_delta = latest_rsi - float(rsi_14.iloc[-2])
else:
    twii_pct, latest_rsi, rsi_delta = 0.0, 50.0, 0.0
    tw_open, tw_close, tw_high, tw_low = 0, 0, 0, 0

if len(twoii_df) >= 2:
    twoii_pct = ((twoii_df['Close'].iloc[-1] / twoii_df['Close'].iloc[-2]) - 1) * 100
else:
    twoii_pct = 0.0
    
spread = twii_pct - twoii_pct 

body = abs(tw_open - tw_close)
lower_shadow = min(tw_open, tw_close) - tw_low
is_long_lower_shadow = (lower_shadow > body * 2) and (lower_shadow > (tw_high - max(tw_open, tw_close))) and (body > 0)

score = 0
if ratio_vix_vix3m > 1.0: score += 3
if latest_rsi < 30: score += 2
if is_long_lower_shadow: score += 2
if twd_l < twd_ma5: score += 1
if skew_l > 140: score -= 2
if latest_rsi > 70: score -= 2
if twd_l > twd_ma5: score -= 1
if tnx_l > 4.5: score -= 1

# ==========================================
# 🏆 頂部：綜合決策計分板
# ==========================================
st.markdown("## 🧠 AI 戰術總分")
if score >= 4: st.success(f"### 🟢 強烈買進 ({score} 分)\n**🎯 總部指令**：天時地利齊聚！請鎖定強勢 ETF 分批重倉！")
elif score >= 1: st.info(f"### 🟡 偏多震盪 ({score} 分)\n**🎯 總部指令**：環境偏樂觀，可小資金試單，嚴防假突破。")
elif score <= -3: st.error(f"### 🔴 極度危險 ({score} 分)\n**🎯 總部指令**：空襲警報！外資撤退加風險飆升，千萬不可接刀。")
else: st.warning(f"### ⚪ 多空交戰 ({score} 分)\n**🎯 總部指令**：多空訊號抵銷，市場尋找方向，耐心等待。")

st.divider()

# 📈 戰區 1：台股結構
st.markdown("### 📈 戰區 1：台股結構")
t1, t2, t3 = st.columns(3)
with t1:
    st.metric(label="大盤 RSI", value=f"{latest_rsi:.1f}", delta=f"{rsi_delta:.1f}")
with t2:
    st.metric(label="主力護盤", value="長下影線" if is_long_lower_shadow else "無", delta="強力支撐" if is_long_lower_shadow else "一般", delta_color="off")
with t3:
    # 確保櫃買有資料，如果 Yahoo 斷線就顯示 0
    twoii_val = twoii_df['Close'].iloc[-1] if len(twoii_df) > 0 else 0.0
    st.metric(label="櫃買指數", value=f"{twoii_val:.2f}", delta=f"{twoii_pct:.2f}%")

st.divider()

# 🌐 戰區 2：恐慌波動
st.markdown("### 🌐 戰區 2：恐慌波動 (⚠️紅向上=危險)")
c1, c2, c3, c4 = st.columns(4)
with c1: st.metric("VIX 比值", f"{ratio_vix_vix3m:.2f}", delta=f"{ratio_delta:.2f}", delta_color="inverse")
with c2: st.metric("VVIX 避險", f"{vvix_l:.1f}", delta=f"{vvix_delta:.1f}", delta_color="inverse")
with c3: st.metric("SKEW 尾部", f"{skew_l:.1f}", delta=f"{skew_delta:.1f}", delta_color="inverse")
with c4: st.metric("VIX 乖離", f"{diff_vix9d_vix:.2f}", delta=f"{diff_delta:.2f}", delta_color="inverse")

st.divider()

# 💸 戰區 3：資金風險
st.markdown("### 💸 戰區 3：資金風險 (⚠️紅向上=撤退)")
f1, f2, f3 = st.columns(3)
with f1: st.metric("台幣匯率", f"{twd_l:.2f}", delta=f"{twd_delta:.2f}", delta_color="inverse")
with f2: st.metric("美債殖利率", f"{tnx_l:.2f}%", delta=f"{tnx_delta:.2f}%", delta_color="inverse")
with f3: st.metric("比特幣(USD)", f"{btc_latest:,.0f}", f"{btc_pct:.2f}%")

st.divider()

# 🦅 戰區 4：美股風向
st.markdown("### 🦅 戰區 4：美股風向")
u1, u2, u3 = st.columns(3)
with u1: st.metric("費半指數", f"{sox_l:.2f}", f"{sox_pct:.2f}%")
with u2: st.metric("那斯達克", f"{ndx_l:.2f}", f"{ndx_pct:.2f}%")
with u3: st.metric("台積電 ADR", f"{tsm_l:.2f}", f"{tsm_pct:.2f}%")

st.divider()

# 🔭 戰區 5：歷史回測
st.markdown("### 🔭 戰區 5：鑑古知今")
try:
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
except:
    st.warning("⚠️ 歷史回測圖表暫時無法載入，Yahoo 伺服器連線異常。")
