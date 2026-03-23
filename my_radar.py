import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="獵人戰情室：波段導航儀 7.0", layout="wide")
st.title("🎯 台股波段轉折導航儀")
st.caption("雷達 7.0 終極籌碼進化版 | 雙核心戰區 + 盤後三大法人主力動向全自動追蹤")

# --- 防連發引擎 ---
@st.cache_resource
def get_alert_memory():
    return {"last_state": "NONE"}
alert_memory = get_alert_memory()

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
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=5)
        if response.status_code == 200: return True
    except: pass
    return False

if st.sidebar.button("發送測試警報 🚀"):
    if line_token and line_user_id:
        if send_line_message("✅ 【戰情室廣播】指揮官，雷達 7.0 雙核心引擎測試正常！", line_token, line_user_id):
            st.sidebar.success("✅ 測試警報已發射！")
        else: st.sidebar.error("❌ 發送失敗，請檢查金鑰。")
    else: st.sidebar.warning("⚠️ 尚未設定金鑰。")

# ==========================================
# 核心資料抓取 1：全球金融與宏觀數據
# ==========================================
@st.cache_data(ttl=300, show_spinner=False)
def fetch_master_data():
    tickers = ["^VIX", "^VIX3M", "^VVIX", "^SKEW", "^VIX9D", "^SOX", "^NDX", "TSM", "TWD=X", "^TNX", "^TWII", "^TWOII", "BTC-USD"]
    results = {}
    for t in tickers:
        try:
            hist = yf.Ticker(t).history(period="2mo")
            if not hist.empty and 'Close' in hist.columns: results[t] = hist['Close']
        except Exception: continue
    if results:
        df = pd.DataFrame(results)
        return df[df.index.dayofweek < 5].ffill()
    return pd.DataFrame()

@st.cache_data(ttl=300, show_spinner=False)
def fetch_twii_kline():
    try:
        hist = yf.Ticker("^TWII").history(period="2mo")
        if not hist.empty: return hist[hist.index.dayofweek < 5].ffill()
    except: pass
    return pd.DataFrame()

# ==========================================
# 核心資料抓取 2：台灣證交所盤後籌碼 (每日 15:30 後更新)
# ==========================================
@st.cache_data(ttl=3600, show_spinner=False) # 籌碼一小時更新一次即可
def fetch_twse_chips():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0"}
    macro_data, trust_data, foreign_data = [], [], []
    try:
        # 1. 三大法人買賣金額總計 (BFI82U)
        r1 = requests.get("https://www.twse.com.tw/rwd/zh/fund/BFI82U?response=json", headers=headers, timeout=5).json()
        if 'data' in r1: macro_data = r1['data']
        # 2. 投信買賣超 (TWT44U)
        r2 = requests.get("https://www.twse.com.tw/rwd/zh/fund/TWT44U?response=json", headers=headers, timeout=5).json()
        if 'data' in r2: trust_data = r2['data']
        # 3. 外資買賣超 (TWT38U)
        r3 = requests.get("https://www.twse.com.tw/rwd/zh/fund/TWT38U?response=json", headers=headers, timeout=5).json()
        if 'data' in r3: foreign_data = r3['data']
    except Exception as e:
        pass
    return macro_data, trust_data, foreign_data

with st.spinner("📡 系統啟動中：讀取全球交易所與籌碼數據..."):
    master_data = fetch_master_data()
    twii_data = fetch_twii_kline()
    macro_chips, trust_chips, foreign_chips = fetch_twse_chips()

# --- 系統健康檢查燈號 ---
st.markdown("### 🚦 系統診斷面板")
health_col1, health_col2, health_col3 = st.columns(3)
data_error = master_data.empty or twii_data.empty

with health_col1:
    if not data_error: st.success("🟢 全球 API 連線正常")
    else: st.error("🔴 交易所 API 遭阻擋")
with health_col2:
    if macro_chips: st.success("🟢 證交所籌碼連線正常")
    else: st.warning("🟡 籌碼尚未更新 (或逢休市)")
with health_col3:
    if not data_error:
        last_date = master_data.index[-1].strftime("%Y-%m-%d")
        st.success(f"🟢 數據更新至: {last_date}")
    else: st.error("🔴 啟動備用假數據模式")

st.divider()

