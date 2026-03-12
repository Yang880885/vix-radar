import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import json
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="獵人戰情室：終極 VIX 量化雷達", layout="wide")
st.title("🎯 終極 VIX 二次運算量化雷達 (四大戰區完全體)")

# --- 側邊欄：LINE 通訊設定 (雲端加密版) ---
st.sidebar.header("🤖 官方機器人通訊")
try:
    # 嘗試從雲端金庫拿鑰匙
    line_token = st.secrets["LINE_TOKEN"]
    line_user_id = st.secrets["LINE_USER_ID"]
    st.sidebar.success("🔒 雲端機密金庫已解鎖，雷達武裝完畢！")
except:
    # 如果找不到金庫 (例如在本機端測試)，就允許手動輸入
    st.sidebar.warning("⚠️ 尚未偵測到金庫，請手動輸入座標")
    line_token = st.sidebar.text_input("Channel Access Token", type="password")
    line_user_id = st.sidebar.text_input("Your User ID", type="password")

def send_line_message(message, token, user_id):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    payload = {"to": user_id, "messages": [{"type": "text", "text": message}]}
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            st.sidebar.success("✅ 機器人通訊連線成功！")
        else:
            st.sidebar.error(f"❌ 傳送失敗，錯誤碼：{response.text}")
    except Exception as e:
        st.sidebar.error("❌ 系統連線發生異常")

# --- 抓取四大戰區與台股資料 ---
st.write("📡 正在掃描全球四大戰區數據...")
tickers = ["^VIX", "^VIX3M", "^VVIX", "^SKEW", "^VIX9D", "^TWII"]
data = yf.download(tickers, period="2y")['Close']
data.ffill(inplace=True) 

# 取得最新報價與計算
latest = data.iloc[-1]
vix = latest['^VIX']
vix3m = latest['^VIX3M']
vvix = latest['^VVIX']
skew = latest['^SKEW']
vix9d = latest['^VIX9D']

ratio_vix_vix3m = vix / vix3m
diff_vix9d_vix = vix9d - vix

# --- 發送警報邏輯 ---
if ratio_vix_vix3m > 1.0 and line_token and line_user_id:
    alert_msg = f"\n🚨【獵人紅色警報】\n極端恐慌出現！\n目前的 VIX 恐慌比值高達 {ratio_vix_vix3m:.2f}。\n準備尋找台股底部買點！"
    send_line_message(alert_msg, line_token, line_user_id)

if st.sidebar.button("發送測試警報 🚀"):
    if line_token and line_user_id:
        send_line_message("✅ 【戰情室廣播】指揮官，四大戰區監控系統運作正常！", line_token, line_user_id)

# --- 四大戰區儀表板呈現 ---
st.markdown("### 🌐 全球波動率戰區即時監控")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.info("戰區 1：核心恐慌比值")
    st.metric(label="VIX / VIX3M (>1極限恐慌)", value=f"{ratio_vix_vix3m:.2f}")
    if ratio_vix_vix3m > 1:
        st.error("🚨 逆價差爆發！準備抄底！")
    else:
        st.success("✅ 正價差，大盤情緒穩定。")

with col2:
    st.info("戰區 2：大戶避險情緒")
    st.metric(label="VVIX 指數 (>110警戒)", value=f"{vvix:.1f}")
    if vvix > 110 and vix < 20:
        st.warning("⚠️ 聰明錢正在偷買保險！")
        
with col3:
    st.info("戰區 3：黑天鵝雷達")
    st.metric(label="SKEW 指數 (>140危險)", value=f"{skew:.1f}")
    if skew > 140:
        st.error("💣 核彈級災難預警飆升！")

with col4:
    st.info("戰區 4：短期均值回歸")
    st.metric(label="極短線乖離 (9D-VIX >5超殺)", value=f"{diff_vix9d_vix:.2f}")
    if diff_vix9d_vix > 5:
        st.error("🔥 情緒過度宣洩，醞釀強彈！")

st.divider()

# --- 上帝視角對比圖 ---
st.subheader("📈 歷史回測：VIX 核心恐慌比值 VS 台股大盤")
historical_ratio = data['^VIX'] / data['^VIX3M']
fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_trace(go.Scatter(x=data.index, y=data['^TWII'], name="台股大盤", line=dict(color='blue')), secondary_y=False)
fig.add_trace(go.Scatter(x=data.index, y=historical_ratio, name="恐慌比值", line=dict(color='rgba(255,0,0,0.6)')), secondary_y=True)
fig.add_hline(y=1.0, line_dash="dash", line_color="red", secondary_y=True, annotation_text="狙擊扳機觸發線 (1.0)")
fig.update_layout(height=500, hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)
