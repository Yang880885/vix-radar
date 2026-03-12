import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import json
import numpy as np

st.set_page_config(page_title="獵人戰情室：終極波段導航儀 5.0", layout="wide")
st.title("🎯 台股波段轉折導航儀 (雷達 5.0 全自動 AI 指令版)")

# --- 側邊欄：純粹的通訊引擎 ---
st.sidebar.header("🤖 LINE 通訊引擎")
try:
    line_token = st.secrets["LINE_TOKEN"]
    line_user_id = st.secrets["LINE_USER_ID"]
    st.sidebar.success("🔒 雲端機密金庫已解鎖！全自動待命中。")
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
    except Exception as e:
        pass
    return False

if st.sidebar.button("發送測試警報 🚀"):
    if line_token and line_user_id:
        if send_line_message("✅ 【戰情室廣播】指揮官，雷達 5.0 指令版已上線，100% 自動化偵測中！", line_token, line_user_id):
            st.sidebar.success("✅ 測試警報已發射！")
        else:
            st.sidebar.error("❌ 發送失敗，請檢查座標設定。")

st.write("📡 啟動全球數據鏈，100% 全自動 AI 戰術運算中...")

# --- 抓取所有戰區資料 ---
tickers = ["^VIX", "^VIX3M", "^VVIX", "^SKEW", "^VIX9D", "^SOX", "^NDX", "TSM", "TWD=X", "^TNX", "BTC-USD"]
data = yf.download(tickers, period="10d")['Close'].ffill()
twii_data = yf.download("^TWII", period="2mo")

# --- 數據計算區 ---
latest = data.iloc[-1]
prev = data.iloc[-2]

ratio_vix_vix3m = latest['^VIX'] / latest['^VIX3M']
diff_vix9d_vix = latest['^VIX9D'] - latest['^VIX']
sox_pct = ((latest['^SOX'] / prev['^SOX']) - 1) * 100
ndx_pct = ((latest['^NDX'] / prev['^NDX']) - 1) * 100
tsm_pct = ((latest['TSM'] / prev['TSM']) - 1) * 100

twd_latest = latest['TWD=X']
twd_ma5 = data['TWD=X'].tail(5).mean()

tnx_latest = latest['^TNX']
btc_pct = ((latest['BTC-USD'] / prev['BTC-USD']) - 1) * 100

# 技術面計算
delta = twii_data['Close'].diff()
gain = (delta.where(delta > 0, 0)).fillna(0)
loss = (-delta.where(delta < 0, 0)).fillna(0)
avg_gain = gain.rolling(window=14, min_periods=1).mean()
avg_loss = loss.rolling(window=14, min_periods=1).mean()
rs = avg_gain / avg_loss
rsi_14 = 100 - (100 / (1 + rs))
latest_rsi = float(rsi_14.iloc[-1])

tw_open = float(twii_data['Open'].iloc[-1])
tw_close = float(twii_data['Close'].iloc[-1])
tw_high = float(twii_data['High'].iloc[-1])
tw_low = float(twii_data['Low'].iloc[-1])

body = abs(tw_open - tw_close)
lower_shadow = min(tw_open, tw_close) - tw_low
upper_shadow = tw_high - max(tw_open, tw_close)
is_long_lower_shadow = (lower_shadow > body * 2) and (lower_shadow > upper_shadow) and (body > 0)

# --- AI 戰術大腦：綜合計分系統 ---
score = 0
if ratio_vix_vix3m > 1.0: score += 3
if latest_rsi < 30: score += 2
if is_long_lower_shadow: score += 2
if twd_latest < twd_ma5: score += 1
if latest['^SKEW'] > 140: score -= 2
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
st.markdown("## 🧠 戰情室 AI 全自動綜合判定")
if score >= 4:
    st.success(f"### 🟢 強烈買進訊號 (多方戰力：{score} 分)\n**🎯 總部指令**：天時地利人和齊聚！血流成河中的絕佳買點，請立刻鎖定強勢 ETF 分批打出重倉！")
elif score >= 1:
    st.info(f"### 🟡 偏多震盪 (多方戰力：{score} 分)\n**🎯 總部指令**：環境偏向樂觀，可維持多單部位，或動用小資金試單，嚴格設定停損。")
elif score <= -3:
    st.error(f"### 🔴 極度危險 (空方戰力：{score} 分)\n**🎯 總部指令**：空襲警報！外資撤退加風險飆升，千萬不可接刀！滿手現金觀望或佈局反向避險。")
else:
    st.warning(f"### ⚪ 多空交戰 (戰力平盤：{score} 分)\n**🎯 總部指令**：多空訊號抵銷，市場正在尋找方向。耐心等待勝率更高的轉折浮現。")

st.divider()

