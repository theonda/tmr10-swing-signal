"""Conservative Japanese value-growth discovery: not a buy signal."""
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
import yfinance as yf

DEFAULT_TICKERS = ["8035.T", "6098.T", "7936.T", "7011.T", "6501.T", "6504.T"]


def _number(value):
    try:
        v = float(value)
        return v if pd.notna(v) else None
    except (TypeError, ValueError):
        return None


def _ordinary_growth(financials):
    """Only use a row explicitly identified as ordinary/recurring profit.
    Pretax Income is NOT ordinary profit and must not be substituted.
    """
    if financials is None or financials.empty:
        return None
    candidates = ["Ordinary Income", "Ordinary Profit", "Recurring Profit"]
    for label in candidates:
        if label in financials.index:
            row = financials.loc[label].dropna()
            if len(row) < 2:
                return None
            row = row.sort_index(ascending=False)
            recent, prior = _number(row.iloc[0]), _number(row.iloc[1])
            if recent is None or prior is None or prior <= 0:
                return None
            return (recent / prior - 1) * 100
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def inspect(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info or {}
    # Fetch raw, unadjusted historical highs and closes on the same scale.
    history = stock.history(period="18mo", interval="1d", auto_adjust=False)
    if history.empty:
        raise ValueError("株価履歴なし")
    history = history.dropna(subset=["High", "Close"])
    local_today = datetime.now(ZoneInfo("Asia/Tokyo")).date()
    # Never label the current Japanese session as confirmed.
    history = history.loc[history.index.date < local_today]
    if len(history) < 100:
        raise ValueError("履歴不足（100営業日未満）")
    recent = history.tail(252)
    close = _number(recent["Close"].iloc[-1])
    peak = _number(recent["High"].max())
    if close is None or peak is None or peak <= 0:
        raise ValueError("価格データ不足")
    market_cap = _number(info.get("marketCap"))
    equity_ratio = None
    balance_sheet = stock.balance_sheet
    if balance_sheet is not None and not balance_sheet.empty:
        equity = None
        assets = None
        for key in ("Stockholders Equity", "Total Equity Gross Minority Interest"):
            if key in balance_sheet.index:
                equity = _number(balance_sheet.loc[key].iloc[0])
                break
        if "Total Assets" in balance_sheet.index:
            assets = _number(balance_sheet.loc["Total Assets"].iloc[0])
        if equity is not None and assets is not None and assets > 0:
            equity_ratio = 100 * equity / assets
    growth = _ordinary_growth(stock.income_stmt)
    drop = 100 * (close / peak - 1)
    # Unknown fields must never be treated as passing filters.
    passed = (market_cap is not None and market_cap >= 100_000_000_000
              and equity_ratio is not None and equity_ratio >= 40
              and growth is not None and growth >= 10
              and drop <= -15)
    missing = [key for key, val in [
        ("時価総額", market_cap), ("自己資本比率", equity_ratio),
        ("経常利益成長率", growth)] if val is None]
    return {
        "コード": ticker,
        "銘柄": info.get("shortName") or ticker,
        "確定日": str(recent.index[-1].date()),
        "時価総額(億円)": round(market_cap / 1e8, 1) if market_cap is not None else None,
        "自己資本比率(%)": round(equity_ratio, 1) if equity_ratio is not None else None,
        "経常利益増減(%)": round(growth, 1) if growth is not None else None,
        "52週高値比(%)": round(drop, 1),
        "判定": "一次条件通過・要審査" if passed else ("要データ確認" if missing else "条件外"),
        "未確認項目": "、".join(missing),
    }


def render():
    st.header("割安成長株スクリーニング")
    st.caption("中長期用・一次候補の抽出。TMR10採点・売買判断・SWING SIGNALとは独立。既存の保存データは変更しません。")
    st.info("検索対象は入力した日本株のみ。東証全銘柄の自動探索ではありません。無料の非公式データで欠損する項目は合格扱いにしません。")
    symbols = st.text_area("対象銘柄（証券コードをカンマ・改行区切りで入力）", value=", ".join(DEFAULT_TICKERS), height=75)
    st.write("一次条件：時価総額1,000億円以上／自己資本比率40%以上／経常利益の前年度比+10%以上／52週高値から15%以上下落")
    if st.button("割安成長株を確認", key="value_growth_scan"):
        raw = symbols.replace("\n", ",").replace("、", ",").split(",")
        tickers = list(dict.fromkeys((s.strip().upper() if "." in s else s.strip() + ".T") for s in raw if s.strip()))[:30]
        if not tickers:
            st.warning("証券コードを入力してください")
            return
        rows, errors = [], []
        with st.spinner("財務・株価データを確認中..."):
            for ticker in tickers:
                try:
                    rows.append(inspect(ticker))
                except Exception as exc:
                    errors.append(f"{ticker}: {exc}")
        if rows:
            frame = pd.DataFrame(rows)
            rank = {"一次条件通過・要審査": 0, "要データ確認": 1, "条件外": 2}
            frame["_priority"] = frame["判定"].map(rank)
            st.dataframe(frame.sort_values("_priority").drop(columns="_priority"), hide_index=True, use_container_width=True)
            st.caption("経常利益は税引前利益で代用しません。取得不能なら『要データ確認』です。高値比は調整前終値と高値から計算しています。")
        if errors:
            st.warning("取得できなかった銘柄：" + " / ".join(errors))
    st.warning("一次条件通過＝買いではありません。TMR10 80点以上、決算、セクター、株価の下げ止まり・反転を別途確認してください。")
