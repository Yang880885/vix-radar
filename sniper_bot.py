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

# 🔗 連結您的 Google 表單彈匣 (請將下方的網址替換為您剛剛複製的 CSV 網址)
# 注意：網址前後的雙引號 " 不要刪掉喔！
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTWbJ9b8ehZQPmL1-U-GU-kCpDbx_YpVL4-xh7-epTz3uYXhlOZlWTOyFu6PuLLM90XNQmhN8nfOMdF/pub?output=csv"

def get_watchlist_from_google():
    """起飛前自動從 Google 表單讀取最新彈匣"""
    try:
        df = pd.read_csv(SHEET_CSV_URL)
        # 假設 A 欄是代號，B 欄是名稱。去除空白與空值
        df = df.dropna(subset=[df.columns[0]]) 
        tickers = df.iloc[:, 0].astype(str).str.strip().tolist()
        names = df.iloc[:, 1].astype(str).str.strip().tolist()
        return dict(zip(tickers, names))
    except Exception as e:
        print(f"❌ 無法讀取 Google 表單，請檢查網址是否正確。錯誤原因: {e}")
        return {}

# ==========================================
# 📡 戰術運算與通訊區
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
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    rs = gain.rolling(window=14, min_periods=1).mean() / loss.rolling(window=14, min_periods=1).mean()
    df['RSI'] = 100 - (100 / (1 + rs))
    
    df['BIAS20'] = (df['Close'] - df['MA20']) / df['MA20'] * 100
    df['Vol_MA5'] = df['Volume'].rolling(window=5).mean()
    
    return df

def run_sniper_scan():
    tz = pytz.timezone('Asia/Taipei')
    today_str = datetime.now(tz).strftime('%Y-%m-%d %H:%M')
    
    # 💥 第一步：裝填子彈 (從 Google 表單下載清單)
    print("🔄 正在從 Google 雲端裝填彈匣...")
    watchlist = get_watchlist_from_google()
    
    if not watchlist:
        send_line_message(f"⚠️【狙擊手異常】\n掃描時間: {today_str}\n無法讀取 Google 表單清單或清單為空，請檢查設定。")
        return
        
    print(f"🔍 [{today_str}] 啟動終極收割掃描 (共 {len(watchlist)} 檔)...")
    alerts = []
    
    for ticker, name in watchlist.items():
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="6mo")
            if len(df) < 30: continue
                
            df = calculate_indicators(df)
            
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
            
            bullish_signals, profit_signals, bearish_signals = [], [], []
            
            # 🟢 攻擊訊號
            if prev_k < prev_d and curr_k > curr_d and curr_k < 50: bullish_signals.append(f"✨ KD 低檔黃金交叉 (K={curr_k:.1f})")
            if prev_osc <= 0 and curr_osc > 0: bullish_signals.append(f"📈 MACD 柱狀體翻紅")
            if curr_close > curr_upper: bullish_signals.append(f"🔥 強勢突破布林上軌")
                
            # 💰 極限逃頂
            if curr_rsi > 80: profit_signals.append(f"🔥 RSI 極度超買過熱 (RSI={curr_rsi:.1f})")
            if prev_k >= 85 and curr_k < 85: profit_signals.append(f"🔥 KD 高檔極限反轉 (K自 85 跌落)")
            if curr_vol > (curr_vol_ma5 * 2) and curr_close <= curr_open: profit_signals.append(f"💣 爆量滯漲 (高檔爆量收黑)")
            if curr_bias20 > 10.0: profit_signals.append(f"🚀 正乖離過大 ({curr_bias20:.1f}%)")

            # 🔴 波段撤退
            if prev_close >= curr_ma20 and curr_close < curr_ma20: bearish_signals.append(f"📉 跌破生命月線 (20MA: {curr_ma20:.1f})")
                
            if bullish_signals or profit_signals or bearish_signals:
                msg = f"🎯 {name} ({ticker.replace('.TW', '')})\n🔸 最新收盤: {curr_close:.2f}\n"
                if bullish_signals: msg += "🟢 【攻擊鎖定】\n - " + "\n - ".join(bullish_signals) + "\n"
                if profit_signals: msg += "💰 【逃頂警報】\n - " + "\n - ".join(profit_signals) + "\n"
                if bearish_signals: msg += "🔴 【撤退警報】\n - " + "\n - ".join(bearish_signals) + "\n"
                alerts.append(msg.strip())
                
        except Exception as e:
            pass
            
    if alerts:
        send_line_message(f"🚨【狙擊手戰況通報】\n掃描時間: {today_str}\n\n" + "\n\n".join(alerts))
    else:
        send_line_message(f"📡【狙擊手回報】\n掃描時間: {today_str}\n清單內 {len(watchlist)} 檔標的無觸發訊號，繼續潛伏。")

if __name__ == "__main__":
    run_sniper_scan()
