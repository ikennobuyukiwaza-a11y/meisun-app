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

st.title("🏛️ 名選：S&P 500 統合スクリーニング＆全銘柄分析")
st.markdown("S&P 500全銘柄を対象に、財務・成長率・暴落/暴騰率・出来高を分析します。")

# S&P 500の全ティッカーをWikipediaから自動取得する関数
@st.cache_data(ttl=86400)
def get_sp500_tickers():
    try:
        table = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
        df = table[0]
        tickers = df['Symbol'].tolist()
        # yfinance用にドットをハイフンに置換 (例: BRK.B -> BRK-B)
        tickers = [t.replace('.', '-') for t in tickers]
        return tickers
    except Exception:
        # 万が一取得できない場合のフォールバック（主要銘柄）
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "JNJ", "V", 
                "JPM", "WMT", "PG", "MA", "UNH", "HD", "DIS", "BAC", "XOM", "CVX"]

ALL_SP500_TICKERS = get_sp500_tickers()

# すぐに選べる代表的・主要な注目銘柄リスト
DEFAULT_SELECTED = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JNJ", "V", "JPM", "XOM", "NFLX", "AMD"]

st.sidebar.header("🎯 検索対象の銘柄選択")
select_all_mode = st.sidebar.checkbox("S&P 500全銘柄（約500社）を対象にする", value=False)

if select_all_mode:
    target_tickers = ALL_SP500_TICKERS
    st.sidebar.info(f"現在、S&P 500全 **{len(target_tickers)}銘柄** を対象にしています（※初回読み込みに少し時間がかかります）。")
else:
    # チェックボックスで簡単に選択・除外できるようにする
    st.sidebar.markdown("下のチェックボックスで対象を自由にON/OFFできます：")
    target_tickers = []
    for t in DEFAULT_SELECTED:
        if st.sidebar.checkbox(f"{t}", value=True, key=f"chk_{t}"):
            target_tickers.append(t)

@st.cache_data(ttl=86400) # 1日キャッシュして高速化
def fetch_stock_data(tickers_tuple):
    data = []
    end_date = datetime.today()
    date_1m = end_date - timedelta(days=30)
    date_3m = end_date - timedelta(days=90)
    date_1y = end_date - timedelta(days=365)
    
    for ticker in tickers_tuple:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # 株価・出来高履歴の取得
            hist = stock.history(start=date_1y)
            if hist.empty:
                continue
            
            current_price = hist['Close'].iloc[-1]
            
            def get_return(target_date):
                sub_hist = hist.loc[hist.index >= pd.Timestamp(target_date, tz=hist.index.tz)]
                if not sub_hist.empty:
                    past_price = sub_hist['Close'].iloc[0]
                    return ((current_price - past_price) / past_price) * 100
                return 0.0

            return_1m = get_return(date_1m)
            return_3m = get_return(date_3m)
            return_1y = get_return(date_1y)
            
            total_revenue = info.get("totalRevenue", 0)
            net_income = info.get("netIncomeToCommon", 0)
            profit_margin = (net_income / total_revenue) * 100 if total_revenue and total_revenue > 0 else None
            
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

if not target_tickers:
    st.warning("左側のサイドバーで対象銘柄が選択されていません。少なくとも1つ以上チェックを入れるか、全銘柄モードを有効にしてください。")
