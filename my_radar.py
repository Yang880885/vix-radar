import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import json
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="獵人戰情室：終極 VIX 量化雷達", layout="wide")
st.title("🎯 終極 VIX 二次運算量化雷達 (實戰指令版)")

# --- 側邊欄：LINE 通訊設定 (雲端加密版) ---
st.sidebar.header("🤖 官方機器人通訊")
try:
    line_token = st.secrets["LINE_TOKEN"]
    line_user_id = st.secrets["LINE_USER_ID"]
    st.sidebar.success("🔒 雲端機密金庫已解鎖！")
except:
    st.sidebar.warning("⚠️ 尚未偵測到金庫，請手動輸入")
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
    except Exception as e:
        st.sidebar.error("❌ 系統連線發生異常")

# --- 抓取四大戰區與台股資料 ---
st.write("📡 正在掃描全球戰區數據並分析戰術...")
tickers = ["^VIX", "^VIX3M", "^VVIX", "^SKEW", "^VIX9D", "^TWII"]
data = yf.download(tickers, period="2y")['Close']
data.ffill(inplace=True) 

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
    alert_msg = f"\n🚨【獵人紅色警報】\n極端恐慌出現！\n目前的 VIX 恐慌比值高達 {ratio_vix_vix3m:.2f}。\n請立刻開啟雷達確認抄底指令！"
    send_line_message(alert_msg, line_token, line_user_id)

if st.sidebar.button("發送測試警報 🚀"):
    if line_token and line_user_id:
        send_line_message("✅ 【戰情室廣播】指揮官，實戰指令系統運作正常！", line_token, line_user_id)

# --- 四大戰區儀表板呈現 (加入動態行動指令) ---
st.markdown("### 🌐 全球波動率戰區即時監控與行動指南")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.info("戰區 1：核心恐慌比值")
    st.metric(label="VIX / VIX3M (>1極限恐慌)", value=f"{ratio_vix_vix3m:.2f}")
    if ratio_vix_vix3m > 1:
        st.error("🚨 逆價差爆發！極度恐慌！")
        st.markdown("**🎯 您的動作：**\n毫不猶豫瞄準大盤與強勢 ETF（如 009816、00981A 等），打出第一筆 **30% 抄底資金**！")
    else:
        st.success("✅ 正價差，大盤情緒穩定。")
        st.markdown("**🎯 您的動作：**\n天下太平。抱緊手上的多單，不需要做多餘的動作。")

with col2:
    st.info("戰區 2：大戶避險情緒")
    st.metric(label="VVIX 指數 (>110警戒)", value=f"{vvix:.1f}")
    if vvix > 110 and vix < 20:
        st.warning("⚠️ 聰明錢正偷偷買保險！")
        st.markdown("**🎯 您的動作：**\n大戶預期將有震盪。請拉高警覺，將**停利點設緊**，隨時準備獲利了結。")
    else:
        st.success("✅ 大戶避險情緒正常。")
        st.markdown("**🎯 您的動作：**\n目前無異常聰明錢動作，維持紀律，按兵不動。")
        
with col3:
    st.info("戰區 3：黑天鵝雷達")
    st.metric(label="SKEW 指數 (>140危險)", value=f"{skew:.1f}")
    if skew > 140:
        st.error("💣 核彈級災難預警飆升！")
        st.markdown("**🎯 您的動作：**\n巨鱷正在豪賭崩盤！**絕對不可滿倉或融資**，鎖死現金，可佈局防禦型金融股避險。")
    else:
        st.success("✅ 尾部風險處於低檔。")
        st.markdown("**🎯 您的動作：**\n發生黑天鵝暴跌的機率低，維持正常的股債資金配置。")

with col4:
    st.info("戰區 4：短期均值回歸")
    st.metric(label="極短線乖離 (9D-VIX >5)", value=f"{diff_vix9d_vix:.2f}")
    if diff_vix9d_vix > 5:
        st.error("🔥 情緒過度宣洩，醞釀強彈！")
        st.markdown("**🎯 您的動作：**\n突發利空導致超殺！極短線（1~3天）高機率出現**報復性V轉**，可動用小資金搶反彈。")
    else:
        st.success("✅ 短線情緒無極端異常。")
        st.markdown("**🎯 您的動作：**\n短線無不理性的超賣超買現象，不建議隨意短線進出。")

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