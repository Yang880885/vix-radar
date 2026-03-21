import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- 1. 設定網頁標題與樣式 ---
st.set_page_config(page_title="VIX-Radar 戰情室", layout="wide")
st.title("🎯 VIX-Radar 台股波段轉折導航儀")
st.markdown("---")

# --- 2. 核心分析類別 (整合 FinMind API) ---
class VixRadarEngine:
    def __init__(self, api_token=None):
        self.api_url = "https://api.finmindtrade.com/api/v4/data"
        self.api_token = api_token
        self.headers = {"Authorization": f"Bearer {api_token}"} if api_token else {}

    def analyze_stock_warrant(self, stock_id, target_date):
        """
        抓取權證資料並計算 P/C Ratio
        """
        # 向 FinMind 請求權證成交資料
        params = {
            "dataset": "TaiwanStockWarrantTickInfo",
            "data_id": stock_id,
            "date": target_date
        }
        
        try:
            resp = requests.get(self.api_url, params=params, headers=self.headers)
            if resp.status_code != 200:
                return {"error": "API 請求失敗，請檢查 Token"}
            
            data = resp.json().get('data', [])
            
            if not data:
                return {"error": f"⚠️ 找不到 {stock_id} 在 {target_date} 的權證資料。"}
            
            df = pd.DataFrame(data)
            
            # 判斷認購 (Call) 或 認售 (Put)
            df['type'] = df['warrant_id'].apply(lambda x: 'Put' if x.endswith('P') else 'Call')
            
            # 數據加總
            summary = df.groupby('type')['amount'].sum()
            call_amt = summary.get('Call', 0)
            put_amt = summary.get('Put', 0)
            
            # 計算 P/C Ratio
            pc_ratio = put_amt / call_amt if call_amt > 0 else 0
            
            # 雷達綜合評估
            if pc_ratio < 0.3:
                status = "🔥 極度樂觀：大戶狂掃認購"
                level = "success"
            elif 0.3 <= pc_ratio < 0.7:
                status = "↗️ 偏多攻擊：多頭占優"
                level = "info"
            elif 0.7 <= pc_ratio < 1.2:
                status = "↔️ 盤整偏多"
                level = "warning"
            else:
                status = "⚠️ 警戒：避險情緒升溫"
                level = "error"
            
            return {
                "stock_id": stock_id,
                "date": target_date,
                "call_amt": call_amt,
                "put_amt": put_amt,
                "pc_ratio": round(pc_ratio, 4),
                "status": status,
                "level": level
            }
            
        except Exception as e:
            return {"error": f"❌ 系統異常: {str(e)}"}

# --- 3. 實例化引擎 ---
# 如果你有 FinMind Token，請在這裡填入，或用 st.secrets 讀取
# token = st.secrets["FINMIND_TOKEN"] 
token = None 
engine = VixRadarEngine(api_token=token)

# --- 4. 側邊欄：輸入區 ---
st.sidebar.header("📊 戰術輸入")
stock_id = st.sidebar.text_input("輸入股票代號", value="2308", max_chars=6)
# 預設為最新交易日，但需注意 API 更新時間，這裡暫設 2026-03-20
analysis_date = st.sidebar.date_input("分析日期", value=datetime(2026, 3, 20))
analysis_date_str = analysis_date.strftime("%Y-%m-%d")

# --- 模擬你的 VIX/VVIX 數據 ---
st.sidebar.markdown("---")
st.sidebar.subheader("📡 VIX 避險引擎數據 (模擬)")
vix_ratio = st.sidebar.number_input("VIX 比值", value=0.98, step=0.01)
vvix = st.sidebar.number_input("VVIX 避險", value=126.3, step=0.1)

# 按下分析按鈕
analyze_btn = st.sidebar.button("開始掃描")

# --- 5. 主介面：顯示區 ---
if analyze_btn:
    # 執行權證分析
    warrant_result = engine.analyze_stock_warrant(stock_id, analysis_date_str)
    
    # 檢查是否有錯誤
    if "error" in warrant_result:
        st.error(warrant_result["error"])
    else:
        # 顯示個股權證戰情
        st.subheader(f"🛡️ 戰區 0：{stock_id} 個股權證籌碼")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("認購金額", f"{warrant_result['call_amt']:,.0f}")
        c2.metric("認售金額", f"{warrant_result['put_amt']:,.0f}")
        c3.metric("P/C Ratio", warrant_result['pc_ratio'])
        
        # 使用自定義的警示方塊
        st.markdown(f"""
        <div style="background-color: {'#d4edda' if warrant_result['level']=='success' else '#d1ecf1' if warrant_result['level']=='info' else '#fff3cd' if warrant_result['level']=='warning' else '#f8d7da'}; padding: 10px; border-radius: 5px; color: black; border: 1px solid black; font-weight: bold; text-align: center;">
            {warrant_result['status']}
        </div>
        """, unsafe_allow_stdio=True)
        
        st.markdown("---")
        
        # 顯示你原本的 VIX 雷達戰情
        st.subheader("💡 戰術決策中心")
        
        # 模擬你的 AI 戰術總分邏輯
        ai_score = 0
        if vvix > 120: ai_score -= 2 # VVIX 異常扣分
        if vix_ratio < 1.0: ai_score += 1 # VIX 正價差加分
        if warrant_result['pc_ratio'] < 0.5: ai_score += 1 # 權證多頭加分
        
        t_col1, t_col2 = st.columns([1, 2])
        
        # 左側顯示總分
        with t_col1:
            st.markdown("### 🧠 AI 戰術總分")
            if ai_score >= 1:
                st.success(f"🟢 多頭攻擊 ({ai_score} 分)")
            elif ai_score <= -1:
                st.error(f"🔴 強制避險 ({ai_score} 分)")
            else:
                st.warning(f"⚪ 多空交戰 ({ai_score} 分)")
        
        # 右側顯示 VIX / VVIX 警示
        with t_col2:
            st.markdown("### 🌐 戰區 2：恐慌波動")
            v1, v2 = st.columns(2)
            v1.metric("VIX 比值", vix_ratio, help="> 1 代表市場情緒偏向恐慌")
            # 重點警示 VVIX
            if vvix > 120:
                v2.metric("VVIX 避險", vvix, help="> 120 代表大戶瘋狂買進保險", delta_color="inverse", delta="⚠️ 異常飆高")
            else:
                v2.metric("VVIX 避險", vvix, help="正常區間")
                
        # 綜合建議
        st.markdown("---")
        st.markdown("### 🔭 綜合戰術建議")
        if vvix > 120 and warrant_result['pc_ratio'] > 1:
            st.markdown("🎯 **指令：** 強制避險！VVIX 與權證籌碼同步示警，市場即將發生大幅波動，建議建立避險部位。")
        elif warrant_result['pc_ratio'] < 0.5 and vix_ratio < 1.0:
            st.markdown("🎯 **指令：** 多頭持續。個股籌碼熱絡且市場情緒穩定，可依個別強勢股操作。")
        else:
            st.markdown("🎯 **指令：** 耐心等待。多空訊號抵銷，市場尋找方向中。")
