import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import json
import numpy as np

st.set_page_config(page_title="獵人戰情室：終極波段導航儀 4.0", layout="wide")
st.title("🎯 台股波段轉折導航儀 (雷達 4.0 AI決策完全體)")

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
st.sidebar.markdown("[👉 點我查微台籌碼](https://www.wantgoo.com/futures/retail-indicator/wtm&)")
retail_ratio = st.sidebar.number_input("微台散戶多空比 (%)", value=0.0, step=1.0)
st.sidebar.markdown("[👉 點我查外資未平倉口數](https://www.taifex.com.tw/cht/3/futContractsDateExcel)")
foreign_oi = st.sidebar.number_input("外資期貨未平倉 (萬口，空單輸入負數)", value=-3.5, step=0.1)
st.sidebar.markdown("[👉 點我查景氣分數](https://index.ndc.gov.tw/n/zh_tw)")
ndc_light = st.sidebar.number_input("國發會景氣分數 (9~45)", value=30, step=1)

st.write("📡 啟動全球數據鏈，AI 戰術運算中...")

# --- 抓取所有戰區資料 ---
# 1. 波動率與美股
tickers = ["^VIX", "^VIX3M", "^VVIX", "^SKEW", "^VIX9D", "^SOX", "^NDX", "TSM"]
data = yf.download(tickers, period="5d")['Close'].ffill()

# 2. 台股大盤 (用於技術面偵測)
twii_data = yf.download("^TWII", period="2mo")

# --- 數據計算區 ---
latest = data.iloc[-1]
prev = data.iloc[-2]

ratio_vix_vix3m = latest['^VIX'] / latest['^VIX3M']
diff_vix9d_vix = latest['^VIX9D'] - latest['^VIX']
sox_pct = ((latest['^SOX'] / prev['^SOX']) - 1) * 100

# 技術面計算：RSI (14天)
delta = twii_data['Close'].diff()
gain = (delta.where(delta > 0, 0)).fillna(0)
loss = (-delta.where(delta < 0, 0)).fillna(0)
avg_gain = gain.rolling(window=14, min_periods=1).mean()
avg_loss = loss.rolling(window=14, min_periods=1).mean()
rs = avg_gain / avg_loss
rsi_14 = 100 - (100 / (1 + rs))
latest_rsi = float(rsi_14.iloc[-1])

# 技術面計算：K線型態 (偵測仙人指路/長下影線)
tw_open = float(twii_data['Open'].iloc[-1])
tw_close = float(twii_data['Close'].iloc[-1])
tw_high = float(twii_data['High'].iloc[-1])
tw_low = float(twii_data['Low'].iloc[-1])

body = abs(tw_open - tw_close)
lower_shadow = min(tw_open, tw_close) - tw_low
upper_shadow = tw_high - max(tw_open, tw_close)

# 判定長下影線條件：下影線大於實體2倍，且大於上影線
is_long_lower_shadow = (lower_shadow > body * 2) and (lower_shadow > upper_shadow) and (body > 0)

# --- AI 戰術大腦：綜合計分系統 ---
score = 0
if ratio_vix_vix3m > 1.0: score += 3
if retail_ratio > 20: score -= 2
elif retail_ratio < -20: score += 2
if foreign_oi < -5.0: score -= 2
elif foreign_oi > 0: score += 2
if latest_rsi < 30: score += 2
if is_long_lower_shadow: score += 2

# --- 🏆 頂部：綜合決策計分板 ---
st.markdown("## 🧠 戰情室 AI 綜合戰術判定")
if score >= 4:
    st.success(f"### 🟢 強烈買進訊號 (多方戰力：{score} 分)\n**🎯 總部指令**：天時地利人和齊聚！血流成河中的絕佳買點，請立刻鎖定強勢 ETF 分批打出重倉！")
elif score >= 1:
    st.info(f"### 🟡 偏多震盪 (多方戰力：{score} 分)\n**🎯 總部指令**：環境偏向樂觀，可維持多單部位，或動用小資金試單，嚴格設定停損。")
elif score <= -3:
    st.error(f"### 🔴 極度危險 (空方戰力：{score} 分)\n**🎯 總部指令**：空襲警報！外資大空加散戶大買，千萬不可接刀！滿手現金觀望或佈局反向避險。")
else:
    st.warning(f"### ⚪ 多空交戰 (戰力平盤：{score} 分)\n**🎯 總部指令**：訊號衝突，市場正在尋找方向。最好的動作就是「沒有動作」，耐心等待轉折浮現。")

st.divider()

# --- 📈 技術面自動偵測 ---
st.markdown("### 📈 技術面自動偵測 (大盤落底掃描)")
t1, t2 = st.columns(2)
with t1:
    st.info("大盤相對強弱指標 (RSI 14)")
    st.metric(label="最新 RSI (<30 超賣落底)", value=f"{latest_rsi:.1f}")
    if latest_rsi < 30:
        st.error("🚨 跌幅過深，技術面嚴重超賣，醞釀強彈！")
    elif latest_rsi > 70:
        st.warning("⚠️ 漲幅過大，技術面嚴重超買，留意拉回！")
    else:
        st.success("✅ 指標位階適中。")

with t2:
    st.info("主力護盤 K 線掃描 (最新單日)")
    if is_long_lower_shadow:
        st.metric(label="K 線型態", value="長下影線 (仙人指路)")
        st.error("🎯 偵測到強力護盤！主力在底部把籌碼全部接走，勝率極高的抄底確認訊號！")
    else:
        st.metric(label="K 線型態", value="一般型態")
        st.success("✅ 目前無極端洗盤特徵。")

