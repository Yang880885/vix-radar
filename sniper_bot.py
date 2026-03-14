import os
import yfinance as yf
import pandas as pd
import requests
import json
from datetime import datetime
import pytz

# ==========================================
# ⚙️ 系統設定區 (最高資安防護)
# ==========================================
LINE_TOKEN = os.environ.get("LINE_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")

if not LINE_TOKEN or not LINE_USER_ID:
    print("❌ 致命錯誤：找不到 LINE 金鑰，請確認 GitHub Secrets 是否設定正確。")
    exit()

# 🎯 狙擊監控清單 (指揮官專屬彈匣)
WATCHLIST = {
    "2330.TW": "台積電",
    "2317.TW": "鴻海",
    "2603.TW": "長榮",
    "4960.TW": "誠美材",
    "3013.TW": "晟銘電",
    "0050.TW": "元大台灣50",
    "00631L.TW": "元大台灣50正2",
    "0052.TW": "富邦科技",
    "00981A.TW": "主動統一台股增長",
    "009816.TW": "凱基台灣TOP50"
}

# ==========================================
# 📡 戰術運算與通訊區
# ==========================================
def send_line_message(message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"}
    payload = {"to": LINE_USER_ID, "messages": [{"type": "text", "text": message}]}
    requests.post(url, headers=headers, data=json.dumps(payload))

def calculate_indicators(df):
    # --- 1. KD 指標 ---
    low_min = df['Low'].rolling(window=9, min_periods=1).min()
    high_max = df['High'].rolling(window=9, min_periods=1).max()
    df['RSV'] = 100 * (df['Close'] - low_min) / (high_max - low_min)
    df['K'] = df['RSV'].ewm(com=2, adjust=False).mean()
    df['D'] = df['K'].ewm(com=2, adjust=False).mean()
    
    # --- 2. MACD 指標 ---
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['DIF'] = ema12 - ema26
    df['MACD'] = df['DIF'].ewm(span=9, adjust=False).mean()
    df['OSC'] = df['DIF'] - df['MACD']
    
    # --- 3. 均線與布林通道 ---
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['STD20'] = df['Close'].rolling(window=20).std()
    df['Upper_Band'] = df['MA20'] + 2 * df['STD20']
    
    # --- 4. RSI 指標 (用於偵測極度過熱) ---
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.rolling(window=14, min_periods=1).mean()
    avg_loss = loss.rolling(window=14, min_periods=1).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # --- 5. 乖離率 BIAS (股價偏離月線的百分比) ---
    df['BIAS20'] = (df['Close'] - df['MA20']) / df['MA20'] * 100
    
    # --- 6. 爆量偵測 (5日均量) ---
    df['Vol_MA5'] = df['Volume'].rolling(window=5).mean()
    
    return df

def run_sniper_scan():
    tz = pytz.timezone('Asia/Taipei')
    today_str = datetime.now(tz).strftime('%Y-%m-%d %H:%M')
    print(f"🔍 [{today_str}] 啟動終極收割掃描...")
    
    alerts = []
    
    for ticker, name in WATCHLIST.items():
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="6mo")
            if len(df) < 30: continue
                
            df = calculate_indicators(df)
            
            # 取得最新數值
            curr_close = df['Close'].iloc[-1]
            curr_open = df['Open'].iloc[-1]
            prev_close = df['Close'].iloc[-2]
            
            prev_k, curr_k = df['K'].iloc[-2], df['K'].iloc[-1]
            prev_d, curr_d = df['D'].iloc[-2], df['D'].iloc[-1]
            prev_osc, curr_osc = df['OSC'].iloc[-2], df['OSC'].iloc[-1]
            
            curr_upper = df['Upper_Band'].iloc[-1]
            curr_ma20 = df['MA20'].iloc[-1]
            
            curr_rsi = df['RSI'].iloc[-1]
            curr_bias20 = df['BIAS20'].iloc[-1]
            curr_vol = df['Volume'].iloc[-1]
            curr_vol_ma5 = df['Vol_MA5'].iloc[-1]
            
            bullish_signals = [] # 買進
            profit_signals = []  # 極限逃頂 (賣出)
            bearish_signals = [] # 停損撤退
            
            # ==========================================
            # 🟢 【攻擊訊號】(起漲點)
            # ==========================================
            if prev_k < prev_d and curr_k > curr_d and curr_k < 50: 
                bullish_signals.append(f"✨ KD 低檔黃金交叉 (K={curr_k:.1f})")
            if prev_osc <= 0 and curr_osc > 0: 
                bullish_signals.append(f"📈 MACD 柱狀體翻紅")
            if curr_close > curr_upper: 
                bullish_signals.append(f"🔥 強勢突破布林上軌")
                
            # ==========================================
            # 💰 【極限逃頂】(指揮官專屬：過熱/爆量/乖離)
            # ==========================================
            # 1. 技術指標過熱 (RSI > 80 或 KD 高檔反轉)
            if curr_rsi > 80:
                profit_signals.append(f"🔥 RSI 極度超買過熱 (RSI={curr_rsi:.1f})")
            if prev_k >= 85 and curr_k < 85:
                profit_signals.append(f"🔥 KD 高檔極限反轉 (K值自 85 跌落)")
                
            # 2. 爆量且滯漲 (成交量暴增至 5 日均量的 2 倍以上，且收黑 K 線)
            if curr_vol > (curr_vol_ma5 * 2) and curr_close <= curr_open:
                profit_signals.append(f"💣 爆量滯漲 (高檔爆量收黑，主力出貨嫌疑)")
                
            # 3. 乖離率過大 (股價偏離月線超過 10%，隨時報復性回檔)
            if curr_bias20 > 10.0:
                profit_signals.append(f"🚀 正乖離率過大 ({curr_bias20:.1f}%)，隨時回測月線")

            # ==========================================
            # 🔴 【波段撤退】(跌破防線停損)
            # ==========================================
            if prev_close >= curr_ma20 and curr_close < curr_ma20:
                bearish_signals.append(f"📉 跌破生命月線 (20MA: {curr_ma20:.1f})")
                
            # 打包訊息
            if bullish_signals or profit_signals or bearish_signals:
                msg = f"🎯 {name} ({ticker.replace('.TW', '')})\n🔸 最新收盤: {curr_close:.2f}\n"
                if bullish_signals:
                    msg += "🟢 【攻擊鎖定】\n - " + "\n - ".join(bullish_signals) + "\n"
                if profit_signals:
                    msg += "💰 【極限逃頂警報】(準備獲利了結)\n - " + "\n - ".join(profit_signals) + "\n"
                if bearish_signals:
                    msg += "🔴 【波段撤退警報】(停損/防守)\n - " + "\n - ".join(bearish_signals) + "\n"
                alerts.append(msg.strip())
                
        except Exception as e:
            pass
            
    if alerts:
        send_line_message(f"🚨【狙擊手戰況通報】\n掃描時間: {today_str}\n\n" + "\n\n".join(alerts))
    else:
        send_line_message(f"📡【狙擊手回報】\n掃描時間: {today_str}\n無標的觸發訊號，繼續潛伏。")

if __name__ == "__main__":
    run_sniper_scan()