if data_error:
    dates = pd.date_range(end=pd.Timestamp.today(), periods=6, freq='B')
    dummy_dict = {t: [100.0]*6 for t in ["^VIX", "^VIX3M", "^VVIX", "^SKEW", "^VIX9D", "^SOX", "^NDX", "TSM", "TWD=X", "^TNX", "^TWII", "^TWOII", "BTC-USD"]}
    master_data = pd.DataFrame(dummy_dict, index=dates)
    twii_data = pd.DataFrame({'Open': [100]*6, 'High': [100]*6, 'Low': [100]*6, 'Close': [100]*6, 'Volume': [1000]*6}, index=dates)

# ==========================================
# 數據安全讀取與運算區 (背景執行)
# ==========================================
t_latest, t_prev = {}, {}
for col in master_data.columns:
    valid_series = master_data[col].dropna()
    if len(valid_series) >= 2:
        t_latest[col], t_prev[col] = float(valid_series.iloc[-1]), float(valid_series.iloc[-2])
    else: t_latest[col], t_prev[col] = 0.0001, 0.0001

def get_val(ticker, latest=True): return t_latest.get(ticker, 0.0001) if latest else t_prev.get(ticker, 0.0001)

ratio_vix_vix3m = get_val('^VIX') / get_val('^VIX3M')
ratio_delta = ratio_vix_vix3m - (get_val('^VIX', False) / get_val('^VIX3M', False))
diff_vix9d_vix = get_val('^VIX9D') - get_val('^VIX')
diff_delta = diff_vix9d_vix - (get_val('^VIX9D', False) - get_val('^VIX', False))
vvix_latest = get_val('^VVIX')
vvix_delta = vvix_latest - get_val('^VVIX', False)
skew_delta = get_val('^SKEW') - get_val('^SKEW', False)
sox_pct = ((get_val('^SOX') / get_val('^SOX', False)) - 1) * 100
ndx_pct = ((get_val('^NDX') / get_val('^NDX', False)) - 1) * 100
tsm_pct = ((get_val('TSM') / get_val('TSM', False)) - 1) * 100
twd_latest = get_val('TWD=X')
twd_delta = twd_latest - get_val('TWD=X', False)
twd_ma5 = master_data['TWD=X'].dropna().tail(5).mean() if 'TWD=X' in master_data.columns and len(master_data['TWD=X'].dropna()) >= 5 else twd_latest
tnx_latest = get_val('^TNX')
tnx_delta = tnx_latest - get_val('^TNX', False)
btc_pct = ((get_val('BTC-USD') / get_val('BTC-USD', False)) - 1) * 100
twii_pct = ((get_val('^TWII') / get_val('^TWII', False)) - 1) * 100
twoii_pct = ((get_val('^TWOII') / get_val('^TWOII', False)) - 1) * 100
spread = twii_pct - twoii_pct 

delta = twii_data['Close'].diff()
gain, loss = (delta.where(delta > 0, 0)).fillna(0), (-delta.where(delta < 0, 0)).fillna(0)
rs = gain.rolling(window=14, min_periods=1).mean() / loss.rolling(window=14, min_periods=1).mean()
rsi_14 = 100 - (100 / (1 + rs))
latest_rsi = float(rsi_14.iloc[-1]) if not rsi_14.dropna().empty else 50
rsi_delta = latest_rsi - float(rsi_14.iloc[-2]) if len(rsi_14.dropna()) >= 2 else 0

tw_open, tw_close = float(twii_data['Open'].iloc[-1]), float(twii_data['Close'].iloc[-1])
tw_high, tw_low = float(twii_data['High'].iloc[-1]), float(twii_data['Low'].iloc[-1])
body = abs(tw_open - tw_close)
lower_shadow = min(tw_open, tw_close) - tw_low
upper_shadow = tw_high - max(tw_open, tw_close)
is_long_lower_shadow = (lower_shadow > body * 2) and (lower_shadow > upper_shadow) and (body > 0)

is_panic_volume = False
if len(twii_data['Volume'].dropna()) >= 6:
    vol_latest = float(twii_data['Volume'].iloc[-1])
    vol_ma5 = twii_data['Volume'].iloc[-6:-1].mean()
    is_panic_volume = vol_latest > (vol_ma5 * 1.5)

is_v_reversal = (latest_rsi < 25) and is_long_lower_shadow and is_panic_volume
is_vix_inverted = ratio_vix_vix3m > 1.05
is_short_panic = diff_vix9d_vix > 2.0

score = 0
if not data_error: 
    if ratio_vix_vix3m > 1.0: score += 3
    if latest_rsi < 30: score += 2
    if is_long_lower_shadow: score += 2
    if twd_latest < twd_ma5: score += 1
    if get_val('^SKEW') > 140: score -= 2
    if latest_rsi > 70: score -= 2
    if twd_latest > twd_ma5: score -= 1
    if tnx_latest > 4.5: score -= 1
    if is_vix_inverted: score -= 3
    if is_short_panic: score -= 2

