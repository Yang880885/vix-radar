import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="獵人戰情室：波段導航儀 5.8.1", layout="wide")
st.title("🎯 台股波段轉折導航儀")
st.caption("雷達 5.8.1 最終修復版 | 徹底解決 Yahoo API 櫃買報價延遲與 0% 幽靈數據")

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
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            return True
    except:
        pass
    return False

if st.sidebar.button("發送測試警報 🚀"):
    if line_token and line_user_id:
        if send_line_message("✅ 【戰情室廣播】指揮官，雷達 5.8.1 系統測試正常！通訊管道 100% 暢通！", line_token, line_user_id):
            st.sidebar.success("✅ 測試警報已發射！請檢查 LINE。")
        else:
            st.sidebar.error("❌ 發送失敗，請檢查金鑰設定。")
    else:
        st.sidebar.warning("⚠️ 尚未設定金鑰。")

# --- 抓取所有戰區資料 (徹底剔除週末與延遲幽靈數據) ---
trad_tickers = ["^VIX", "^VIX3M", "^VVIX", "^SKEW", "^VIX9D", "^SOX", "^NDX", "TSM", "TWD=X", "^TNX"]
trad_data_raw = yf.download(trad_tickers, period="10d")['Close'].dropna(how='all')
trad_data = trad_data_raw[trad_data_raw.index.dayofweek < 5]

btc_data = yf.download("BTC-USD", period="10d")['Close'].dropna()

tw_tickers = ["^TWII", "^TWOII"]
# 💡 修正點 1：拿掉台股資料的 .ffill()，保留 NaN 讓後面獨立計算
tw_data_raw = yf.download(tw_tickers, period="2mo")['Close'].dropna(how='all')
tw_data = tw_data_raw[tw_data_raw.index.dayofweek < 5]

twii_data = yf.download("^TWII", period="2mo").dropna(how='all')
twii_data = twii_data[twii_data.index.dayofweek < 5]

# --- 數據計算區 ---
# 建立字典，獨立抓取美股每個標的的「最後一天」與「前一天」有效數據
t_latest = {}
t_prev = {}
for col in trad_data.columns:
    valid_series = trad_data[col].dropna()
    if len(valid_series) >= 2:
        t_latest[col] = float(valid_series.iloc[-1])
        t_prev[col] = float(valid_series.iloc[-2])
    else:
        t_latest[col], t_prev[col] = 0.0001, 0.0001

btc_latest = float(btc_data.iloc[-1])
btc_prev = float(btc_data.iloc[-2])

# 💡 修正點 2：建立字典，獨立抓取台股（加權、櫃買）的有效數據，徹底解決報價時間差
tw_latest = {}
tw_prev = {}
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

# 💡 修正點 3：使用新的 tw_latest 字典來計算台股與櫃買漲跌幅
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

tw_open, tw_close = float(twii_data['Open'].iloc[-1]), float(twii_data['Close'].iloc[-1])
tw_high, tw_low = float(twii_data['High'].iloc[-1]), float(twii_data['Low'].iloc[-1])
body = abs(tw_open - tw_close)
lower_shadow = min(tw_open, tw_close) - tw_low
is_long_lower_shadow = (lower_shadow > body * 2) and (lower_shadow > (tw_high - max(tw_open, tw_close))) and (body > 0)

score = 0
if ratio_vix_vix3m > 1.0: score += 3
if latest_rsi < 30: score += 2
if is_long_lower_shadow: score += 2
if twd_latest < twd_ma5: score += 1
if t_latest['^SKEW'] > 140: score -= 2
if latest_rsi > 70: score -= 2
if twd_latest > twd_ma5: score -= 1
if tnx_latest > 4.5: score -= 1

# --- 自動警報觸發邏輯 ---
if score >= 4 and line_token and line_user_id:
    alert_msg = f"\n🚨【獵人紅色警報】\n🟢 強烈買進訊號！\n自動戰力評估高達 {score} 分！絕佳抄底買點已浮現，請立刻開啟雷達確認指令！"
    send_line_message(alert_msg, line_token, line_user_id)
elif score <= -3 and line_token and line_user_id:
    alert_msg = f"\n🚨【獵人紅色警報】\n🔴 極度危險訊號！\n空方戰力高達 {abs(score)} 分！系統偵測到多重暴跌風險，請立刻確認避險部位！"
    send_line_message(alert_msg, line_token, line_user_id)

# --- 🏆 頂部：綜合決策計分板 ---
st.markdown("## 🧠 AI 戰術總分")
if score >= 4:
    st.success(f"### 🟢 強烈買進 ({score} 分)\n**🎯 總部指令**：天時地利齊聚！血流成河中的絕佳買點，請鎖定強勢 ETF 分批重倉！")
elif score >= 1:
    st.info(f"### 🟡 偏多震盪 ({score} 分)\n**🎯 總部指令**：環境偏樂觀，可小資金試單，嚴防假突破。")
elif score <= -3:
    st.error(f"### 🔴 極度危險 ({score} 分)\n**🎯 總部指令**：空襲警報！外資撤退加風險飆升，千萬不可接刀。")
