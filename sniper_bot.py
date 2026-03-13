import yfinance as yf
import pandas as pd
import requests
import json
from datetime import datetime
import pytz

# ==========================================
# ⚙️ 指揮官設定區
# ==========================================
# 1. 您的 LINE 金鑰 (請填入您之前的 Token 與 User ID)
LINE_TOKEN = "請填入您的_LINE_TOKEN"
LINE_USER_ID = "請填入您的_LINE_USER_ID"

# 2. 狙擊監控清單 (可隨時自由新增，記得加 .TW)
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
# 📡 系統運作區 (請勿更動)
# ==========================================
def send_line_message(message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"}
    payload = {"to": LINE_USER_ID, "messages": [{"type": "text", "text": message}]}
    try:
        requests.post(url, headers=headers, data=json.dumps(payload))
    except Exception as e:
        print(f"LINE 發送失敗: {e}")

def calculate_indicators(df):
    """計算 KD, MACD, 布林通道"""
    # 1. 算 KD (9天 RSV, 1/3 平滑)
    low_min = df['Low'].rolling(window=9, min_periods=1).min()
    high_max = df['High'].rolling(window=9, min_periods=1).max()
    df['RSV'] = 100 * (df['Close'] - low_min) / (high_max - low_min)
    df['K'] = df['RSV'].ewm(com=2, adjust=False).mean() # com=2 等同於 1/3 的權重
    df['D'] = df['K'].ewm(com=2, adjust=False).mean()
    
    # 2. 算 MACD (12, 26, 9)
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['DIF'] = ema12 - ema26
    df['MACD'] = df['DIF'].ewm(span=9, adjust=False).mean()
    df['OSC'] = df['DIF'] - df['MACD'] # 柱狀體
    
    # 3. 算布林通道 (20MA, 2倍標準差)
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
            # 抓取近半年資料以確保均線計算準確
            stock = yf.Ticker(ticker)
            df = stock.history(period="6mo")
            
            if len(df) < 30:
                continue
                
            df = calculate_indicators(df)
            
            # 取得「昨天」與「今天」的數值來判斷交叉
            curr_close = df['Close'].iloc[-1]
            
            prev_k, curr_k = df['K'].iloc[-2], df['K'].iloc[-1]
            prev_d, curr_d = df['D'].iloc[-2], df['D'].iloc[-1]
            
            prev_osc, curr_osc = df['OSC'].iloc[-2], df['OSC'].iloc[-1]
            
            curr_upper = df['Upper_Band'].iloc[-1]
            
            signals = []
            
            # 💡 觸發條件 1：KD 黃金交叉 (昨天 K<D，今天 K>D，且在低檔 < 50 更有威力)
            if prev_k < prev_d and curr_k > curr_d:
                signals.append(f"✨ KD 黃金交叉 (K={curr_k:.1f})")
                
            # 💡 觸發條件 2：MACD 翻多 (柱狀體由綠轉紅)
            if prev_osc <= 0 and curr_osc > 0:
                signals.append(f"📈 MACD 柱狀體翻紅")
                
            # 💡 觸發條件 3：突破布林上軌 (強勢噴出)
            if curr_close > curr_upper:
                signals.append(f"🔥 股價突破布林上軌 ({curr_upper:.1f})")
                
            # 如果有任何訊號觸發，加入警報清單
            if signals:
                msg = f"🎯 {name} ({ticker.replace('.TW', '')})\n"
                msg += f"🔸 最新收盤: {curr_close:.2f}\n"
                msg += f"🔸 觸發訊號:\n - " + "\n - ".join(signals)
                alerts.append(msg)
                
        except Exception as e:
            print(f"❌ 無法掃描 {ticker}: {e}")
            
    # 發送 LINE 總結警報
    if alerts:
        final_msg = "\n\n".join(alerts)
        send_line_message(f"🚨【狙擊手鎖定通報】\n掃描時間: {today_str}\n\n{final_msg}")
        print("✅ 發現獵物！已發送 LINE 警報。")
    else:
        print("⏸️ 掃描完畢，今日無獵物進入射程。")

if __name__ == "__main__":
    run_sniper_scan()