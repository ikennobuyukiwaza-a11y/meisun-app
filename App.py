import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# 1. ページ構成とアイコンの設定
st.set_page_config(
    page_title="名選 - 米国株統合選定・分析アプリ",
    page_icon="🐂",
    layout="wide"
)

st.title("🏛️ 名選：S&P 500 全銘柄 統合スクリーニング＆分析")
st.markdown("S&P 500全銘柄を高速一括取得し、各種ランキング・スクリーニング・チャートを快適に操作できます。")

# S&P 500の全ティッカーをWikipediaから自動取得する関数
@st.cache_data(ttl=86400)
def get_sp500_tickers():
    try:
        table = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
        df = table[0]
        tickers = df['Symbol'].tolist()
        tickers = [t.replace('.', '-') for t in tickers]
        return tickers
    except Exception:
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "JNJ", "V", 
                "JPM", "WMT", "PG", "MA", "UNH", "HD", "DIS", "BAC", "XOM", "CVX",
                "NFLX", "AMD", "INTC", "QCOM", "IBM", "ORCL", "CRM", "ADBE", "NKE", "MCD"]

ALL_SP500_TICKERS = get_sp500_tickers()

st.sidebar.header("🎯 検索対象の切替")
fetch_mode = st.sidebar.radio(
    "モード選択",
    ["S&P 500 全銘柄（約500社）", "軽量モード（主要30銘柄のみ）"],
    index=0
)

if "全銘柄" in fetch_mode:
    target_tickers = ALL_SP500_TICKERS
    st.sidebar.info(f"S&P 500全 **{len(target_tickers)}銘柄** を対象に実行中。")
else:
    target_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "JNJ", "V", 
                      "JPM", "WMT", "PG", "MA", "UNH", "HD", "DIS", "BAC", "XOM", "CVX",
                      "NFLX", "AMD", "INTC", "QCOM", "IBM", "ORCL", "CRM", "ADBE", "NKE", "MCD"]
    st.sidebar.warning("軽量モード（主要30銘柄）で実行中。")

@st.cache_data(ttl=86400)
def fetch_stock_data(tickers_tuple):
    end_date = datetime.today()
    date_1y = end_date - timedelta(days=365)
    
    # yfinanceのマルチダウンロードで一括取得（フリーズ防止・高速化）
    data_load_state = st.text("株価データを一括ダウンロード中...")
    try:
        df_hist = yf.download(list(tickers_tuple), start=date_1y, end=end_date, group_by='ticker', threads=True, progress=False)
    except Exception:
        df_hist = pd.DataFrame()
    data_load_state.empty()
    
    data = []
    for ticker in tickers_tuple:
        try:
            # 個別データの切り出し
            if len(tickers_tuple) == 1:
                hist = df_hist
            else:
                if ticker in df_hist.columns.levels[0]:
                    hist = df_hist[ticker].dropna(how="all")
                else:
                    continue
            
            if hist.empty or len(hist) < 5:
                continue
                
            current_price = hist['Close'].iloc[-1]
            high_1y = hist['High'].max()
            low_1y = hist['Low'].min()
            
            # 暴落率・暴騰率
            drop_from_high = ((current_price - high_1y) / high_1y) * 100 if high_1y > 0 else 0.0
            surge_from_low = ((current_price - low_1y) / low_1y) * 100 if low_1y > 0 else 0.0
            
            # 1ヶ月騰落率
            date_1m = end_date - timedelta(days=30)
            sub_hist_1m = hist.loc[hist.index >= pd.Timestamp(date_1m, tz=hist.index.tz) if hist.index.tz else pd.Timestamp(date_1m)]
            return_1m = ((current_price - sub_hist_1m['Close'].iloc[0]) / sub_hist_1m['Close'].iloc[0]) * 100 if not sub_hist_1m.empty else 0.0

            # 簡易ファンダメンタルズ（info取得時のタイムアウトを防ぐため安全に取得）
            stock = yf.Ticker(ticker)
            info = stock.info
            
            total_revenue = info.get("totalRevenue", 0)
            net_income = info.get("netIncomeToCommon", 0)
            profit_margin = (net_income / total_revenue) * 100 if total_revenue and total_revenue > 0 else None
            
            data.append({
                "Ticker": ticker,
                "社名": info.get("shortName", ticker),
                "現在株価 ($)": current_price,
                "過去1年最高値 ($)": high_1y,
                "過去1年最安値 ($)": low_1y,
                "暴落率(最高値比) (%)": drop_from_high,
                "暴騰率(最安値比) (%)": surge_from_low,
                "時価総額 ($)": info.get("marketCap", 0),
                "売上高 ($)": total_revenue,
                "純利益 ($)": net_income,
                "売上上昇率 (%)": info.get("revenueGrowth", 0) * 100 if info.get("revenueGrowth") else None,
                "利益率 (%)": profit_margin,
                "PER": info.get("trailingPE", None),
                "予想PER": info.get("forwardPE", None),
                "PBR": info.get("priceToBook", None),
                "ROE (%)": info.get("returnOnEquity", 0) * 100 if info.get("returnOnEquity") else None,
                "配当利回り (%)": info.get("dividendYield", 0) * 100 if info.get("dividendYield") else 0,
                "1ヶ月騰落率 (%)": return_1m
            })
        except Exception:
            continue
            
    return pd.DataFrame(data)

