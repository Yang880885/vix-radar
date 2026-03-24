import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import io

st.set_page_config(page_title="獵人戰情室：波段導航儀 8.0", layout="wide")
st.title("🎯 台股波段轉折導航儀")
st.caption("雷達 8.0 土洋共識狙擊版 | 實裝天地連線系統 + 外資投信重疊買超過濾引擎")

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

with st.spinner("📡 系統啟動中：讀取全球交易所數據..."):
    master_data = fetch_master_data()
    twii_data = fetch_twii_kline()

# --- 系統健康檢查燈號 ---
st.markdown("### 🚦 系統診斷面板")
health_col1, health_col2, health_col3 = st.columns(3)
data_error = master_data.empty or twii_data.empty

with health_col1:
    if not data_error: st.success("🟢 全球 API 連線正常")
    else: st.error("🔴 交易所 API 遭阻擋")
with health_col2:
    st.info("🔵 籌碼數據已切換為「手動接收模式」")
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
# 數據安全讀取與運算區
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

# ==========================================
# 🖥️ 雙螢幕戰區 UI 介面
# ==========================================
tab1, tab2 = st.tabs(["🌐 戰區一：宏觀波動雷達", "🎯 戰區二：土洋共識籌碼狙擊"])

with tab1:
    if not data_error:
        if is_v_reversal: st.error("### 🎯【終極狙擊】極度恐慌 V 轉抄底訊號浮現！\n大盤 RSI 跌破絕對冰點且爆出恐慌天量留下長下影線，請準備進場！")
        elif vvix_latest > 115: st.error(f"### 🛡️ 系統強制避險指令生效\n目前市場波動率指標出現異常，強烈建議建立避險部位！觸發原因：VVIX 異常飆高 ({vvix_latest:.1f})。")

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
    with c1: st.metric("VIX 比值", f"{ratio_vix_vix3m:.2f}", delta=f"{ratio_delta:.2f}", delta_color="inverse")
    with c2: st.metric("VVIX 避險", f"{vvix_latest:.1f}", delta=f"{vvix_delta:.1f}", delta_color="inverse")
    with c3: st.metric("SKEW 尾部", f"{get_val('^SKEW'):.1f}", delta=f"{skew_delta:.1f}", delta_color="inverse")
    with c4: st.metric("VIX 乖離", f"{diff_vix9d_vix:.2f}", delta=f"{diff_delta:.2f}", delta_color="inverse")

    st.divider()
    st.markdown("### 💸 戰區 3：資金風險 (⚠️紅向上=撤退)")
    f1, f2, f3 = st.columns(3)
    with f1: st.metric("台幣匯率", f"{twd_latest:.2f}", delta=f"{twd_delta:.2f}", delta_color="inverse")
    with f2: st.metric("美債殖利率", f"{tnx_latest:.2f}%", delta=f"{tnx_delta:.2f}%", delta_color="inverse")
    with f3: st.metric("比特幣(USD)", f"{get_val('BTC-USD'):,.0f}", f"{btc_pct:.2f}%")

    st.divider()
    st.markdown("### 🔭 戰區 4：鑑古知今")
    if not master_data.empty and not data_error:
        c_chart1, c_chart2 = st.columns(2)
        with c_chart1:
            fig1 = make_subplots(specs=[[{"secondary_y": True}]])
            fig1.add_trace(go.Scatter(x=master_data.index, y=master_data['^TWII'], name="台股", line=dict(color='#2962ff')), secondary_y=False)
            fig1.add_trace(go.Scatter(x=master_data.index, y=master_data['^VIX']/master_data['^VIX3M'], name="恐慌", line=dict(color='#ff3b3b', dash='dot')), secondary_y=True)
            fig1.add_hline(y=1.0, line_dash="solid", line_color="red", secondary_y=True)
            fig1.update_layout(title="恐慌 vs 台股", height=350, margin=dict(l=0, r=0, t=30, b=0), hovermode="x unified")
            st.plotly_chart(fig1, use_container_width=True)

        if 'TWD=X' in master_data.columns:
            with c_chart2:
                fig2 = make_subplots(specs=[[{"secondary_y": True}]])
                fig2.add_trace(go.Scatter(x=master_data.index, y=master_data['^TWII'], name="台股", line=dict(color='#2962ff')), secondary_y=False)
                fig2.add_trace(go.Scatter(x=master_data.index, y=master_data['TWD=X'], name="匯率", line=dict(color='#00c853', dash='dot')), secondary_y=True)
                fig2.update_layout(title="熱錢 vs 台股", height=350, margin=dict(l=0, r=0, t=30, b=0), hovermode="x unified")
                st.plotly_chart(fig2, use_container_width=True)


