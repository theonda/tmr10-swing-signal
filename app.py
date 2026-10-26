import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from scanner import WATCHLIST, download_daily, scan

st.set_page_config(page_title="TMR10 Swing Signal", page_icon="📈", layout="wide")
st.title("TMR10 | SWING SIGNAL")
st.caption("CSV不要・確定日足による分析ツール。売買の保証や自動注文は行いません。")
st.info("TMR10スコア・セクター強度・決算チェックは未接続です。チャート判定だけで買い条件は満たしません。")
selected = st.multiselect("監視銘柄", list(WATCHLIST), default=list(WATCHLIST))

if st.button("最新の確定日足を取得・判定", type="primary"):
    out, details, failures = [], {}, []
    with st.spinner("株価データを照会中..."):
        for ticker in selected:
            try:
                df = download_daily(ticker)
                result = scan(ticker, WATCHLIST[ticker], df)
                out.append(vars(result))
                details[ticker] = df
            except Exception as exc:
                failures.append(f"{ticker}: {exc}")
    if out:
        st.session_state["results"] = pd.DataFrame(out)
        st.session_state["details"] = details
    else:
        st.session_state.pop("results", None)
        st.session_state.pop("details", None)
    if failures:
        st.warning("取得失敗・判定除外：" + " / ".join(failures))

if "results" in st.session_state:
    results = st.session_state["results"].copy()
    # Streamlit sessions can preserve an older DataFrame across a GitHub deployment.
    # Do not assume that its schema already contains Ver.3 fields.
    if "category" not in results.columns or "distance_pct" not in results.columns:
        st.info("更新前の分析結果が残っているため、新しい3段階判定用に再取得してください。")
        st.session_state.pop("results", None)
        st.session_state.pop("details", None)
    else:
        categories = ["買い候補", "上抜け接近", "監視継続"]
        counts = results["category"].value_counts()
        c1, c2, c3 = st.columns(3)
        c1.metric("🟢 買い候補", f"{int(counts.get(categories[0], 0))} / {len(results)}")
        c2.metric("🟠 上抜け接近（2%以内）", f"{int(counts.get(categories[1], 0))} / {len(results)}")
        c3.metric("⚪ 監視継続", f"{int(counts.get(categories[2], 0))} / {len(results)}")
        st.caption("上抜け接近：抵抗線まで0〜2%で、終値＞20日線＞50日線。未突破なので買いシグナルではありません。")
        ordered = results.assign(_order=results["category"].map({"買い候補":0, "上抜け接近":1, "監視継続":2})).sort_values(["_order", "distance_pct"], na_position="last")
        wanted = ["name", "date", "close", "category", "distance_pct", "signal", "trigger", "volume_ratio", "stop", "description"]
        available = [c for c in wanted if c in ordered.columns]
        st.dataframe(ordered[available].rename(columns={
            "name":"銘柄", "date":"確定日", "close":"終値", "category":"3段階判定",
            "distance_pct":"抵抗線まで(%)", "signal":"検出パターン", "trigger":"抵抗線/基準",
            "volume_ratio":"出来高倍率", "stop":"参考損切り", "description":"根拠"}), hide_index=True, use_container_width=True)
        details = st.session_state.get("details", {})
        if details:
            ticker = st.selectbox("チャート詳細", list(details))
            df = details[ticker].tail(70)
            fig = go.Figure(data=[go.Candlestick(x=df.index, open=df.Open, high=df.High, low=df.Low, close=df.Close, name="日足")])
            fig.add_trace(go.Scatter(x=df.index, y=df.Close.rolling(20).mean(), name="20日平均", line=dict(width=1)))
            fig.add_trace(go.Scatter(x=df.index, y=df.Close.rolling(50).mean(), name="50日平均", line=dict(width=1)))
            fig.update_layout(height=480, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)
        st.caption("三角保合いは簡易アルゴリズムで判定します。価格データの欠損や遅延に注意してください。")

st.divider()
st.write("**買い候補の基本条件**：三角保合いの終値上抜け＋出来高20日平均比1.5倍以上＋上昇トレンドなど。最終判断にはTMR10も確認してください。")
st.caption("これらのシグナルは将来の株価上昇を保証するものではありません。")


# Standalone discovery module: preserves the existing SWING SIGNAL screen and state.
with st.expander('🔎 割安成長株スクリーニング（中長期用）', expanded=False):
    from value_growth_screener import render as render_value_growth
    render_value_growth()