# --- LINE 全域狀態機警報系統 ---
current_alert_state = "NONE"
current_alert_msg = ""
if not data_error:
    if is_v_reversal:
        current_alert_state = "V_REVERSAL_SNIPE"
        current_alert_msg = f"\n🚨【終極狙擊】極度恐慌 V 轉抄底訊號浮現！\n大盤 RSI 跌破絕對冰點且爆出恐慌天量留下長下影線，勝率極高，請指揮官準備進場重倉！"
    elif vvix_latest > 115: 
        current_alert_state = "VVIX_WARNING"
        current_alert_msg = f"\n🚨【系統強制避險指令生效】\n波動率異常，強烈建議建立避險部位！VVIX 飆高 ({vvix_latest:.1f})。"
    elif score >= 4:
        current_alert_state = "BUY_SIGNAL"
        current_alert_msg = f"\n🚨【獵人紅色警報】\n🟢 強烈買進訊號！\n戰力評估 {score} 分，絕佳抄底買點！"
    elif score <= -4:
        current_alert_state = "SELL_SIGNAL"
        current_alert_msg = f"\n🚨【獵人紅色警報】\n🔴 極度危險訊號！\n空方戰力 {abs(score)} 分，多重暴跌風險！"

if current_alert_state != "NONE" and line_token and line_user_id:
    if alert_memory["last_state"] != current_alert_state:
        if send_line_message(current_alert_msg, line_token, line_user_id):
            alert_memory["last_state"] = current_alert_state
elif current_alert_state == "NONE":
    alert_memory["last_state"] = "NONE"

# ==========================================
# 🖥️ 雙螢幕戰區 UI 介面 (Tab 1: 宏觀雷達 / Tab 2: 盤後籌碼)
# ==========================================
tab1, tab2 = st.tabs(["🌐 戰區一：宏觀波動雷達", "💰 戰區二：盤後籌碼狙擊"])