else:
    with st.spinner(f"選択された {len(target_tickers)} 銘柄の財務・株価データを解析中..."):
        df = fetch_stock_data(tuple(target_tickers))

    if df.empty:
        st.error("データを取得できませんでした。時間をおいて再読み込みしてください。")
    else:
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 総合ランキング", 
            "🔍 複合スクリーニング", 
            "🔎 個別銘柄チェッカー（合否判定）", 
            "📈 個別チャート＆出来高"
        ])
        
        with tab1:
            st.subheader("指標別ランキング一覧")
            sort_metric = st.selectbox(
                "並び替えの基準を選択",
                ["1年騰落率 (%)", "1ヶ月騰落率 (%)", "売上上昇率 (%)", "利益率 (%)", "時価総額 ($)", "売上高 ($)", "予想PER", "ROE (%)"],
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
                    "売上上昇率 (%)": "{:+.2f}%",
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
            st.markdown("条件を設定して、暴落・暴騰銘柄や高成長・割安銘柄を一発抽出します。")
            
            col1, col2 = st.columns(2)
            with col1:
                min_rev_growth = st.slider("売上上昇率の下限（前年比 %以上）", -50.0, 100.0, 0.0, 1.0)
                min_profit_margin = st.slider("利益率の下限（%以上）", -20.0, 80.0, 5.0, 1.0)
                max_forward_pe = st.slider("予想PERの上限（倍以下）", 5.0, 300.0, 50.0, 5.0)  # 上限300倍
            with col2:
                min_roe = st.slider("ROEの下限（%以上）", -10.0, 100.0, 10.0, 1.0)
                min_1y_return = st.slider("1年騰落率の下限（暴落〜暴騰フィルタ %）", -80.0, 200.0, -20.0, 5.0)
                max_pbr = st.slider("PBRの上限（倍以下）", 0.5, 100.0, 20.0, 1.0)          # 上限100倍
                
            # フィルター適用
            filtered_df = df[
                (df["売上上昇率 (%)"].fillna(-999) >= min_rev_growth) &
                (df["利益率 (%)"].fillna(-999) >= min_profit_margin) &
                (df["予想PER"].fillna(999) <= max_forward_pe) &
                (df["ROE (%)"].fillna(0) >= min_roe) &
                (df["1年騰落率 (%)"] >= min_1y_return) &
                (df["PBR"].fillna(999) <= max_pbr)
            ]
            
            st.write(f"条件に一致した銘柄: **{len(filtered_df)}件** / 対象全{len(df)}銘柄中")
            
            if not filtered_df.empty:
                st.dataframe(
                    filtered_df.style.format({
                        "現在株価 ($)": "${:,.2f}",
                        "売上上昇率 (%)": "{:+.2f}%",
                        "利益率 (%)": "{:.2f}%",
                        "予想PER": "{:.2f}",
                        "PBR": "{:.2f}",
                        "ROE (%)": "{:.2f}%",
                        "1年騰落率 (%)": "{:+.2f}%"
                    }),
                    use_container_width=True
                )
            else:
                st.info("条件に一致する銘柄が見つかりませんでした。条件を調整してみてください。")

        with tab3:
            st.subheader("🔎 銘柄個別チェッカー（スクリーニング合否＆理由の色分け表示）")
            st.markdown("気になる銘柄コードを入力または選択すると、現在のスクリーニング条件に合格しているか、**どの条件で外れているか**を色付きで判定します。")
            
            search_ticker = st.selectbox("判定する銘柄を選択・検索", df["Ticker"].tolist(), key="chk_ticker")
            
            # タブ2で設定したスライダー条件をここでも判定用に適用
            st.markdown("---")
            st.markdown("##### 現在のスリーニング基準との照合結果:")
            
            row = df[df["Ticker"] == search_ticker].iloc[0]
            
            # 各条件の判定
            checks = [
                ("売上上昇率 (前年比)", row["売上上昇率 (%)"], min_rev_growth, ">=ో", lambda v, th: v is not None and v >= th, f"{min_rev_growth}%以上"),
                ("利益率", row["利益率 (%)"], min_profit_margin, ">=", lambda v, th: v is not None and v >= th, f"{min_profit_margin}%以上"),
                ("予想PER", row["予想PER"], max_forward_pe, "<=", lambda v, th: v is not None and v <= th, f"{max_forward_pe}倍以下"),
                ("ROE", row["ROE (%)"], min_roe, ">=", lambda v, th: v is not None and v >= th, f"{min_roe}%以上"),
                ("1年騰落率", row["1年騰落率 (%)"], min_1y_return, ">=", lambda v, th: v is not None and v >= th, f"{min_1y_return}%以上"),
                ("PBR", row["PBR"], max_pbr, "<=", lambda v, th: v is not None and v <= th, f"{max_pbr}倍以下")
            ]
            
            all_passed = True
            for label, val, threshold, op_str, eval_func, desc in checks:
                passed = eval_func(val, threshold)
                if not passed:
                    all_passed = False
                
                val_str = f"{val:,.2f}" if pd.notnull(val) else "データなし"
                if "%" in label and pd.notnull(val):
                    val_str = f"{val:+.2f}%" if "騰落" in label or "上昇" in label else f"{val:.2f}%"
                elif "PER" in label or "PBR" in label:
                    val_str = f"{val:.2f}倍" if pd.notnull(val) else "データなし"

                if passed:
                    st.success(f"✅ **{label}**: 合格 (実績値: **{val_str}** / 条件: {desc})")
                else:
                    st.error(f"❌ **{label}**: 不合格 (外れています ⚠️ 実績値: **{val_str}** / 条件: {desc})")
            
            st.markdown("---")
            if all_passed:
                st.balloons()
                st.markdown(f"### 🎉 判定結果： **{row['社名']} ({search_ticker})** は現在のすべてのスクリーニング条件をクリアしています！")
            else:
                st.warning(f"⚠️ 判定結果： **{row['社名']} ({search_ticker})** は一部の条件を満たしていないため、スクリーニングから除外されています。")

        with tab4:
            st.subheader("📈 個別銘柄のチャート ＆ 出来高分析")
            selected_ticker = st.selectbox("チャートを表示する銘柄を選択", df["Ticker"].tolist(), key="chart_select")
            
            selected_row = df[df["Ticker"] == selected_ticker].iloc[0]
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("1年騰落率", f"{selected_row['1年騰落率 (%)']:+.2f}%")
            c2.metric("予想PER", f"{selected_row['予想PER']:.2f}倍" if pd.notnull(selected_row['予想PER']) else "N/A")
            c3.metric("PBR", f"{selected_row['PBR']:.2f}倍" if pd.notnull(selected_row['PBR']) else "N/A")
            c4.metric("ROE", f"{selected_row['ROE (%)']:.2f}%" if pd.notnull(selected_row['ROE (%)']) else "N/A")
            
            st.markdown("---")
            st.markdown(f"**【{selected_row['社名']} ({selected_ticker}) の株価推移（1年間）】**")
            
            stock_history = yf.Ticker(selected_ticker).history(period="1y")
            st.line_chart(stock_history['Close'])
            
            st.markdown(f"**【同期間の出来高（Volume）推移】**")
            st.bar_chart(stock_history['Volume'])
