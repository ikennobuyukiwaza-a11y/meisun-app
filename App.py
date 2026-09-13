import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# 1. ページ構成とアイコンの設定（ページの先頭に必ず置く必要があります）
st.set_page_config(
    page_title="名選 - 米国株統合選定・分析アプリ",
    page_icon="🐂", # またはカスタム画像
    layout="wide"
)

st.title("🏛️ 名選：米国株 高度スクリーニング＆ランキング")
st.markdown("S&P 500の主要銘柄を対象に、財務データ・予想・期間騰落率（上昇率/下降率）を統合分析します。")

# 2. 代表的なS&P 500主要銘柄のリスト（必要に応じて追加・変更可能）
# ※数が多いと読み込みに時間がかかるため、主要な代表銘柄で構成しています
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
            
            # 株価履歴の取得（騰落率計算用）
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
            
            # データの抽出
            data.append({
                "Ticker": ticker,
                "社名": info.get("shortName", ticker),
                "現在株価 ($)": current_price,
                "時価総額 ($)": info.get("marketCap", 0),
                "売上高 ($)": info.get("totalRevenue", 0),
                "純利益 ($)": info.get("netIncomeToCommon", 0),
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

# データ読み込みのインジケーター
with st.spinner("米国株の財務データおよび株価チャートを解析中...少々お待ちください。"):
    df = fetch_stock_data(DEFAULT_TICKERS)

if df.empty:
    st.error("データを取得できませんでした。しばらく経ってから再読み込みしてください。")
else:
    # 3. タブによる機能切り替え（見やすさを重視）
    tab1, tab2, tab3 = st.tabs(["📊 総合ランキング", "🔍 複合スクリーニング（絞り込み）", "📈 個別銘柄の深掘り"])
    
    with tab1:
        st.subheader("指標別ランキング一覧")
        sort_metric = st.selectbox(
            "並び替えの基準を選択",
            ["時価総額 ($)", "売上高 ($)", "純利益 ($)", "予想PER", "PBR", "ROE (%)", "1年騰落率 (%)", "1ヶ月騰落率 (%)"],
            key="sort1"
        )
        
        # 昇順・降順の切り替え
        ascending = True if sort_metric in ["予想PER", "PBR"] else False
        df_sorted = df.sort_values(by=sort_metric, ascending=ascending)
        
        st.dataframe(
            df_sorted.style.format({
                "現在株価 ($)": "${:,.2f}",
                "時価総額 ($)": "${:,.0f}",
                "売上高 ($)": "${:,.0f}",
                "純利益 ($)": "${:,.0f}",
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
        st.markdown("ご希望の条件スライダーを設定して、条件を満たす銘柄を絞り込みます。")
        
        col1, col2 = st.columns(2)
        with col1:
            max_forward_pe = st.slider("予想PERの上限（倍以下）", 5.0, 60.0, 30.0, 1.0)
            min_roe = st.slider("ROEの下限（%以上）", 0.0, 50.0, 10.0, 1.0)
        with col2:
            min_1y_return = st.slider("1年騰落率の下限（%以上、マイナス指定可）", -50.0, 100.0, -10.0, 5.0)
            max_pbr = st.slider("PBRの上限（倍以下）", 0.5, 20.0, 10.0, 0.5)
            
        # 条件でフィルター
        filtered_df = df[
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
                    "予想PER": "{:.2f}",
                    "PBR": "{:.2f}",
                    "ROE (%)": "{:.2f}%",
                    "1年騰落率 (%)": "{:+.2f}%"
                }),
                use_container_width=True
            )
        else:
            st.info("条件に一致する銘柄が見つかりませんでした。条件を少し緩めてみてください。")

    with tab3:
        st.subheader("個別銘柄の詳細チャート・財務チェック")
        selected_ticker = st.selectbox("銘柄を選択", df["Ticker"].tolist())
        
        selected_row = df[df["Ticker"] == selected_ticker].iloc[0]
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("現在株価", f"${selected_row['現在株価 ($)']:,.2f}")
        c2.metric("予想PER", f"{selected_row['予想PER']:.2f}倍" if pd.notnull(selected_row['予想PER']) else "N/A")
        c3.metric("PBR", f"{selected_row['PBR']:.2f}倍" if pd.notnull(selected_row['PBR']) else "N/A")
        c4.metric("1年騰落率", f"{selected_row['1年騰落率 (%)']:+.2f}%")
        
        st.markdown("---")
        st.markdown(f"**【{selected_row['社名']} ({selected_ticker}) の過去1年間株価推移】**")
        
        # 個別チャートの描画
        chart_data = yf.Ticker(selected_ticker).history(period="1y")['Close']
        st.line_chart(chart_data)