with tab1:
    # --- 🛡️ 獨立警告面板 ---
    if not data_error:
        if is_v_reversal:
            st.error("### 🎯【終極狙擊】極度恐慌 V 轉抄底訊號浮現！\n大盤 RSI 跌破絕對冰點且爆出恐慌天量留下長下影線，勝率極高，請準備進場！")
        elif vvix_latest > 115:
            st.error(f"### 🛡️ 系統強制避險指令生效\n目前市場波動率指標出現異常，強烈建議建立避險部位！觸發原因：VVIX 異常飆高 ({vvix_latest:.1f})。")

    # --- 🏆 頂部：綜合決策計分板 ---
    st.markdown("## 🧠 AI 戰術總分")
    if data_error: st.warning("### 📡 訊號中斷：等待連線恢復")
    elif is_v_reversal: st.success("### 🌟 無視評分：V轉抄底狙擊啟動！\n**🎯 總部指令**：閉著眼睛打進第一批資金，這是勝率極高的血洗反彈點。")
    elif score >= 4: st.success(f"### 🟢 強烈買進 ({score} 分)\n**🎯 總部指令**：天時地利齊聚！血流成河中的絕佳買點，鎖定強勢 ETF 分批重倉！")
    elif score >= 1: st.info(f"### 🟡 偏多震盪 ({score} 分)\n**🎯 總部指令**：環境偏樂觀，可小資金試單，嚴防假突破。")
    elif score <= -4: st.error(f"### 🔴 極度危險 ({score} 分)\n**🎯 總部指令**：空襲警報！外資撤退加風險飆升，千萬不可接刀。")
    else: st.warning(f"### ⚪ 多空交戰 ({score} 分)\n**🎯 總部指令**：多空訊號抵銷，耐心等待。")

    st.divider()

    st.markdown("### 📈 戰區 1：台股結構")
    t1, t2, t3 = st.columns(3)
    with t1:
        st.metric(label="大盤 RSI", value=f"{latest_rsi:.1f}", delta=f"{rsi_delta:.1f}")
        if not data_error:
            if latest_rsi < 25: st.error("🚨 **絕對冰點**\n\n🎯 **動作**: 隨時 V 轉")
            elif latest_rsi < 30: st.error("🚨 **嚴重超賣**\n\n🎯 **動作**: 準備搶反彈")
            elif latest_rsi > 70: st.warning("⚠️ **高檔過熱**\n\n🎯 **動作**: 勿追高")
            else: st.success("✅ **位階適中**\n\n🎯 **動作**: 依強勢股操作")
    with t2:
        if is_long_lower_shadow:
            st.metric(label="主力護盤", value="長下影線", delta="強力支撐", delta_color="off")
            if not data_error: st.error("🎯 **洗盤結束**\n\n🎯 **動作**: 資金進場")
        else:
            st.metric(label="主力護盤", value="無", delta="一般", delta_color="off")
            if not data_error: st.success("✅ **無極端洗盤**\n\n🎯 **動作**: 耐心等待")
    with t3:
        st.metric(label="櫃買指數", value=f"{get_val('^TWOII'):.2f}", delta=f"{twoii_pct:.2f}%")
        if not data_error:
            if spread > 1.0 and twii_pct > 0: st.error("🚨 **嚴重拉積盤**\n\n🎯 **動作**: 避開中小型與一般ETF")
            elif twoii_pct > twii_pct and twoii_pct > 0: st.success("🔥 **內資噴發**\n\n🎯 **動作**: 積極佈局中小型ETF")
            else: st.info("⚖️ **結構同步**\n\n🎯 **動作**: 依大盤趨勢操作")

    st.divider()

    st.markdown("### 🌐 戰區 2：恐慌波動 (⚠️紅向上=危險)")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("VIX 比值", f"{ratio_vix_vix3m:.2f}", delta=f"{ratio_delta:.2f}", delta_color="inverse")
        if not data_error:
            if is_vix_inverted: st.error("🚨 **極度恐慌倒掛**\n\n🎯 **動作**: 暫停買進，準備避險")
            elif ratio_vix_vix3m > 1: st.warning("⚠️ **逆價差爆發**\n\n🎯 **動作**: 準備抄底")
            else: st.success("✅ **正價差**\n\n🎯 **動作**: 抱緊多單")
    with c2:
        st.metric("VVIX 避險", f"{vvix_latest:.1f}", delta=f"{vvix_delta:.1f}", delta_color="inverse")
        if not data_error:
            if vvix_latest > 115: st.error("🔥 **造市商瘋狂避險**\n\n🎯 **動作**: 大幅減碼")
            elif vvix_latest > 110: st.warning("⚠️ **大戶避險**\n\n🎯 **動作**: 拉高停利點")
            else: st.success("✅ **情緒正常**\n\n🎯 **動作**: 按兵不動")
    with c3:
        st.metric("SKEW 尾部", f"{get_val('^SKEW'):.1f}", delta=f"{skew_delta:.1f}", delta_color="inverse")
        if not data_error:
            if get_val('^SKEW') > 140: st.error("💣 **黑天鵝預警**\n\n🎯 **動作**: 鎖死現金避險")
            else: st.success("✅ **風險低**\n\n🎯 **動作**: 維持正常配置")
    with c4:
        st.metric("VIX 乖離", f"{diff_vix9d_vix:.2f}", delta=f"{diff_delta:.2f}", delta_color="inverse")
        if not data_error:
            if is_short_panic: st.error("🔥 **突發短線崩跌**\n\n🎯 **動作**: 嚴防連續下殺")
            elif diff_vix9d_vix > 0: st.warning("⚠️ **情緒轉弱**\n\n🎯 **動作**: 隨時報復性V轉")
            else: st.success("✅ **無異常**\n\n🎯 **動作**: 不隨意短線進出")

    st.divider()
    st.markdown("### 💸 戰區 3：資金風險 (⚠️紅向上=撤退)")
    f1, f2, f3 = st.columns(3)
    with f1:
        st.metric("台幣匯率", f"{twd_latest:.2f}", delta=f"{twd_delta:.2f}", delta_color="inverse")
        if not data_error:
            if twd_latest > twd_ma5: st.warning("⚠️ **台幣貶值**\n\n🎯 **動作**: 暫緩權值股買進")
            else: st.success("✅ **熱錢流入**\n\n🎯 **動作**: 有利多頭佈局")
    with f2:
        st.metric("美債殖利率", f"{tnx_latest:.2f}%", delta=f"{tnx_delta:.2f}%", delta_color="inverse")
        if not data_error:
            if tnx_latest > 4.5: st.error("🚨 **成本過高**\n\n🎯 **動作**: 避開高本益比電子股")
            else: st.success("✅ **資金寬鬆**\n\n🎯 **動作**: 有利科技半導體")
    with f3:
        st.metric("比特幣(USD)", f"{get_val('BTC-USD'):,.0f}", f"{btc_pct:.2f}%")
        if not data_error:
            if btc_pct < -5.0: st.error("💣 **幣圈暴跌**\n\n🎯 **動作**: 嚴控股市資金水位")
            else: st.success("✅ **投機穩定**\n\n🎯 **動作**: 維持操作紀律")

    st.divider()
    st.markdown("### 🦅 戰區 4：美股風向")
    u1, u2, u3 = st.columns(3)
    with u1: st.metric("費半指數", f"{get_val('^SOX'):.2f}", f"{sox_pct:.2f}%")
    with u2: st.metric("那斯達克", f"{get_val('^NDX'):.2f}", f"{ndx_pct:.2f}%")
    with u3: st.metric("台積電 ADR", f"{get_val('TSM'):.2f}", f"{tsm_pct:.2f}%")


