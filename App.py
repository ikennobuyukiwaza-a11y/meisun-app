import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="名選 - 米株選定アプリ", layout="wide")
st.title("🏛️ 名選 - 米国株 統合選定・分析アプリ")

# サイドメニュー: 選定モード選択
st.sidebar.header("🔍 選定設定")
mode = st.sidebar.radio("モード選択", ["固定ルールで自動選定", "カスタム条件選定"])

# 監視対象銘柄↑ 1
default_tickers = "NVDA, AAPL, MSFT, GOOGL, AMZN, META, AVGO, AMD, TSLA"
target_input = st.sidebar.text_area("分析対象（カンマ区切り）", default_tickers)
target_tickers = [t.strip() for t in target_input.split(",") if t.strip()]

# カスタム条件の設定
if mode == "カスタム条件選定":
    st.sidebar.subheader("業績条件")
    min_rev_growth = st.sidebar.slider("最低売上成長率 (%)", 0, 50, 10)
    st.sidebar.subheader("チャート条件")
    check_trend = st.sidebar.checkbox("200日移動平均線の上にあること", value=True)

if st.sidebar.button("選定実行"):
    selected_list = []
    
    with st.spinner("過去数年の業績とチャートデータを解析中..."):
        for symbol in target_tickers:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="1y")
                financials = ticker.financials
                
                if hist.empty or financials.empty:
                    continue
                
                latest_price = hist['Close'].iloc[-1]
                sma200 = hist['Close'].rolling(200).mean().iloc[-1]
                
                if 'Total Revenue' in financials.index:
                    rev_series = financials.loc['Total Revenue'].dropna()
                    latest_rev = rev_series.iloc[0]
                    prev_rev = rev_series.iloc[1] if len(rev_series) > 1 else latest_rev
                    rev_growth = ((latest_rev - prev_rev) / prev_rev) * 100
                else:
                    rev_growth = 0
                
                is_selected = False
                if mode == "固定ルールで自動選定":
                    if rev_growth >= 10 and latest_price > sma200:
                        is_selected = True
                else:
                    trend_ok = (latest_price > sma200) if check_trend else True
                    if rev_growth >= min_rev_growth and trend_ok:
                        is_selected = True
                
                if is_selected:
                    selected_list.append({
                        "Ticker": symbol,
                        "現在値 ($)": round(latest_price, 2),
                        "直近売上成長率 (%)": round(rev_growth, 2)
                    })
            except Exception as e:
                pass
                
    st.subheader(f"【選定結果】({len(selected_list)} 銘柄が見つかりました)")
    if selected_list:
        df_res = pd.DataFrame(selected_list)
        st.dataframe(df_res)
    else:
        st.info("条件に該当する銘柄はありませんでした。")

st.markdown("---")

st.subheader("📊 銘柄詳細確認（過去数年の業績 & チャート）")
selected_symbol = st.selectbox("詳細を確認したい銘柄を選択", target_tickers)

if selected_symbol:
    t_data = yf.Ticker(selected_symbol)
    
    st.write("▼ **過去数年の業績推移（売上高 & 純利益）**")
    fin = t_data.financials
    if not fin.empty and 'Total Revenue' in fin.index:
        perf_df = pd.DataFrame()
        perf_df['売上高'] = fin.loc['Total Revenue']
        if 'Net Income' in fin.index:
            perf_df['純利益'] = fin.loc['Net Income']
            
        perf_df.index = pd.to_datetime(perf_df.index).year
        perf_df = perf_df.sort_index()
        st.bar_chart(perf_df / 1e6)
        st.dataframe(perf_df.T)
    else:
        st.warning("業績データが取得できませんでした。")
        
    st.write("▼ **過去1年の株価チャート（50日・200日移動平均線）**")
    chart_df = t_data.history(period="1y")
    if not chart_df.empty:
        chart_df['50日線'] = chart_df['Close'].rolling(50).mean()
        chart_df['200日線'] = chart_df['Close'].rolling(200).mean()
        st.line_chart(chart_df[['Close', '50日線', '200日線']])
