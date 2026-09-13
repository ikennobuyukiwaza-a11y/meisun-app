import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# 1. ページ構成とアイコンの設定
st.set_page_config(
    page_title="名選 - 米国株統合選定・分析アプリ",
    page_icon="🐂",
    layout="wide"
)

st.title("🏛️ 名選：S&P 500 銘柄 統合スクリーニング＆分析")
st.markdown("ランキング・スクリーニング機能と、アナリスト予想・EPSを含む詳細な個別銘柄アナライザーを備えた安定版です。")

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

st.sidebar.header("🎯 表示モードの切替")
app_mode = st.sidebar.radio(
    "機能選択",
    ["📊 総合ランキング ＆ スクリーニング", "🔎 個別銘柄 詳細アナライザー"],
    index=0,
    key="app_mode_radio"
)

st.sidebar.markdown("---")
st.sidebar.header("🎯 検索対象の切替（ランキング用）")
fetch_mode = st.sidebar.radio(
    "対象選択",
    ["S&P 500 全銘柄（約500社）", "軽量モード（主要30銘柄のみ高速テスト）"],
    index=0,
    key="fetch_mode_radio"
)

if "全銘柄" in fetch_mode:
    target_tickers = ALL_SP500_TICKERS
    st.sidebar.info(f"S&P 500全 **{len(target_tickers)}銘柄** を対象に実行中。")
else:
    target_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "JNJ", "V", 
                      "JPM", "WMT", "PG", "MA", "UNH", "HD", "DIS", "BAC", "XOM", "CVX",
                      "NFLX", "AMD", "INTC", "QCOM", "IBM", "ORCL", "CRM", "ADBE", "NKE", "MCD"]
    st.sidebar.warning("軽量モード（主要30銘柄）で実行中。")

# 1銘柄分のデータを安全に取得する関数
def fetch_single_stock(ticker):
    try:
        end_date = datetime.today()
        date_1y = end_date - timedelta(days=365)
        
        stock = yf.Ticker(ticker)
        hist = stock.history(start=date_1y)
        if hist.empty or len(hist) < 5:
            return None
            
        current_price = hist['Close'].iloc[-1]
        high_1y = hist['High'].max()
        low_1y = hist['Low'].min()
        
        drop_from_high = ((current_price - high_1y) / high_1y) * 100 if high_1y > 0 else 0.0
        surge_from_low = ((current_price - low_1y) / low_1y) * 100 if low_1y > 0 else 0.0
        
        date_1m = end_date - timedelta(days=30)
        sub_hist_1m = hist.loc[hist.index >= pd.Timestamp(date_1m, tz=hist.index.tz) if hist.index.tz else pd.Timestamp(date_1m)]
        return_1m = ((current_price - sub_hist_1m['Close'].iloc[0]) / sub_hist_1m['Close'].iloc[0]) * 100 if not sub_hist_1m.empty else 0.0

        info = stock.info
        total_revenue = info.get("totalRevenue", 0)
        net_income = info.get("netIncomeToCommon", 0)
        profit_margin = (net_income / total_revenue) * 100 if total_revenue and total_revenue > 0 else None

        return {
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
        }
    except Exception:
        return None

@st.cache_data(ttl=86400)
def fetch_stock_data_parallel(tickers_tuple):
    data = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_single_stock, ticker): ticker for ticker in tickers_tuple}
        for future in as_completed(futures):
            res = future.result()
            if res is not None:
                data.append(res)
    return pd.DataFrame(data)

