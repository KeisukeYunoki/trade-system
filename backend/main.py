from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import pandas_ta as ta
import uvicorn
from typing import Optional
from pydantic import BaseModel

app = FastAPI(title="トレード支援API", version="1.0.0")

# CORS設定（Androidアプリからのアクセスを許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class IndicatorsResponse(BaseModel):
    # 日経平均
    nikkei_close: Optional[float]
    nikkei_5ma: Optional[float]
    nikkei_rsi9: Optional[float]
    nikkei_bb_minus2sigma: Optional[float]
    nikkei_bb_minus3sigma: Optional[float]

    # 米国VIX
    vix_close: Optional[float]

    # プレースホルダー（後日実装）
    nikkei_vi: Optional[float]        # 日経VI（スクレイピング予定）
    nikkei_futures_night: Optional[float]  # 日経225先物ナイトセッション（スクレイピング予定）


def safe_float(value) -> Optional[float]:
    """NaN や None を安全に float または None に変換する"""
    try:
        import math
        if value is None:
            return None
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, 2)
    except (TypeError, ValueError):
        return None


@app.get("/api/indicators", response_model=IndicatorsResponse)
def get_indicators():
    """
    日経平均・VIXのテクニカル指標を返すエンドポイント。
    - 日経平均終値、5MA、9日RSI、ボリンジャーバンド(-2σ/-3σ)
    - VIX終値
    - 日経VI・先物ナイトセッションはプレースホルダー（null）
    """

    # ── 日経平均データ取得 ──────────────────────────────
    try:
        nikkei = yf.Ticker("^N225")
        nikkei_df = nikkei.history(period="3mo")  # 指標計算のため多めに取得

        if nikkei_df.empty:
            raise HTTPException(status_code=502, detail="日経平均のデータ取得に失敗しました")

        nikkei_close_latest = safe_float(nikkei_df["Close"].iloc[-1])

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"日経平均データ取得エラー: {str(e)}")

    # ── 日経平均テクニカル指標計算 ────────────────────────
    try:
        close = nikkei_df["Close"]

        # 5日移動平均線
        sma5 = ta.sma(close, length=5)
        nikkei_5ma = safe_float(sma5.iloc[-1]) if sma5 is not None else None

        # 9日RSI
        rsi9 = ta.rsi(close, length=9)
        nikkei_rsi9 = safe_float(rsi9.iloc[-1]) if rsi9 is not None else None

       # ボリンジャーバンド（-2σ）pandas_taで計算
        bb2 = ta.bbands(close, length=20, std=2)
        nikkei_bb_minus2sigma = None
        if bb2 is not None and not bb2.empty:
            lower2_col = [c for c in bb2.columns if c.startswith("BBL_")]
            if lower2_col:
                nikkei_bb_minus2sigma = safe_float(bb2[lower2_col[0]].iloc[-1])

        # ボリンジャーバンド（-3σ）手動計算（pandas_taのstdバグ回避）
        nikkei_bb_minus3sigma = None
        try:
            sma20 = close.rolling(window=20).mean()
            std20 = close.rolling(window=20).std()
            bb_minus3 = sma20 - 3 * std20
            nikkei_bb_minus3sigma = safe_float(bb_minus3.iloc[-1])
        except Exception:
            nikkei_bb_minus3sigma = None

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"テクニカル指標計算エラー: {str(e)}")

    # ── VIXデータ取得 ──────────────────────────────────
    try:
        vix = yf.Ticker("^VIX")
        vix_df = vix.history(period="1mo")

        if vix_df.empty:
            raise HTTPException(status_code=502, detail="VIXのデータ取得に失敗しました")

        vix_close_latest = safe_float(vix_df["Close"].iloc[-1])

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"VIXデータ取得エラー: {str(e)}")

    # ── レスポンス返却 ─────────────────────────────────
    return IndicatorsResponse(
        nikkei_close=nikkei_close_latest,
        nikkei_5ma=nikkei_5ma,
        nikkei_rsi9=nikkei_rsi9,
        nikkei_bb_minus2sigma=nikkei_bb_minus2sigma,
        nikkei_bb_minus3sigma=nikkei_bb_minus3sigma,
        vix_close=vix_close_latest,
        nikkei_vi=None,            # プレースホルダー（後日スクレイピングで実装）
        nikkei_futures_night=None, # プレースホルダー（後日スクレイピングで実装）
    )


@app.get("/")
def root():
    return {"message": "トレード支援API is running 🚀", "docs": "/docs"}
@app.get("/debug/bbands")
def debug_bbands():
    nikkei = yf.Ticker("^N225")
    df = nikkei.history(period="3mo")
    close = df["Close"]
    bb3 = ta.bbands(close, length=20, std=3)
    return {
        "columns": list(bb3.columns),
        "sample": bb3.iloc[-1].to_dict()
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)