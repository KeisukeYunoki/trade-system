from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import pandas_ta as ta
import uvicorn
import requests
from bs4 import BeautifulSoup

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/indicators")
def get_indicators():
    try:
        # 1. 日経平均の取得と計算
        nikkei = yf.Ticker("^N225")
        df_n225 = nikkei.history(period="3mo")
        if df_n225.empty:
            raise ValueError("日経平均データ取得失敗")

        df_n225.ta.rsi(length=9, append=True)
        df_n225['5MA'] = df_n225['Close'].rolling(window=5).mean()
        df_n225['20MA'] = df_n225['Close'].rolling(window=20).mean()
        df_n225['20STD'] = df_n225['Close'].rolling(window=20).std()
        df_n225['BB_minus_2sigma'] = df_n225['20MA'] - (df_n225['20STD'] * 2)
        df_n225['BB_minus_3sigma'] = df_n225['20MA'] - (df_n225['20STD'] * 3)

        df_n225_clean = df_n225.dropna()
        latest_n225 = df_n225_clean.iloc[-1]

        # 2. 米国VIXの取得
        vix = yf.Ticker("^VIX")
        df_vix = vix.history(period="5d")
        latest_vix_close = df_vix['Close'].iloc[-1] if not df_vix.empty else None

        # 3. CME日経225先物（ナイトセッション代用）の取得
        niy = yf.Ticker("NIY=F")
        df_niy = niy.history(period="5d")
        nikkei_futures_night = df_niy['Close'].iloc[-1] if not df_niy.empty else None

       # 4. 日経VIの取得（investing.comからスクレイピング）
        nikkei_vi_val = None
        try:
            url = "https://jp.investing.com/indices/nikkei-volatility"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            }
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                vi_element = soup.select_one('div.text-5xl\\/9')
                if vi_element:
                    nikkei_vi_val = float(vi_element.text.strip().replace(',', ''))
        except Exception as e:
            print(f"日経VI取得エラー: {e}")

        # 5. Androidアプリの「受け皿」に合わせたフラットなJSONで返す
        return {
            "nikkei_close": round(float(latest_n225['Close']), 2),
            "nikkei_5ma": round(float(latest_n225['5MA']), 2),
            "nikkei_rsi9": round(float(latest_n225['RSI_9']), 2),
            "nikkei_bb_minus2sigma": round(float(latest_n225['BB_minus_2sigma']), 2),
            "nikkei_bb_minus3sigma": round(float(latest_n225['BB_minus_3sigma']), 2),
            "vix_close": round(float(latest_vix_close), 2) if latest_vix_close else None,
            "nikkei_vi": nikkei_vi_val,
            "nikkei_futures_night": round(float(nikkei_futures_night), 2) if nikkei_futures_night else None
        }

    except Exception as e:
        print(f"全体エラー発生: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)