# モードの分岐
if app_mode == "📊 総合ランキング ＆ スクリーニング":
    with st.spinner(f"対象銘柄（{len(target_tickers)}社）のデータを高速並列解析中..."):
        df = fetch_stock_data_parallel(tuple(target_tickers))

    if df.empty:
        st.error("データを取得できませんでした。「軽量モード」に切り替えてお試しください。")
    else:
        tab1, tab2 = st.tabs([
            "📊 総合ランキング", 
            "🔍 複合スクリーニング"
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

else:
    # 個別銘柄 詳細アナライザーモード
    st.subheader("🔎 個別銘柄 詳細アナライザー（チャート・業績予想・実績）")
    st.markdown("任意のティッカーシンボル（例: `AAPL`, `MSFT`, `GOOGL`, `NVDA`, `TSLA` 等）を入力または選択してください。")
    
    col_input1, col_input2 = st.columns([2, 3])
    with col_input1:
        input_ticker = st.text_input("ティッカーシンボルを入力", value="AAPL").upper().strip()
    with col_input2:
        select_ticker = st.selectbox("または代表的な銘柄から選択", ALL_SP500_TICKERS[:30], key="select_ticker_quick")
    
    target_symbol = input_ticker if input_ticker else select_ticker
    
    if target_symbol:
        with st.spinner(f"【{target_symbol}】の詳細データ・アナリスト予想を取得中..."):
            try:
                stock_obj = yf.Ticker(target_symbol)
                info = stock_obj.info
                company_name = info.get("shortName", target_symbol)
                
                st.markdown(f"### 📌 銘柄情報: **{company_name} ({target_symbol})**")
                
                # 基本指標の表示
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("現在株価", f"${info.get('currentPrice', info.get('regularMarketPrice', 0)):,.2f}")
                c2.metric("時価総額", f"${info.get('marketCap', 0):,.0f}")
                c3.metric("実績PER(TTM)", f"{info.get('trailingPE', 'N/A')}")
                c4.metric("予想PER(Fwd)", f"{info.get('forwardPE', 'N/A')}")
                
                trailing_eps = info.get('trailingEps', None)
                c5.metric("EPS (TTM)", f"${trailing_eps:,.2f}" if trailing_eps is not None else "N/A")
                
                st.markdown("---")
                
                # 1. チャート ＆ 出来高
                st.markdown("#### 📈 株価チャート ＆ 出来高（過去1年間）")
                hist_data = stock_obj.history(period="1y")
                if not hist_data.empty:
                    st.line_chart(hist_data['Close'])
                    st.markdown("**【出来高 (Volume)】**")
                    st.bar_chart(hist_data['Volume'])
                else:
                    st.warning("株価履歴データが見つかりませんでした。")
                
                st.markdown("---")
                
                # 2. アナリストの業績予想（EPS・売上高）※場所をチャートと四半期実績の間に配置
                st.markdown("#### 🎯 アナリスト業績予想コンセンサス（EPS / 売上高）")
                st.markdown("`0q`は今期(直近)、`+1q`は1四半期先、`0y`は今年度、`+1y`は来年度の予想です（growthは前年同期/前期比の成長率）。")
                
                try:
                    earnings_est = stock_obj.earnings_estimate
                    if earnings_est is not None and not earnings_est.empty:
                        st.markdown("**【EPS 予想 (Earnings Estimate)】**")
                        st.dataframe(earnings_est, use_container_width=True)
                    else:
                        st.info("EPS予想データが取得できませんでした。")
                except Exception:
                    st.info("EPS予想データを取得できませんでした。")

                try:
                    revenue_est = stock_obj.revenue_estimate
                    if revenue_est is not None and not revenue_est.empty:
                        st.markdown("**【売上高 予想 (Revenue Estimate)】**")
                        st.dataframe(revenue_est, use_container_width=True)
                    else:
                        st.info("売上高予想データが取得できませんでした。")
                except Exception:
                    st.info("売上高予想データを取得できませんでした。")

                st.markdown("---")
                
                # 3. 四半期ごとの損益計算書データ（EPSを含む実績）
                st.markdown("#### 📊 四半期ごとの実績業績 ＆ EPS推移（直近5期分）")
                q_fin = stock_obj.get_income_stmt(freq="quarterly")
                if q_fin is not None and not q_fin.empty:
                    st.dataframe(q_fin.style.format("{:,.2f}"), use_container_width=True)
                else:
                    st.info("四半期業績データが見つかりませんでした。")
                
                st.markdown("---")
                
                # 4. 年別の損益計算書データ（EPSを含む実績）
                st.markdown("#### 📅 年別の実績業績 ＆ EPS推移（過去5年分）")
                y_fin = stock_obj.get_income_stmt(freq="yearly")
                if y_fin is not None and not y_fin.empty:
                    st.dataframe(y_fin.style.format("{:,.2f}"), use_container_width=True)
                else:
                    st.info("年別業績データが見つかりませんでした。")
                    
            except Exception as e:
                st.error(f"データの取得中にエラーが発生しました。正しいティッカーかご確認ください。（エラー詳細: {e}）")
