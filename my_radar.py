import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import io

st.set_page_config(page_title="獵人戰情室：波段導航儀 8.1", layout="wide")
st.title("🎯 台股波段轉折導航儀")
st.caption("雷達 8.1 終極完全體 | 實裝月線防護罩 + 融資潔淨度掃描 + 追殺地雷預警")

# --- 側邊欄：純粹的通訊引擎 ---
st.sidebar.header("🤖 LINE 警報引擎")
line_token = st.sidebar.text_input("LINE Token", type="password")
line_user_id = st.sidebar.text_input("User ID", type="password")

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
    if results: return pd.DataFrame(results)[lambda x: x.index.dayofweek < 5].ffill()
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

data_error = master_data.empty or twii_data.empty

if data_error:
    dates = pd.date_range(end=pd.Timestamp.today(), periods=6, freq='B')
    master_data = pd.DataFrame({t: [100.0]*6 for t in ["^VIX", "^VIX3M", "^VVIX", "^SKEW", "^VIX9D", "^SOX", "^NDX", "TSM", "TWD=X", "^TNX", "^TWII", "^TWOII", "BTC-USD"]}, index=dates)
    twii_data = pd.DataFrame({'Open': [100]*6, 'High': [100]*6, 'Low': [100]*6, 'Close': [100]*6, 'Volume': [1000]*6}, index=dates)

# ==========================================
# 🖥️ 雙螢幕戰區 UI 介面
# ==========================================
tab1, tab2 = st.tabs(["🌐 戰區一：宏觀波動雷達", "🎯 戰區二：終極籌碼狙擊儀"])

with tab1:
    st.markdown("### 📈 戰區 1：台股結構與宏觀波動")
    st.info("💡 宏觀指標穩定運作中，請切換至【戰區二】進行每日盤後籌碼深度掃描。")
    if not master_data.empty and not data_error:
        c_chart1, c_chart2 = st.columns(2)
        with c_chart1:
            fig1 = make_subplots(specs=[[{"secondary_y": True}]])
            fig1.add_trace(go.Scatter(x=master_data.index, y=master_data['^TWII'], name="台股", line=dict(color='#2962ff')), secondary_y=False)
            fig1.add_trace(go.Scatter(x=master_data.index, y=master_data['^VIX']/master_data['^VIX3M'], name="恐慌", line=dict(color='#ff3b3b', dash='dot')), secondary_y=True)
            fig1.add_hline(y=1.0, line_dash="solid", line_color="red", secondary_y=True)
            fig1.update_layout(title="恐慌 vs 台股", height=350, margin=dict(l=0, r=0, t=30, b=0), hovermode="x unified")
            st.plotly_chart(fig1, use_container_width=True)

