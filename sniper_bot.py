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

# 🎯 狙擊監控清單
WATCHLIST = {
    "2330.TW": "台積電",
    "2317.TW": "鴻海",
    "2485.TW": "兆赫",
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
    # KD
    low_min = df['Low'].rolling(window=9, min_periods=1).min()
    high_max = df['High'].rolling(window=9, min_periods=1).max()
    df['RSV'] = 100 * (df['Close'] - low_min) / (high_max - low_min)
    df['K'] = df['RSV'].ewm(com=2, adjust=False).mean()
    df['D'] = df['K'].ewm(com=2, adjust=False).mean()
    
    # MACD
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['DIF'] = ema12 - ema26
    df['MACD'] = df['DIF'].ewm(span=9, adjust=False).mean()
    df['OSC'] = df['DIF'] - df['MACD']
    
    # 布林通道與均線防線 (5MA 短線停利, 20MA 波段防守)
    df['MA5'] = df['Close'].rolling(window=5).mean()  # 新增 5日線(飆股停利線)
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['STD20'] = df['Close'].rolling(window=20).std()
    df['Upper_Band'] = df['MA20'] + 2 * df['STD20']
    
    return df

def run_sniper_scan():
    tz = pytz.timezone('Asia/Taipei')
    today_str = datetime.now(tz).strftime('%Y-%m-%d %H:%M')
    print(f"🔍 [{today_str}] 啟動攻守雙向掃描...")
    
    alerts = []
    
    for ticker, name in WATCHLIST.items():
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="6mo")
            if len(df) < 30: continue
                
            df = calculate_indicators(df)
            
            # 取得昨日與今日數值
            curr_close = df['Close'].iloc[-1]
            prev_close = df['Close'].iloc[-2]
            
            prev_k, curr_k = df['K'].iloc[-2], df['K'].iloc[-1]
            prev_d, curr_d = df['D'].iloc[-2], df['D'].iloc[-1]
            
            prev_osc, curr_osc = df['OSC'].iloc[-2], df['OSC'].iloc[-1]
            
            curr_upper = df['Upper_Band'].iloc[-1]
            
            prev_ma5 = df['MA5'].iloc[-2]
            curr_ma5 = df['MA5'].iloc[-1]
            
            prev_ma20 = df['MA20'].iloc[-2]
            curr_ma20 = df['MA20'].iloc[-1]
            
            bullish_signals = [] # 多方攻擊
            profit_signals = []  # 高檔極限停利 (賣在相近最高點)
            bearish_signals = [] # 空方撤退 (波段棄守)
            
            # 🟢 攻擊訊號 (起漲偵測)
            if prev_k < prev_d and curr_k > curr_d: 
                bullish_signals.append(f"✨ KD 黃金交叉 (K={curr_k:.1f})")
            if prev_osc <= 0 and curr_osc > 0: 
                bullish_signals.append(f"📈 MACD 柱狀體翻紅")
            if curr_close > curr_upper: 
                bullish_signals.append(f"🔥 突破布林上軌 ({curr_upper:.1f})")
                
            # 💰 高檔極限停利 (賣在相近最高點)
            if prev_k >= 80 and curr_k < 80:
                profit_signals.append(f"💰 KD 高檔過熱反轉 (K值自 80 以上跌落)")
            if prev_close >= prev_ma5 and curr_close < curr_ma5:
                profit_signals.append(f"💰 跌破極短線 5MA ({curr_ma5:.1f}) - 飆漲慣性打破")
                
            # 🔴 波段撤退訊號 (轉弱與破線偵測)
            if prev_close >= prev_ma20 and curr_close < curr_ma20:
                bearish_signals.append(f"📉 跌破生命月線 (20MA: {curr_ma20:.1f})")
            if prev_k > prev_d and curr_k < curr_d and curr_k < 80: # 排除掉上面的高檔反轉
                bearish_signals.append(f"💀 KD 死亡交叉 (K={curr_k:.1f})")
            if prev_osc >= 0 and curr_osc < 0:
                bearish_signals.append(f"🩸 MACD 柱狀體翻綠 (動能轉弱)")
                
            # 打包訊息
            if bullish_signals or profit_signals or bearish_signals:
                msg = f"🎯 {name} ({ticker.replace('.TW', '')})\n🔸 最新收盤: {curr_close:.2f}\n"
                if bullish_signals:
                    msg += "🟢 【攻擊鎖定】\n - " + "\n - ".join(bullish_signals) + "\n"
                if profit_signals:
                    msg += "💰 【極限停利入袋】(賣在相近最高點)\n - " + "\n - ".join(profit_signals) + "\n"
                if bearish_signals:
                    msg += "🔴 【波段撤退警報】\n - " + "\n - ".join(bearish_signals) + "\n"
                alerts.append(msg.strip())
                
        except Exception as e:
            pass
            
    if alerts:
        send_line_message(f"🚨【狙擊手戰況通報】\n掃描時間: {today_str}\n\n" + "\n\n".join(alerts))
    else:
        send_line_message(f"📡【狙擊手回報】\n掃描時間: {today_str}\n無標的觸發訊號，繼續潛伏。")

if __name__ == "__main__":
    run_sniper_scan()