else:
    st.warning(f"### ⚪ 多空交戰 ({score} 分)\n**🎯 總部指令**：多空訊號抵銷，市場尋找方向，耐心等待。")

st.divider()

# --- 📈 戰區 1：台股結構 ---
st.markdown("### 📈 戰區 1：台股結構")
t1, t2, t3 = st.columns(3)
with t1:
    st.metric(label="大盤 RSI", value=f"{latest_rsi:.1f}", delta=f"{rsi_delta:.1f}")
    if latest_rsi < 30: st.error("🚨 **嚴重超賣**\n\n🎯 **動作**: 準備搶V轉反彈")
    elif latest_rsi > 70: st.warning("⚠️ **高檔過熱**\n\n🎯 **動作**: 勿追高，準備停利")
    else: st.success("✅ **位階適中**\n\n🎯 **動作**: 依個別強勢股操作")
with t2:
    if is_long_lower_shadow:
        st.metric(label="主力護盤", value="長下影線", delta="強力支撐", delta_color="off")
        st.error("🎯 **洗盤結束**\n\n🎯 **動作**: 打出 30% 資金抄底")
    else:
        st.metric(label="主力護盤", value="無", delta="一般", delta_color="off")
        st.success("✅ **無極端洗盤**\n\n🎯 **動作**: 無反轉訊號，耐心等待")
with t3:
    # 💡 修正點 4：UI 顯示也同步改為使用新的字典變數 tw_latest['^TWOII']
    st.metric(label="櫃買指數", value=f"{tw_latest['^TWOII']:.2f}", delta=f"{twoii_pct:.2f}%")
    if spread > 1.0 and twii_pct > 0: st.error("🚨 **嚴重拉積盤**\n\n🎯 **動作**: 避開中小型與一般ETF")
    elif twoii_pct > twii_pct and twoii_pct > 0: st.success("🔥 **內資噴發**\n\n🎯 **動作**: 積極佈局中小型ETF")
    else: st.info("⚖️ **結構同步**\n\n🎯 **動作**: 依大盤趨勢操作")

st.divider()

# --- 🌐 戰區 2：恐慌波動 ---
st.markdown("### 🌐 戰區 2：恐慌波動 (⚠️紅向上=危險)")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("VIX 比值", f"{ratio_vix_vix3m:.2f}", delta=f"{ratio_delta:.2f}", delta_color="inverse")
    if ratio_vix_vix3m > 1: st.error("🚨 **逆價差爆發**\n\n🎯 準備抄底")
    else: st.success("✅ **正價差**\n\n🎯 抱緊多單")
with c2:
    st.metric("VVIX 避險", f"{t_latest['^VVIX']:.1f}", delta=f"{vvix_delta:.1f}", delta_color="inverse")
    if t_latest['^VVIX'] > 110: st.warning("⚠️ **大戶避險**\n\n🎯 拉高停利點")
    else: st.success("✅ **情緒正常**\n\n🎯 按兵不動")
with c3:
    st.metric("SKEW 尾部", f"{t_latest['^SKEW']:.1f}", delta=f"{skew_delta:.1f}", delta_color="inverse")
    if t_latest['^SKEW'] > 140: st.error("💣 **黑天鵝預警**\n\n🎯 鎖死現金避險")
    else: st.success("✅ **風險低**\n\n🎯 維持正常配置")
with c4:
    st.metric("VIX 乖離", f"{diff_vix9d_vix:.2f}", delta=f"{diff_delta:.2f}", delta_color="inverse")
    if diff_vix9d_vix > 5: st.error("🔥 **情緒超殺**\n\n🎯 隨時報復性V轉")
    else: st.success("✅ **無異常**\n\n🎯 不隨意短線進出")

st.divider()

# --- 💸 戰區 3：資金風險 ---
st.markdown("### 💸 戰區 3：資金風險 (⚠️紅向上=撤退)")
f1, f2, f3 = st.columns(3)
with f1:
    st.metric("台幣匯率", f"{twd_latest:.2f}", delta=f"{twd_delta:.2f}", delta_color="inverse")
    if twd_latest > twd_ma5: st.warning("⚠️ **台幣貶值**\n\n🎯 暫緩權值股買進")
    else: st.success("✅ **熱錢流入**\n\n🎯 有利多頭佈局")
with f2:
    st.metric("美債殖利率", f"{tnx_latest:.2f}%", delta=f"{tnx_delta:.2f}%", delta_color="inverse")
    if tnx_latest > 4.5: st.error("🚨 **成本過高**\n\n🎯 避開高本益比電子股")
    else: st.success("✅ **資金寬鬆**\n\n🎯 有利科技半導體")
with f3:
    st.metric("比特幣(USD)", f"{btc_latest:,.0f}", f"{btc_pct:.2f}%")
    if btc_pct < -5.0: st.error("💣 **幣圈暴跌**\n\n🎯 嚴控股市資金水位")
    else: st.success("✅ **投機穩定**\n\n🎯 維持操作紀律")

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
