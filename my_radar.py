import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import json
import streamlit.components.v1 as components

st.set_page_config(page_title="獵人戰情室：終極波段導航儀", layout="wide")
st.title("🎯 台股波段轉折導航儀 (雷達 3.0 狙擊完全體)")

# --- 側邊欄：情報中心 ---
st.sidebar.header("🤖 LINE 通訊與情報輸入")
try:
    line_token = st.secrets["LINE_TOKEN"]
    line_user_id = st.secrets["LINE_USER_ID"]
except:
    line_token = st.sidebar.text_input("LINE Token", type="password")
    line_user_id = st.sidebar.text_input("User ID", type="password")

st.sidebar.divider()
st.sidebar.subheader("📥 每日手動情報輸入")
st.sidebar.markdown("[👉 點我查籌碼](https://www.wantgoo.com/futures/retail-indicator/wmt&)")
retail_ratio = st.sidebar.number_input("小台散戶多空比 (%)", value=0.0, step=1.0)
foreign_oi = st.sidebar.number_input("外資期貨未平倉 (萬口，空單請輸入負數)", value=-3.5, step=0.1)
ndc_light = st.sidebar.number_input("國發會景氣分數 (9~45)", value=30, step=1)

# --- 第一戰區：VIX 量化自動掃描 ---
st.markdown("### 🌐 自動戰區：全球波動率監控")
tickers = ["^VIX", "^VIX3M", "^VVIX", "^SKEW", "^VIX9D"]
data = yf.download(tickers, period="5d")['Close'].ffill()
latest = data.iloc[-1]
ratio_vix_vix3m = latest['^VIX'] / latest['^VIX3M']
diff_vix9d_vix = latest['^VIX9D'] - latest['^VIX']

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.info("戰區 1：核心恐慌比值")
    st.metric(label="VIX/VIX3M (>1極度恐慌)", value=f"{ratio_vix_vix3m:.2f}")
    if ratio_vix_vix3m > 1: 
        st.error("🚨 逆價差爆發！")
        st.markdown("**🎯 您的動作**：\n瞄準長下影線準備 30% 抄底！")
    else: 
        st.success("✅ 正價差。")
        st.markdown("**🎯 您的動作**：\n天下太平，抱緊多單。")

with col2:
    st.info("戰區 2：大戶避險情緒")
    st.metric(label="VVIX 指數 (>110警戒)", value=f"{latest['^VVIX']:.1f}")
    if latest['^VVIX'] > 110: 
        st.warning("⚠️ 聰明錢偷買保險！")
        st.markdown("**🎯 您的動作**：\n大戶預期震盪，拉高停利點。")
    else: 
        st.success("✅ 大戶情緒正常。")
        st.markdown("**🎯 您的動作**：\n維持紀律，按兵不動。")

with col3:
    st.info("戰區 3：黑天鵝雷達")
    st.metric(label="SKEW 指數 (>140危險)", value=f"{latest['^SKEW']:.1f}")
    if latest['^SKEW'] > 140:
        st.error("💣 核彈預警飆升！")
        st.markdown("**🎯 您的動作**：\n巨鱷正豪賭崩盤！切勿滿倉，鎖死現金避險。")
    else:
        st.success("✅ 尾部風險低。")
        st.markdown("**🎯 您的動作**：\n發生黑天鵝機率低，維持正常配置。")

with col4:
    st.info("戰區 4：短線均值回歸")
    st.metric(label="9D-VIX 乖離 (>5超殺)", value=f"{diff_vix9d_vix:.2f}")
    if diff_vix9d_vix > 5:
        st.error("🔥 情緒過度宣洩！")
        st.markdown("**🎯 您的動作**：\n突發利空導致超殺，極短線高機率出現報復性V轉！")
    else:
        st.success("✅ 短線無極端異常。")
        st.markdown("**🎯 您的動作**：\n不建議隨意短線進出。")

st.divider()

# --- 第二戰區：籌碼與總經 (動態指令) ---
st.markdown("### 🕵️‍♂️ 手動情報戰區：籌碼與總經判讀")
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("#### 🧑‍🤝‍🧑 微台指散戶多空比 (終極反指標)")
    st.metric("目前數值", f"{retail_ratio}%")
    if retail_ratio > 20:
        st.error("🚨 散戶全面接刀！\n\n**🎯 您的動作**：跌勢確立，主力正在倒貨。絕對不可買進，滿手多單者需減碼！")
    elif retail_ratio < -20:
        st.success("🔥 散戶全面被軋！\n\n**🎯 您的動作**：軋空行情啟動，主力正在拉抬。沿著 5 日線上攻，做多為主！")
    else:
        st.info("⚖️ 散戶多空分歧\n\n**🎯 您的動作**：無明顯反指標效應，觀察其他數據。")

with c2:
    st.markdown("#### 🏦 外資未平倉 (莊家底牌)")
    st.metric("目前口數", f"{foreign_oi} 萬口")
    if foreign_oi < -3.5:
        st.error("💣 空襲警報：外資重倉放空！\n\n**🎯 您的動作**：外資強烈看空，不管反彈多少都是逃命波。切勿接刀！")
    elif foreign_oi > 0:
        st.success("🚀 外資翻多！\n\n**🎯 您的動作**：波段行情啟動，積極做多。")
    else:
        st.warning("⚠️ 外資偏空震盪\n\n**🎯 您的動作**：轉折點尚未浮現，控制資金水位。")

with c3:
    st.markdown("#### 🚦 景氣對策信號")
    st.metric("最新分數", f"{ndc_light} 分")
    if ndc_light >= 38:
        st.error("🔴 紅燈 (過熱)\n\n**🎯 您的動作**：市場過度樂觀，準備分批獲利了結。")
    elif ndc_light <= 16:
        st.success("🔵 藍燈 (低迷)\n\n**🎯 您的動作**：最佳波段佈局點！買在無人問津時。")
    else:
        st.info("🟢 綠/黃紅燈 (穩定)\n\n**🎯 您的動作**：景氣溫和成長，維持既有部位。")

st.divider()

# --- 第三戰區：美股板塊熱力圖 (TradingView 完美嵌入) ---
st.markdown("### 🗺️ 美股板塊戰略地圖 (預判台股明日資金流向)")
st.caption("💡 狙擊判讀：觀察 Technology (科技) 與 Semiconductors (半導體)。若鮮綠色，台股電子必漲；若深紅色，小心補跌。")
heatmap_html = """
<div class="tradingview-widget-container" style="height: 500px; width: 100%;">
  <div class="tradingview-widget-container__widget" style="height: calc(100% - 32px); width: 100%;"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-stock-heatmap.js" async>
  {
  "dataSource": "SPX500",
  "blockSize": "market_cap_basic",
  "blockColor": "change",
  "grouping": "sector",
  "locale": "zh_TW",
  "symbolUrl": "",
  "colorTheme": "dark",
  "hasTopBar": true,
  "isDataSetEnabled": true,
  "isZoomEnabled": true,
  "hasSymbolTooltip": true,
  "isMonoSize": false,
  "width": "100%",
  "height": "100%"
}
  </script>
</div>
"""
components.html(heatmap_html, height=500)