with tab2:
    st.markdown("## 🎯 盤後籌碼天地連線：土洋共識過濾引擎")
    st.info("💡 **作戰指南：** 請先執行您電腦桌面上的「一鍵下載籌碼.bat」，接著將抓到的 CSV 檔案拖曳至下方對應的空位。系統將自動為您鎖定雙方共同買超的飆股！")
    
    col_up1, col_up2 = st.columns(2)
    with col_up1:
        file_foreign = st.file_uploader("📥 請上傳【1_外資買賣超.csv】", type=['csv'])
    with col_up2:
        file_trust = st.file_uploader("📥 請上傳【3_投信買賣超.csv】", type=['csv'])

    # --- 內部資料清洗引擎 ---
    def clean_twse_csv(file_bytes):
        try:
            content = file_bytes.decode('utf-8-sig')
        except:
            content = file_bytes.decode('big5', errors='ignore')
            
        lines = content.splitlines()
        header_idx = -1
        for i, line in enumerate(lines):
            if '證券代號' in line and '證券名稱' in line:
                header_idx = i
                break
                
        if header_idx == -1: return pd.DataFrame()
        
        df = pd.read_csv(io.StringIO(content), skiprows=header_idx, engine='python', on_bad_lines='skip')
        df.columns = df.columns.str.strip().str.replace('"', '')
        
        # 尋找淨買賣超欄位
        target_col = None
        for col in df.columns:
            if '買賣超' in col and '股數' in col:
                target_col = col
                break
                
        if not target_col: return pd.DataFrame()
        
        # 資料清理
        df['證券代號'] = df['證券代號'].astype(str).str.replace('=', '').str.replace('"', '').str.strip()
        df['證券名稱'] = df['證券名稱'].astype(str).str.strip()
        df[target_col] = df[target_col].astype(str).str.replace(',', '').str.strip()
        df[target_col] = pd.to_numeric(df[target_col], errors='coerce').fillna(0)
        
        # 將股數轉換為張數
        df['買賣超張數'] = (df[target_col] / 1000).astype(int)
        
        return df[['證券代號', '證券名稱', '買賣超張數']].dropna()

    if file_foreign and file_trust:
        with st.spinner("⚙️ AI 戰術引擎正在過濾土洋共識名單..."):
            df_foreign = clean_twse_csv(file_foreign.read())
            df_trust = clean_twse_csv(file_trust.read())
            
            if not df_foreign.empty and not df_trust.empty:
                # 進行交集比對
                merged = pd.merge(df_foreign, df_trust, on=['證券代號', '證券名稱'], suffixes=('_外資', '_投信'))
                # 篩選條件：外資與投信同時買超大於 0 張
                consensus = merged[(merged['買賣超張數_外資'] > 0) & (merged['買賣超張數_投信'] > 0)].copy()
                consensus['雙主力總買超'] = consensus['買賣超張數_外資'] + consensus['買賣超張數_投信']
                consensus = consensus.sort_values(by='雙主力總買超', ascending=False).head(15).reset_index(drop=True)
                consensus.index = consensus.index + 1
                
                st.divider()
                st.markdown("### 🔥 【終極狙擊名單】土洋共識重疊買超 (Top 15)")
                if not consensus.empty:
                    st.success("🎯 **AI 判定**：以下標的在今日殺盤中，獲得外資與投信「同時」砸重金買進，具備極強的籌碼防禦力與攻擊潛力！")
                    st.dataframe(consensus, use_container_width=True)
                else:
                    st.warning("⚔️ 今日大盤撕裂嚴重，外資與投信沒有任何交集買超的標的。")

                # ================= 新增：土洋聯合追殺榜 =================
                sell_consensus = merged[(merged['買賣超張數_外資'] < 0) & (merged['買賣超張數_投信'] < 0)].copy()
                sell_consensus['雙主力總賣超'] = sell_consensus['買賣超張數_外資'] + sell_consensus['買賣超張數_投信']
                sell_consensus = sell_consensus.sort_values(by='雙主力總賣超', ascending=True).head(15).reset_index(drop=True)
                sell_consensus.index = sell_consensus.index + 1
                
                st.divider()
                st.markdown("### 💣 【地雷預警名單】土洋共識重疊賣超 (Top 15)")
                if not sell_consensus.empty:
                    st.error("🚨 **AI 警告**：以下標的遭到外資與投信「聯手無情拋售」，籌碼極度渙散，嚴禁摸底接刀！")
                    st.dataframe(sell_consensus, use_container_width=True)
                else:
                    st.success("🛡️ 今日無雙法人聯合追殺之標的。")

                # 顯示個別排行榜
                st.divider()
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("#### 🔵 外資買超排行榜")
                    st.dataframe(df_foreign.sort_values(by='買賣超張數', ascending=False).head(10).reset_index(drop=True), use_container_width=True)
                with c2:
                    st.markdown("#### 🟢 投信買超排行榜")
                    st.dataframe(df_trust.sort_values(by='買賣超張數', ascending=False).head(10).reset_index(drop=True), use_container_width=True)
            else:
                st.error("❌ 檔案解析失敗，請確認上傳的是證交所原始的 CSV 檔案。")