# --- 📈 戰區 1：台股技術面自動偵測 ---
st.markdown("### 📈 戰區 1：台股技術面自動偵測 (大盤落底掃描)")
t1, t2 = st.columns(2)
with t1:
    st.info("相對強弱指標 (RSI 14)")
    st.metric(label="最新 RSI (<30 超賣)", value=f"{latest_rsi:.1f}")
    if latest_rsi < 30: 
        st.error("🚨 跌幅過深，嚴重超賣！")
        st.markdown("**🎯 您的動作**：\n極短線跌幅滿足，隨時準備搶 V 轉反彈！")
    elif latest_rsi > 70: 
        st.warning("⚠️ 漲幅過大，嚴重超買！")
        st.markdown("**🎯 您的動作**：\n高檔過熱，請勿追高，準備分批獲利了結。")
    else: 
        st.success("✅ 指標位階適中。")
        st.markdown("**🎯 您的動作**：\n大盤節奏穩定，依個別強勢股操作。")
with t2:
    st.info("主力護盤 K 線掃描 (最新單日)")
    if is_long_lower_shadow:
        st.metric(label="K 線型態", value="長下影線 (仙人指路)")
        st.error("🎯 偵測到強力護盤！勝率極高的抄底確認訊號！")
        st.markdown("**🎯 您的動作**：\n主力洗盤結束並接走籌碼！立刻打出 30% 資金抄底。")
    else:
        st.metric(label="K 線型態", value="一般型態")
        st.success("✅ 目前無極端洗盤特徵。")
        st.markdown("**🎯 您的動作**：\n尚無明確單日反轉訊號，繼續耐心等待。")

st.divider()

# --- 🌐 戰區 2：全球波動率監控 ---
st.markdown("### 🌐 戰區 2：全球波動率監控")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.info("核心恐慌")
    st.metric("VIX/VIX3M (>1極恐慌)", f"{ratio_vix_vix3m:.2f}")
    if ratio_vix_vix3m > 1: 
        st.error("🚨 逆價差爆發！")
        st.markdown("**🎯 您的動作**：\n瞄準長下影線準備 30% 抄底！")
    else: 
        st.success("✅ 正價差。")
        st.markdown("**🎯 您的動作**：\n天下太平，抱緊多單。")
with c2:
    st.info("大戶避險")
    st.metric("VVIX 指數 (>110警戒)", f"{latest['^VVIX']:.1f}")
    if latest['^VVIX'] > 110: 
        st.warning("⚠️ 聰明錢偷買保險！")
        st.markdown("**🎯 您的動作**：\n大戶預期震盪，拉高停利點。")
    else: 
        st.success("✅ 大戶情緒正常。")
        st.markdown("**🎯 您的動作**：\n維持紀律，按兵不動。")
with c3:
    st.info("黑天鵝")
    st.metric("SKEW 指數 (>140危險)", f"{latest['^SKEW']:.1f}")
    if latest['^SKEW'] > 140:
        st.error("💣 核彈預警飆升！")
        st.markdown("**🎯 您的動作**：\n巨鱷正豪賭崩盤！切勿滿倉，鎖死現金避險。")
    else:
        st.success("✅ 尾部風險低。")
        st.markdown("**🎯 您的動作**：\n發生黑天鵝機率低，維持正常配置。")
with c4:
    st.info("短線超殺")
    st.metric("9D-VIX 乖離 (>5超殺)", f"{diff_vix9d_vix:.2f}")
    if diff_vix9d_vix > 5:
        st.error("🔥 情緒過度宣洩！")
        st.markdown("**🎯 您的動作**：\n突發利空導致超殺，極短線高機率出現報復性V轉！")
    else:
        st.success("✅ 短線無極端異常。")
        st.markdown("**🎯 您的動作**：\n不建議隨意短線進出。")

st.divider()

# --- 💸 戰區 3：全球資金流向與風險 ---
st.markdown("### 💸 戰區 3：全球資金流向與風險 (全自動籌碼)")
f1, f2, f3 = st.columns(3)
with f1:
    st.info("外資動向：美元/台幣匯率")
    st.metric("最新匯率 (跌代表台幣升值)", f"{twd_latest:.2f}")
    if twd_latest > twd_ma5:
        st.warning("⚠️ 台幣貶值趨勢：外資提款中。")
        st.markdown("**🎯 您的動作**：\n外資撤退中，請提高警覺，暫緩大型權值股的買進計畫。")
    else:
        st.success("✅ 台幣升值趨勢：熱錢流入。")
        st.markdown("**🎯 您的動作**：\n資金湧入台股，有利多頭行情，可積極佈局權值股。")
with f2:
    st.info("總經環境：美 10 年期公債殖利率")
    st.metric("最新殖利率", f"{tnx_latest:.2f}%")
    if tnx_latest > 4.5:
        st.error("🚨 殖利率過高：壓抑科技股估值！")
        st.markdown("**🎯 您的動作**：\n資金成本過高，避開高本益比電子股，轉向金融或價值股。")
    else:
        st.success("✅ 資金寬鬆：有利科技股。")
        st.markdown("**🎯 您的動作**：\n資金環境寬鬆，有利台股電子與半導體族群上攻。")
