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

st.title("🏛️ 名選：米国株 高度スクリーニング＆ランキング")
st.markdown("S&P 500主要銘柄の財務・成長率（売上増・利益率）・騰落率・出来高を統合分析します。")

# 代表的なS&P 500主要銘柄のリスト
DEFAULT_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "JNJ", "V", 
    "JPM", "WMT", "PG", "MA", "UNH", "HD", "DIS", "BAC", "XOM", "CVX", 
    "NFLX", "AMD", "INTC", "QCOM", "IBM", "ORCL", "CRM", "ADBE", "NKE", "MCD"
]

@st.cache_data(ttl=86400) # 1日キャッシュして高速化
def fetch_stock_data(tickers):
    data = []
    end_date = datetime.today()
    date_1m = end_date - timedelta(days=30)
    date_3m = end_date - timedelta(days=90)
    date_1y = end_date - timedelta(days=365)
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # 株価・出来高履歴の取得
            hist = stock.history(start=date_1y)
            if hist.empty:
                continue
            
            current_price = hist['Close'].iloc[-1]
            
            # 各期間の価格から上昇率（%）を算出
            def get_return(target_date):
                sub_hist = hist.loc[hist.index >= pd.Timestamp(target_date, tz=hist.index.tz)]
                if not sub_hist.empty:
                    past_price = sub_hist['Close'].iloc[0]
                    return ((current_price - past_price) / past_price) * 100
                return 0.0

            return_1m = get_return(date_1m)
            return_3m = get_return(date_3m)
            return_1y = get_return(date_1y)
            
            # 財務データの取得
            total_revenue = info.get("totalRevenue", 0)
            net_income = info.get("netIncomeToCommon", 0)
            
            # 利益率（純利益 / 売上高）の計算
            profit_margin = (net_income / total_revenue) * 100 if total_revenue and net_income else None
            
            # 売上成長率（yfinanceのfinancialsから直近年次データを取得）
            rev_growth = None
            try:
                financials = stock.financials
                if financials is not None and "Total Revenue" in financials.index and len(financials.columns) >= 2:
                    recent_rev = financials.loc["Total Revenue"].iloc[0]
                    prev_rev = financials.loc["Total Revenue"].iloc[1]
                    if prev_rev and prev_rev > 0:
                        rev_growth = ((recent_rev - prev_rev) / prev_rev) * 100
            except Exception:
                pass

            data.append({
                "Ticker": ticker,
                "社名": info.get("shortName", ticker),
                "現在株価 ($)": current_price,
                "時価総額 ($)": info.get("marketCap", 0),
                "売上高 ($)": total_revenue,
                "純利益 ($)": net_income,
                "売上上昇率 (%)": rev_growth,
                "利益率 (%)": profit_margin,
                "PER": info.get("trailingPE", None),
                "予想PER": info.get("forwardPE", None),
                "PBR": info.get("priceToBook", None),
                "ROE (%)": info.get("returnOnEquity", 0) * 100 if info.get("returnOnEquity") else None,
                "配当利回り (%)": info.get("dividendYield", 0) * 100 if info.get("dividendYield") else 0,
                "1ヶ月騰落率 (%)": return_1m,
                "3ヶ月騰落率 (%)": return_3m,
                "1年騰落率 (%)": return_1y
            })
        except Exception:
            continue
            
    return pd.DataFrame(data)

# データ読み込み
with st.spinner("米国株の財務データ、成長率、株価・出来高を解析中..."):
    df = fetch_stock_data(DEFAULT_TICKERS)

if df.empty:
    st.error("データを取得できませんでした。時間をおいて再読み込みしてください。")