with tab2:
    st.markdown("## 💰 盤後籌碼動向與狙擊榜單")
    st.caption("證交所數據每日 15:30 後更新。此面板協助判讀法人資金流向。")
    
    if not macro_chips:
        st.warning("⚠️ 籌碼數據目前尚未公佈，或遭遇系統休市。請於交易日下午 15:30 後再點擊 Clear Cache 重試。")
    else:
        # 1. 三大法人整體買賣超解析
        st.markdown("### 🏦 三大法人買賣金額總計 (億元)")
        # 解析 JSON 陣列 (索引3為買賣超金額，移除逗號轉數字，除以1億)
        try:
            net_prop = round(int(macro_chips[0][3].replace(',', '')) / 100000000, 2) # 自營商自行買賣
            net_hedge = round(int(macro_chips[1][3].replace(',', '')) / 100000000, 2) # 自營商避險
            net_trust = round(int(macro_chips[2][3].replace(',', '')) / 100000000, 2) # 投信
            net_foreign = round(int(macro_chips[3][3].replace(',', '')) / 100000000, 2) # 外資
            net_total = round(int(macro_chips[5][3].replace(',', '')) / 100000000, 2) # 總計
            
            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("外資買賣超", f"{net_foreign} 億")
            mc2.metric("投信買賣超", f"{net_trust} 億")
            mc3.metric("自營商(含避險)", f"{round(net_prop + net_hedge, 2)} 億")
            
            if net_total > 0:
                mc4.metric("三大法人總計", f"{net_total} 億", "多方強勢")
            else:
                mc4.metric("三大法人總計", f"{net_total} 億", "-空方提款")
        except:
            st.error("解析三大法人數據失敗，證交所格式可能變更。")

        st.divider()

        # 2. 投信與外資買超 Top 10 排行榜
        st.markdown("### 🎯 主力買超 Top 10 狙擊榜 (張數)")
        col_trust, col_foreign = st.columns(2)
        
        with col_trust:
            st.markdown("#### 🟢 投信買超排行榜")
            if trust_chips:
                try:
                    # 索引1: 股票名稱, 索引4: 買賣超股數
                    trust_df = pd.DataFrame(trust_chips)[[(1), (4)]]
                    trust_df.columns = ["股票名稱", "買賣超張數"]
                    trust_df["買賣超張數"] = trust_df["買賣超張數"].apply(lambda x: int(str(x).replace(',', '')) // 1000)
                    trust_top10 = trust_df.sort_values(by="買賣超張數", ascending=False).head(10).reset_index(drop=True)
                    trust_top10.index = trust_top10.index + 1
                    st.dataframe(trust_top10, use_container_width=True)
                except:
                    st.write("解析投信數據失敗")
            else:
                st.write("無投信數據")

        with col_foreign:
            st.markdown("#### 🔵 外資買超排行榜")
            if foreign_chips:
                try:
                    # 索引2: 股票名稱, 索引5: 買賣超股數
                    foreign_df = pd.DataFrame(foreign_chips)[[(2), (5)]]
                    foreign_df.columns = ["股票名稱", "買賣超張數"]
                    foreign_df["買賣超張數"] = foreign_df["買賣超張數"].apply(lambda x: int(str(x).replace(',', '')) // 1000)
                    foreign_top10 = foreign_df.sort_values(by="買賣超張數", ascending=False).head(10).reset_index(drop=True)
                    foreign_top10.index = foreign_top10.index + 1
                    st.dataframe(foreign_top10, use_container_width=True)
                except:
                    st.write("解析外資數據失敗")
            else:
                st.write("無外資數據")
                
    st.divider()
    st.markdown("### 📊 快速連結戰區")
    st.link_button("👉 點此前往查看 00981A (中信成長高股息) 即時持股權重", "https://www.ezmoney.com.tw/ETF/Fund/Info?fundCode=49YTW")