with f3:
    st.info("散戶風險情緒：比特幣")
    st.metric("比特幣 (USD)", f"{latest['BTC-USD']:,.0f}", f"{btc_pct:.2f}%")
    if btc_pct < -5.0:
        st.error("💣 幣圈暴跌：散戶去槓桿！")
        st.markdown("**🎯 您的動作**：\n全球投機資金斷頭，恐慌隨時蔓延股市。嚴控資金水位，切勿隨意摸底。")
    else:
        st.success("✅ 投機情緒穩定。")
        st.markdown("**🎯 您的動作**：\n全球風險偏好正常，維持既有操作紀律。")

st.divider()

# --- 🦅 戰區 4：美股風向球 ---
st.markdown("### 🦅 戰區 4：美股科技領航風向球 (明日預測)")
st.caption("💡 狙擊判讀：若費半與 TSM ADR 雙雙重挫，明日台股開盤極高機率引發多殺多，請準備現金防禦或伺機撿便宜。")
u1, u2, u3 = st.columns(3)
with u1:
    st.info("半導體羅盤")
    st.metric("費城半導體", f"{latest['^SOX']:.2f}", f"{sox_pct:.2f}%")
with u2:
    st.info("科技股情緒")
    st.metric("那斯達克 100", f"{latest['^NDX']:.2f}", f"{ndx_pct:.2f}%")
with u3:
    st.info("大盤先鋒")
    st.metric("台積電 ADR", f"{latest['TSM']:.2f}", f"{tsm_pct:.2f}%")

st.divider()

# --- 🎯 戰區 5：精銳部隊起漲掃描 (火控鎖定) ---
st.markdown("### 🎯 戰區 5：精銳部隊起漲掃描 (主力量能偵測)")
st.caption("💡 戰術邏輯：自動掃描核心 ETF 與權值股。條件：股價站上月線 (20MA) 且 RSI > 55 (動能轉強)。")

# 指揮官的專屬觀察名單 (您可以隨時在這裡新增或刪除代碼，記得加上 .TW)
# 這裡涵蓋了大盤、科技、半導體ETF，以及台股三王
watch_list = [
    "0050.TW", "0052.TW", "0056.TW", "00878.TW", "00929.TW", 
    "00919.TW", "00881.TW", "00891.TW", "2330.TW", "2317.TW", "2454.TW"
]

@st.cache_data(ttl=3600) # 快取資料1小時，避免被 Yahoo 封鎖
def scan_breakout_stocks(tickers):
    breakout_list = []
    # 一次性下載觀察名單的歷史資料 (節省連線時間)
    hist_data = yf.download(tickers, period="2mo")['Close'].ffill()
    
    for ticker in tickers:
        try:
            # 取出單一標的的收盤價序列，並清除空值
            series = hist_data[ticker].dropna()
            if len(series) < 20:
                continue
                
            latest_price = float(series.iloc[-1])
            prev_price = float(series.iloc[-2])
            pct_change = ((latest_price / prev_price) - 1) * 100
            
            # 計算 20日均線 (月線)
            ma20 = float(series.rolling(window=20).mean().iloc[-1])
            
            # 計算 RSI
            delta = series.diff()
            gain = (delta.where(delta > 0, 0)).fillna(0)
            loss = (-delta.where(delta < 0, 0)).fillna(0)
            avg_gain = gain.rolling(window=14).mean().iloc[-1]
            avg_loss = loss.rolling(window=14).mean().iloc[-1]
            rs = avg_gain / avg_loss if avg_loss != 0 else 100
            rsi = 100 - (100 / (1 + rs))
            
            # 🎯 起漲判定邏輯：收盤價大於月線，且 RSI 大於 55 (動能強勢)
            if latest_price > ma20 and rsi > 55:
                breakout_list.append({
                    "標的": ticker.replace(".TW", ""),
                    "最新收盤價": round(latest_price, 2),
                    "今日漲跌幅": f"{round(pct_change, 2)}%",
                    "月線位置": round(ma20, 2),
                    "RSI 動能": round(rsi, 1)
                })
        except:
            continue
            
    return pd.DataFrame(breakout_list)

# 執行掃描
with st.spinner("🔍 正在鎖定起漲目標，請稍候..."):
    breakout_df = scan_breakout_stocks(watch_list)

if not breakout_df.empty:
    st.success(f"🔥 報告指揮官！在觀察名單中，今日有 {len(breakout_df)} 檔標的觸發起漲訊號！")
    # 將 DataFrame 顯示為漂亮的表格
    st.dataframe(breakout_df, use_container_width=True, hide_index=True)
    st.markdown("**🎯 您的動作**：\n請配合最上方的大盤 AI 總分。如果大盤為🟢綠燈，這些就是您可以優先動用資金狙擊的強勢目標！")
else:
    st.info("⏸️ 目前觀察名單中無標的符合強勢起漲條件。")
    st.markdown("**🎯 您的動作**：\n主力尚未發動攻擊，請耐心等待，切勿勉強開槍。")

st.divider()