with tab2:
    st.markdown("## 🎯 盤後籌碼天地連線：終極雙核過濾引擎")
    st.caption("作戰指南：請上傳今日下載的【外資】、【投信】與【融資】檔案。系統將自動執行「防接刀」、「防地雷」與「籌碼潔淨度」掃描。")
    
    col_up1, col_up2, col_up3 = st.columns(3)
    with col_up1: file_foreign = st.file_uploader("📥 1_外資買賣超.csv", type=['csv'])
    with col_up2: file_trust = st.file_uploader("📥 3_投信買賣超.csv", type=['csv'])
    with col_up3: file_margin = st.file_uploader("📥 4_融資融券餘額.csv (選填)", type=['csv'])

    # --- 資料清洗引擎 ---
    def clean_twse_csv(file_bytes):
        try: content = file_bytes.decode('utf-8-sig')
        except: content = file_bytes.decode('big5', errors='ignore')
        lines = content.splitlines()
        header_idx = -1
        for i, line in enumerate(lines):
            if '證券代號' in line and '證券名稱' in line:
                header_idx = i; break
        if header_idx == -1: return pd.DataFrame()
        df = pd.read_csv(io.StringIO(content), skiprows=header_idx, engine='python', on_bad_lines='skip')
        df.columns = df.columns.str.strip().str.replace('"', '')
        target_col = next((col for col in df.columns if '買賣超' in col and '股數' in col), None)
        if not target_col: return pd.DataFrame()
        df['證券代號'] = df['證券代號'].astype(str).str.replace('=', '').str.replace('"', '').str.strip()
        df['證券名稱'] = df['證券名稱'].astype(str).str.strip()
        df[target_col] = pd.to_numeric(df[target_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        df['買賣超張數'] = (df[target_col] / 1000).astype(int)
        return df[['證券代號', '證券名稱', '買賣超張數']].dropna()

    def clean_margin_csv(file_bytes):
        try: content = file_bytes.decode('utf-8-sig')
        except: content = file_bytes.decode('big5', errors='ignore')
        lines = content.splitlines()
        header_idx = -1
        for i, line in enumerate(lines):
            if '股票代號' in line and '前日餘額' in line:
                header_idx = i; break
        if header_idx == -1: return pd.DataFrame(columns=['證券代號', '融資增減(張)'])
        df = pd.read_csv(io.StringIO("\n".join(lines[header_idx:])), header=None, skiprows=1, engine='python', on_bad_lines='skip')
        df_margin = df[[0, 5, 6]].copy()
        df_margin[0] = df_margin[0].astype(str).str.replace('=', '').str.replace('"', '').str.strip()
        df_margin[5] = pd.to_numeric(df_margin[5].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        df_margin[6] = pd.to_numeric(df_margin[6].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        df_margin['融資增減(張)'] = (df_margin[6] - df_margin[5]).astype(int)
        return df_margin[[0, '融資增減(張)']].rename(columns={0: '證券代號'})

    # --- 雲端技術面掃描引擎 (yfinance) ---
    @st.cache_data(ttl=3600, show_spinner=False)
    def get_trend_status(tickers):
        status_dict = {}
        for ticker in tickers:
            try:
                hist = yf.Ticker(f"{ticker}.TW").history(period="2mo")
                if hist.empty: hist = yf.Ticker(f"{ticker}.TWO").history(period="2mo")
                if not hist.empty and len(hist) >= 20:
                    ma20 = hist['Close'].rolling(window=20).mean().iloc[-1]
                    close = hist['Close'].iloc[-1]
                    status_dict[ticker] = "🟢 站上月線 (多)" if close > ma20 else "🔴 跌破月線 (空)"
                else: status_dict[ticker] = "🟡 待確認"
            except: status_dict[ticker] = "⚫ 未知"
        return status_dict

    if file_foreign and file_trust:
        with st.spinner("⚙️ AI 終極雙核過濾引擎運算中..."):
            df_foreign = clean_twse_csv(file_foreign.read())
            df_trust = clean_twse_csv(file_trust.read())
            df_margin = clean_margin_csv(file_margin.read()) if file_margin else pd.DataFrame(columns=['證券代號', '融資增減(張)'])
            
            if not df_foreign.empty and not df_trust.empty:
                merged = pd.merge(df_foreign, df_trust, on=['證券代號', '證券名稱'], suffixes=('_外資', '_投信'))
                
                # --- 模組 1：共識買超 + 趨勢掃描 + 融資掃描 ---
                consensus = merged[(merged['買賣超張數_外資'] > 0) & (merged['買賣超張數_投信'] > 0)].copy()
                consensus['雙主力總買超'] = consensus['買賣超張數_外資'] + consensus['買賣超張數_投信']
                consensus = consensus.sort_values(by='雙主力總買超', ascending=False).head(15)
                
                if not consensus.empty:
                    # 加入融資數據
                    if not df_margin.empty:
                        consensus = pd.merge(consensus, df_margin, on='證券代號', how='left').fillna(0)
                        consensus['籌碼潔淨度'] = consensus['融資增減(張)'].apply(lambda x: "✨ 極佳 (散戶退)" if x < 0 else "⚠️ 凌亂 (散戶進)")
                    
                    # 啟動雲端月線檢查
                    trend_dict = get_trend_status(consensus['證券代號'].tolist())
                    consensus['月線趨勢'] = consensus['證券代號'].map(trend_dict)
                    
                    consensus.index = range(1, len(consensus) + 1)
                    
                    st.divider()
                    st.markdown("### 🔥 【S 級狙擊名單】土洋共識買超 (Top 15)")
                    st.success("🎯 **操作指南**：優先鎖定【籌碼潔淨度 = ✨極佳】且【月線趨勢 = 🟢站上月線】的標的，勝率最高！避開跌破月線的接刀股。")
                    st.dataframe(consensus, use_container_width=True)

                # --- 模組 2：地雷預警 (雙重追殺榜) ---
                sell_consensus = merged[(merged['買賣超張數_外資'] < 0) & (merged['買賣超張數_投信'] < 0)].copy()
                sell_consensus['雙主力總賣超'] = sell_consensus['買賣超張數_外資'] + sell_consensus['買賣超張數_投信']
                sell_consensus = sell_consensus.sort_values(by='雙主力總賣超', ascending=True).head(10).reset_index(drop=True)
                sell_consensus.index = sell_consensus.index + 1
                
                st.divider()
                st.markdown("### 💣 【地雷預警名單】土洋無情拋售 (Top 10)")
                if not sell_consensus.empty:
                    st.error("🚨 **AI 警告**：以下標的遭到外資與投信「聯手重擊拋售」，籌碼極度渙散，就算跌停也【嚴禁摸底接刀】！")
                    st.dataframe(sell_consensus, use_container_width=True)
