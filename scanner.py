"""Daily-bar swing trading research scanner. Not an execution system."""
from dataclasses import dataclass
from datetime import datetime
import numpy as np
import pandas as pd
import yfinance as yf

WATCHLIST = {
    "8035.T": "東京エレクトロン", "6098.T": "リクルート", "7936.T": "アシックス",
    "7011.T": "三菱重工", "6501.T": "日立", "6504.T": "富士電機",
    "META": "Meta", "NVDA": "NVIDIA", "QQQ": "NASDAQ100 ETF",
}

@dataclass
class Result:
    ticker: str
    name: str
    date: str
    close: float
    volume_ratio: float
    ma20: float
    ma50: float
    signal: str
    trigger: float | None
    stop: float | None
    description: str
    source: str


def download_daily(ticker: str) -> pd.DataFrame:
    """Fetch *completed* daily bars; exclude the local market's current date if session may be live."""
    df = yf.download(ticker, period="9mo", interval="1d", auto_adjust=True, progress=False, threads=False)
    if df.empty:
        raise ValueError("株価データを取得できませんでした")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    cols = ["Open", "High", "Low", "Close", "Volume"]
    df = df[cols].dropna().copy()
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    # Conservative policy: use yesterday or earlier to avoid treating a still-forming bar as settled.
    import zoneinfo
    local_tz = zoneinfo.ZoneInfo("Asia/Tokyo" if ticker.endswith(".T") else "America/New_York")
    today = pd.Timestamp(datetime.now(local_tz).date())
    df = df.loc[df.index < today]
    if len(df) < 65:
        raise ValueError("判定に必要な日足データが不足しています（65本以上必要）")
    return df


def scan(ticker: str, name: str, df: pd.DataFrame) -> Result:
    """Simple, reproducible heuristic. Never claims a signal predicts returns."""
    x = df.copy().sort_index()
    last = x.iloc[-1]
    history = x.iloc[:-1]
    close = float(last.Close)
    ma20 = float(history.Close.tail(20).mean())
    ma50 = float(history.Close.tail(50).mean())
    avgvol = float(history.Volume.tail(20).mean())
    vr = float(last.Volume / avgvol) if avgvol > 0 else 0.0
    # Prior twenty-session resistance (today excluded)
    prior_high = float(history.High.tail(20).max())
    prior_low = float(history.Low.tail(10).min())
    trend = close > ma20 > ma50
    volume_ok = vr >= 1.5
    breakout = close >= prior_high * 1.003 and volume_ok and trend

    # Triangle approximation: linear slopes on recent daily highs/lows with convergence.
    w = history.tail(20)
    t = np.arange(len(w))
    hcoef = np.polyfit(t, w.High.astype(float).to_numpy(), 1)
    lcoef = np.polyfit(t, w.Low.astype(float).to_numpy(), 1)
    resistance = float(np.polyval(hcoef, len(w)))
    support_start = float(np.polyval(lcoef, 0))
    resistance_start = float(np.polyval(hcoef, 0))
    support_end = float(np.polyval(lcoef, len(w)))
    converging = (hcoef[0] < 0 and lcoef[0] > 0 and
                   resistance_start > support_start and
                   resistance > support_end and
                   (resistance - support_end) < (resistance_start - support_start) * 0.8)
    triangle = bool(converging and close >= resistance * 1.003 and
                    float(history.Close.iloc[-1]) <= float(np.polyval(hcoef, len(w)-1)) * 1.003 and
                    volume_ok and trend)
    # Other setup: bounce back above short MA after touching it intraday (historical context).
    pullback = bool(trend and float(last.Low) <= ma20 * 1.015 and
                    close > ma20 * 1.01 and close > float(last.Open) and vr >= 1.2)

    if triangle:
        signal, trigger, description = "三角保合い上抜け", resistance, "収束形状の簡易判定＋上値抵抗線0.3%以上の終値突破＋出来高1.5倍以上"
    elif breakout:
        signal, trigger, description = "20日高値上抜け", prior_high, "直近20日高値0.3%以上の終値突破＋出来高1.5倍以上"
    elif pullback:
        signal, trigger, description = "20日線で反発", ma20, "上昇基調で20日線付近に接近し陽線反発＋出来高1.2倍以上"
    else:
        signal, trigger, description = "確認待ち", prior_high, "確定足の上抜け・出来高・トレンド条件が未成立"
    # An indicative stop, not a guaranteed fill or a fixed-distance trading instruction.
    stop = min(prior_low, ma20 * 0.985) if signal != "確認待ち" else None
    return Result(ticker, name, str(x.index[-1].date()), close, round(vr, 2), round(ma20, 2),
                  round(ma50, 2), signal, round(trigger, 2), round(stop, 2) if stop else None,
                  description, f"https://finance.yahoo.com/quote/{ticker}/history/")
