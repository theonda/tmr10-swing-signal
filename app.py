import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from scanner import WATCHLIST, download_daily, scan

st.set_page_config(page_title="TMR10 Swing Signal", page_icon="📈", layout="wide")
st.title("TMR10 | SWING SIGNAL")
st.caption("CSV不要・日足ベースの検証ツール。株価取得にはインターネットが必要。売買の推奨や自動注文は行いません。")
st.info("重要：TMR10スコア・セクター強度・決算チェックは未接続。チャート判定のみでは最終的な買い条件を満たしません。")
selected = st.multiselect("監視銘柄", list(WATCHLIST), default=list(WATCHLIST))
if st.button("最新の確定日足を取得・判定", type="primary"):
    out, details, failures = [], {}, []
    with st.spinner("株価データを照会中..."):
        for ticker in selected:
            try:
                df = download_daily(ticker)
                result = scan(ticker, WATCHLIST[ticker], df)
                out.append(result.__dict__)
                details[ticker] = df
            except Exception as e:
                failures.append(f"{ticker}: {e}")
    if out:
        st.session_state["results"] = pd.DataFrame(out)
        st.session_state["details"] = details
    if failures:
        st.warning("取得失敗・判定除外：" + " / ".join(failures))
if "results" in st.session_state:
    results = st.session_state["results"]
    active = results[results.signal != "確認待ち"]
    st.metric("上昇シグナル成立", f"{len(active)} / {len(results)}銘柄")
    st.dataframe(results[["name", "date", "close", "signal", "trigger", "volume_ratio", "stop", "description"]].rename(columns={
        "name":"銘柄", "date":"確定日", "close":"終値", "signal":"チャート判定", "trigger":"抵抗線/基準", "volume_ratio":"出来高倍率", "stop":"参考損切り", "description":"根拠"}), hide_index=True, use_container_width=True)
    ticker = st.selectbox("チャート詳細", list(st.session_state["details"]))
    df = st.session_state["details"][ticker].tail(70)
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df.Open, high=df.High, low=df.Low, close=df.Close, name="日足")])
    fig.add_trace(go.Scatter(x=df.index, y=df.Close.rolling(20).mean(), name="20日平均", line=dict(width=1)))
    fig.add_trace(go.Scatter(x=df.index, y=df.Close.rolling(50).mean(), name="50日平均", line=dict(width=1)))
    fig.update_layout(height=480, xaxis_rangeslider_visible=False, margin=dict(l=10,r=10,t=20,b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("三角保合いは回帰直線による簡易的な形状判定。裁量で引く抵抗線と異なる場合があります。参考損切り水準は約定価格を保証しません。")
st.divider()
st.write("**判定の基本条件**：三角保合い＋終値で抵抗線0.3%以上突破＋出来高20日平均比1.5倍以上＋終値 > 20日線 > 50日線。別途TMR10採点を確認してください。")