else:
    tab1, tab2, tab3 = st.tabs(["📊 総合ランキング", "🔍 複合スクリーニング（絞り込み）", "📈 個別チャート＆出来高"])
    
    with tab1:
        st.subheader("指標別ランキング一覧")
        sort_metric = st.selectbox(
            "並び替えの基準を選択",
            ["売上上昇率 (%)", "利益率 (%)", "時価総額 ($)", "売上高 ($)", "予想PER", "ROE (%)", "1年騰落率 (%)"],
            key="sort1"
        )
        
        ascending = True if sort_metric in ["予想PER", "PBR"] else False
        df_sorted = df.sort_values(by=sort_metric, ascending=ascending)
        
        st.dataframe(
            df_sorted.style.format({
                "現在株価 ($)": "${:,.2f}",
                "時価総額 ($)": "${:,.0f}",
                "売上高 ($)": "${:,.0f}",
                "純利益 ($)": "${:,.0f}",
                "売上上昇率 (%)": "{:+.2f}%" if "売上上昇率 (%)" in df_sorted.columns else "{}",
                "利益率 (%)": "{:.2f}%",
                "PER": "{:.2f}",
                "予想PER": "{:.2f}",
                "PBR": "{:.2f}",
                "ROE (%)": "{:.2f}%",
                "配当利回り (%)": "{:.2f}%",
                "1ヶ月騰落率 (%)": "{:+.2f}%",
                "3ヶ月騰落率 (%)": "{:+.2f}%",
                "1年騰落率 (%)": "{:+.2f}%"
            }),
            use_container_width=True
        )

    with tab2:
        st.subheader("複合条件による銘柄スクリーニング")
        st.markdown("売上成長・利益率・バリュエーション・株価の勢いを組み合わせて絞り込みます。")
        
        col1, col2 = st.columns(2)
        with col1:
            min_rev_growth = st.slider("売上上昇率の下限（前年比 %以上）", -20.0, 50.0, 5.0, 1.0)
            min_profit_margin = st.slider("利益率の下限（%以上）", -10.0, 50.0, 10.0, 1.0)
            max_forward_pe = st.slider("予想PERの上限（倍以下）", 5.0, 60.0, 35.0, 1.0)
        with col2:
            min_roe = st.slider("ROEの下限（%以上）", 0.0, 50.0, 10.0, 1.0)
            min_1y_return = st.slider("1年騰落率の下限（%以上）", -50.0, 100.0, 0.0, 5.0)
            max_pbr = st.slider("PBRの上限（倍以下）", 0.5, 30.0, 15.0, 0.5)
            
        # フィルター適用
        filtered_df = df[
            (df["売上上昇率 (%)"].fillna(-999) >= min_rev_growth) &
            (df["利益率 (%)"].fillna(-999) >= min_profit_margin) &
            (df["予想PER"].fillna(999) <= max_forward_pe) &
            (df["ROE (%)"].fillna(0) >= min_roe) &
            (df["1年騰落率 (%)"] >= min_1y_return) &
            (df["PBR"].fillna(999) <= max_pbr)
        ]
        
        st.write(f"条件に一致した銘柄: **{len(filtered_df)}件**")
        
        if not filtered_df.empty:
            st.dataframe(
                filtered_df.style.format({
                    "現在株価 ($)": "${:,.2f}",
                    "売上上昇率 (%)": "{:+.2f}%",
                    "利益率 (%)": "{:.2f}%",
                    "予想PER": "{:.2f}",
                    "ROE (%)": "{:.2f}%",
                    "1年騰落率 (%)": "{:+.2f}%"
                }),
                use_container_width=True
            )
        else:
            st.info("条件に一致する銘柄が見つかりませんでした。条件を調整してみてください。")

    with tab3:
        st.subheader("個別銘柄のチャート ＆ 出来高分析")
        selected_ticker = st.selectbox("銘柄を選択", df["Ticker"].tolist(), key="chart_select")
        
        selected_row = df[df["Ticker"] == selected_ticker].iloc[0]
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("売上上昇率(前年比)", f"{selected_row['売上上昇率 (%)']:+.2f}%" if pd.notnull(selected_row['売上上昇率 (%)']) else "N/A")
        c2.metric("利益率", f"{selected_row['利益率 (%)']:.2f}%" if pd.notnull(selected_row['利益率 (%)']) else "N/A")
        c3.metric("予想PER", f"{selected_row['予想PER']:.2f}倍" if pd.notnull(selected_row['予想PER']) else "N/A")
        c4.metric("1年騰落率", f"{selected_row['1年騰落率 (%)']:+.2f}%")
        
        st.markdown("---")
        st.markdown(f"**【{selected_row['社名']} ({selected_ticker}) の株価推移（折れ線）】**")
        
        # 株価チャートの描画
        stock_history = yf.Ticker(selected_ticker).history(period="1y")
        st.line_chart(stock_history['Close'])
        
        st.markdown(f"**【同期間の出来高（Volume）推移】**")
        st.bar_chart(stock_history['Volume'])