with st.spinner(f"対象銘柄（{len(target_tickers)}社）のデータを解析中..."):
    df = fetch_stock_data(tuple(target_tickers))

if df.empty:
    st.error("データを取得できませんでした。「軽量モード」に切り替えてお試しください。")
else:
    all_tickers_list = sorted(df["Ticker"].unique().tolist())

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 総合ランキング", 
        "🔍 複合スクリーニング", 
        "🔎 個別銘柄チェッカー", 
        "📈 個別チャート＆出来高"
    ])
    
    with tab1:
        st.subheader("指標別ランキング一覧")
        sort_metric = st.selectbox(
            "並び替えの基準を選択",
            ["暴落率(最高値比) (%)", "暴騰率(最安値比) (%)", "1ヶ月騰落率 (%)", "売上上昇率 (%)", "利益率 (%)", "時価総額 ($)", "予想PER", "ROE (%)"],
            key="sort1"
        )
        
        ascending = True if sort_metric in ["予想PER", "PBR", "暴落率(最高値比) (%)"] else False
        df_sorted = df.sort_values(by=sort_metric, ascending=ascending)
        
        st.dataframe(
            df_sorted.style.format({
                "現在株価 ($)": "${:,.2f}",
                "過去1年最高値 ($)": "${:,.2f}",
                "過去1年最安値 ($)": "${:,.2f}",
                "暴落率(最高値比) (%)": "{:+.2f}%",
                "暴騰率(最安値比) (%)": "{:+.2f}%",
                "時価総額 ($)": "${:,.0f}",
                "売上高 ($)": "${:,.0f}",
                "純利益 ($)": "${:,.0f}",
                "売上上昇率 (%)": "{:+.2f}%",
                "利益率 (%)": "{:.2f}%",
                "PER": "{:.2f}",
                "予想PER": "{:.2f}",
                "PBR": "{:.2f}",
                "ROE (%)": "{:.2f}%",
                "配当利回り (%)": "{:.2f}%",
                "1ヶ月騰落率 (%)": "{:+.2f}%"
            }),
            use_container_width=True
        )

    with tab2:
        st.subheader("複合条件による銘柄スクリーニング")
        col1, col2 = st.columns(2)
        
        with col1:
            use_rev = st.checkbox("売上上昇率の条件を有効にする", value=True, key="c_rev")
            min_rev_growth = st.slider("売上上昇率の下限（前年比 %以上）", -50.0, 100.0, 0.0, 1.0, key="s_rev")
            
            use_margin = st.checkbox("利益率の条件を有効にする", value=True, key="c_margin")
            min_profit_margin = st.slider("利益率の下限（%以上）", -20.0, 80.0, 5.0, 1.0, key="s_margin")
            
            use_pe = st.checkbox("予想PERの条件を有効にする", value=True, key="c_pe")
            max_forward_pe = st.slider("予想PERの上限（倍以下）", 5.0, 300.0, 50.0, 5.0, key="s_pe")
            
            use_pbr = st.checkbox("PBRの条件を有効にする", value=True, key="c_pbr")
            max_pbr = st.slider("PBRの上限（倍以下）", 0.5, 100.0, 20.0, 1.0, key="s_pbr")

        with col2:
            use_roe = st.checkbox("ROEの条件を有効にする", value=True, key="c_roe")
            min_roe = st.slider("ROEの下限（%以上）", -10.0, 100.0, 10.0, 1.0, key="s_roe")
            
            use_drop = st.checkbox("暴落率の条件を有効にする", value=False, key="c_drop")
            max_drop = st.slider("暴落率の上限（最高値比 %以下）", -90.0, 0.0, -20.0, 5.0, key="s_drop")
            
            use_surge = st.checkbox("暴騰率の条件を有効にする", value=False, key="c_surge")
            min_surge = st.slider("暴騰率の下限（最安値比 %以上）", 0.0, 300.0, 50.0, 10.0, key="s_surge")

        cond = pd.Series([True] * len(df), index=df.index)
        if use_rev:
            cond &= (df["売上上昇率 (%)"].fillna(-999) >= min_rev_growth)
        if use_margin:
            cond &= (df["利益率 (%)"].fillna(-999) >= min_profit_margin)
        if use_pe:
            cond &= (df["予想PER"].fillna(999) <= max_forward_pe)
        if use_pbr:
            cond &= (df["PBR"].fillna(999) <= max_pbr)
        if use_roe:
            cond &= (df["ROE (%)"].fillna(0) >= min_roe)
        if use_drop:
            cond &= (df["暴落率(最高値比) (%)"] <= max_drop)
        if use_surge:
            cond &= (df["暴騰率(最安値比) (%)"] >= min_surge)

        filtered_df = df[cond]
        st.write(f"条件に一致した銘柄: **{len(filtered_df)}件** / 対象全{len(df)}銘柄中")
        
        if not filtered_df.empty:
            st.dataframe(filtered_df, use_container_width=True)
        else:
            st.info("条件に一致する銘柄が見つかりませんでした。")

    with tab3:
        st.subheader("🔎 銘柄個別チェッカー")
        search_ticker = st.selectbox("判定する銘柄を選択", all_tickers_list, key="chk_ticker_main")
        
        matched_rows = df[df["Ticker"] == search_ticker]
        if not matched_rows.empty:
            row = matched_rows.iloc[0]
            st.write(f"**社名**: {row['社名']} ({search_ticker})")
            st.write(f"**現在株価**: ${row['現在株価 ($)']:,.2f}")
            st.write(f"**暴落率(最高値比)**: {row['暴落率(最高値比) (%)']:+.2f}%")
            st.write(f"**暴騰率(最安値比)**: {row['暴騰率(最安値比) (%)']:+.2f}%")
            st.write(f"**予想PER**: {row['予想PER']}")
            st.write(f"**ROE**: {row['ROE (%)']}%")

    with tab4:
        st.subheader("📈 個別銘柄のチャート ＆ 出来高分析")
        selected_ticker = st.selectbox("チャートを表示する銘柄を選択", all_tickers_list, key="chart_select_main")
        
        chart_rows = df[df["Ticker"] == selected_ticker]
        if not chart_rows.empty:
            selected_row = chart_rows.iloc[0]
            st.metric("暴落率(最高値比)", f"{selected_row['暴落率(最高値比) (%)']:+.2f}%")
            st.metric("暴騰率(最安値比)", f"{selected_row['暴騰率(最安値比) (%)']:+.2f}%")
            
            stock_history = yf.Ticker(selected_ticker).history(period="1y")
            if not stock_history.empty:
                st.line_chart(stock_history['Close'])
                st.bar_chart(stock_history['Volume'])