st.divider()

# --- 第一戰區：全球恐慌 (大環境) ---
st.markdown("### 🌐 第一戰區：全球波動率監控")
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.info("戰區 1：核心恐慌")
    st.metric(label="VIX/VIX3M (>1極度恐慌)", value=f"{ratio_vix_vix3m:.2f}")
    if ratio_vix_vix3m > 1: 
        st.error("🚨 逆價差爆發！")
        st.markdown("**🎯 您的動作**：\n瞄準長下影線準備 30% 抄底！")
    else: 
        st.success("✅ 正價差。")
        st.markdown("**🎯 您的動作**：\n天下太平，抱緊多單。")

with c2:
    st.info("戰區 2：大戶避險情緒")
    st.metric(label="VVIX 指數 (>110警戒)", value=f"{latest['^VVIX']:.1f}")
    if latest['^VVIX'] > 110: 
        st.warning("⚠️ 聰明錢偷買保險！")
        st.markdown("**🎯 您的動作**：\n大戶預期震盪，拉高停利點。")
    else: 
        st.success("✅ 大戶情緒正常。")
        st.markdown("**🎯 您的動作**：\n維持紀律，按兵不動。")

with c3:
    st.info("戰區 3：黑天鵝雷達")
    st.metric(label="SKEW 指數 (>140危險)", value=f"{latest['^SKEW']:.1f}")
    if latest['^SKEW'] > 140:
        st.error("💣 核彈預警飆升！")
        st.markdown("**🎯 您的動作**：\n巨鱷正豪賭崩盤！切勿滿倉，鎖死現金避險。")
    else:
        st.success("✅ 尾部風險低。")
        st.markdown("**🎯 您的動作**：\n發生黑天鵝機率低，維持正常配置。")

with c4:
    st.info("戰區 4：短線均值回歸")
    st.metric(label="9D-VIX 乖離 (>5超殺)", value=f"{diff_vix9d_vix:.2f}")
    if diff_vix9d_vix > 5:
        st.error("🔥 情緒過度宣洩！")
        st.markdown("**🎯 您的動作**：\n突發利空導致超殺，極短線極可能出現報復性V轉！")
    else:
        st.success("✅ 短線無極端異常。")
        st.markdown("**🎯 您的動作**：\n不建議隨意短線進出。")

st.divider()

# --- 第二戰區：美股風向球 (明日預測) ---
st.markdown("### 🦅 第二戰區：美股科技領航風向球")
u1, u2, u3 = st.columns(3)
with u1:
    st.info("半導體羅盤")
    st.metric("費城半導體", f"{latest['^SOX']:.2f}", f"{sox_pct:.2f}%")
with u2:
    st.info("科技股情緒")
    ndx_pct = ((latest['^NDX'] / prev['^NDX']) - 1) * 100
    st.metric("那斯達克 100", f"{latest['^NDX']:.2f}", f"{ndx_pct:.2f}%")
with u3:
    st.info("大盤先鋒")
    tsm_pct = ((latest['TSM'] / prev['TSM']) - 1) * 100
    st.metric("台積電 ADR", f"{latest['TSM']:.2f}", f"{tsm_pct:.2f}%")

st.divider()

# --- 第三戰區：籌碼與總經 (在地確認) ---
st.markdown("### 🕵️‍♂️ 第三戰區：台股籌碼與總經判讀")
m1, m2, m3 = st.columns(3)

with m1:
    st.info("微台指散戶多空比 (終極反指標)")
    st.metric("目前數值", f"{retail_ratio}%")
    if retail_ratio > 20:
        st.error("🚨 散戶全面接刀！")
        st.markdown("**🎯 您的動作**：\n跌勢確立，主力正在倒貨。絕對不可買進，滿手多單者需減碼！")
    elif retail_ratio < -20:
        st.success("🔥 散戶全面被軋！")
        st.markdown("**🎯 您的動作**：\n軋空行情啟動，主力正在拉抬。沿著 5 日線上攻，做多為主！")
    else:
        st.info("⚖️ 散戶多空分歧")
        st.markdown("**🎯 您的動作**：\n無明顯反指標效應，觀察其他數據。")

with m2:
    st.info("外資未平倉 (莊家底牌)")
    st.metric("目前口數 (萬口)", f"{foreign_oi}")
    if foreign_oi < -3.5:
        st.error("💣 外資重倉放空！")
        st.markdown("**🎯 您的動作**：\n外資強烈看空，不管反彈多少都是逃命波。切勿接刀！")
    elif foreign_oi > 0:
        st.success("🚀 外資翻多！")
        st.markdown("**🎯 您的動作**：\n波段行情啟動，積極做多。")
    else:
        st.warning("⚠️ 外資偏空震盪")
        st.markdown("**🎯 您的動作**：\n轉折點尚未浮現，控制資金水位。")

with m3:
    st.info("景氣對策信號 (長線基本面)")
    st.metric("最新分數", f"{ndc_light}")
    if ndc_light >= 38:
        st.error("🔴 紅燈 (過熱)")
        st.markdown("**🎯 您的動作**：\n市場過度樂觀，準備分批獲利了結。")
    elif ndc_light <= 16:
        st.success("🔵 藍燈 (低迷)")
        st.markdown("**🎯 您的動作**：\n最佳波段佈局點！買在無人問津時。")
    else:
        st.info("🟢 綠/黃紅燈 (穩定)")
        st.markdown("**🎯 您的動作**：\n景氣溫和成長，維持既有部位。")
