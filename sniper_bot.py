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
# 透過環境變數安全讀取 GitHub Secrets，程式碼裡完全沒有明碼！
LINE_TOKEN = os.environ.get("LINE_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")

if not LINE_TOKEN or not LINE_USER_ID:
    print("❌ 致命錯誤：找不到 LINE 金鑰，請確認 GitHub Secrets 是否設定正確。")
    exit()

# 🎯 狙擊監控清單 (指揮官請在此處手動換彈匣)
WATCHLIST = {
    "2330.TW": "台積電",
    "2317.TW": "鴻海",
    "2603.TW": "長榮",
    "2454.TW": "聯發科",
    "3231.TW": "緯創",
    "0050.TW": "元大台灣50",
    "00929.TW": "復華台灣科技優息"
}

# ==========================================
# 📡 戰術運算與通訊區 (以下不需更動)
# ==========================================
def send_line_message(message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"}
    payload = {"to": LINE_USER_ID, "messages": [{"type": "text", "text": message}]}
    requests.post(url, headers=headers, data=json.dumps(payload))

def calculate_indicators(df):
    low_min = df['Low'].rolling(window=9, min_periods=1).min()
    high_max = df['High'].rolling(window=9, min_periods=1).max()
    df['RSV'] = 100 * (df['Close'] - low_min) / (high_max - low_min)
    df['K'] = df['RSV'].ewm(com=2, adjust=False).mean()
    df['D'] = df['K'].ewm(com=2, adjust=False).mean()
    
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['DIF'] = ema12 - ema26
    df['MACD'] = df['DIF'].ewm(span=9, adjust=False).mean()
    df['OSC'] = df['DIF'] - df['MACD']
    
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['STD20'] = df['Close'].rolling(window=20).std()
    df['Upper_Band'] = df['MA20'] + 2 * df['STD20']
    return df

def run_sniper_scan():
    tz = pytz.timezone('Asia/Taipei')
    today_str = datetime.now(tz).strftime('%Y-%m-%d %H:%M')
    print(f"🔍 [{today_str}] 啟動狙擊掃描...")
    
    alerts = []
    
    for ticker, name in WATCHLIST.items():
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="6mo")
            if len(df) < 30: continue
                
            df = calculate_indicators(df)
            curr_close = df['Close'].iloc[-1]
            prev_k, curr_k = df['K'].iloc[-2], df['K'].iloc[-1]
            prev_d, curr_d = df['D'].iloc[-2], df['D'].iloc[-1]
            prev_osc, curr_osc = df['OSC'].iloc[-2], df['OSC'].iloc[-1]
            curr_upper = df['Upper_Band'].iloc[-1]
            
            signals = []
            if prev_k < prev_d and curr_k > curr_d: signals.append(f"✨ KD 黃金交叉 (K={curr_k:.1f})")
            if prev_osc <= 0 and curr_osc > 0: signals.append(f"📈 MACD 柱狀體翻紅")
            if curr_close > curr_upper: signals.append(f"🔥 突破布林上軌 ({curr_upper:.1f})")
                
            if signals:
                msg = f"🎯 {name} ({ticker.replace('.TW', '')})\n🔸 最新收盤: {curr_close:.2f}\n🔸 觸發訊號:\n - " + "\n - ".join(signals)
                alerts.append(msg)
        except Exception as e:
            pass
            
    if alerts:
        send_line_message(f"🚨【狙擊手鎖定通報】\n掃描時間: {today_str}\n\n" + "\n\n".join(alerts))
        print("✅ 發現獵物！已發送 LINE 警報。")
    else:
        # 為了測試方便，如果沒有獵物，我們也發一條靜默通知，確認系統有在跑
        send_line_message(f"📡【狙擊手回報】\n掃描時間: {today_str}\n清單內無標的觸發攻擊訊號，繼續潛伏。")
        print("⏸️ 掃描完畢，已回報指揮官。")

if __name__ == "__main__":
    run_sniper_scan()
