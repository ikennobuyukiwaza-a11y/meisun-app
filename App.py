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
st.markdown("S&P 500全銘柄（約500社）を対象に、財務・高精度な暴落/暴騰率・チャートを完全連動で解析します。")

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
    ["S&P 500 全銘柄（約500社）", "軽量モード（主要30銘柄のみ高速テスト）"],
    index=0
)

if "全銘柄" in fetch_mode:
    target_tickers = ALL_SP500_TICKERS
    st.sidebar.info(f"S&P 500全 **{len(target_tickers)}銘柄** を対象に実行中（初回読み込み時は少し時間がかかります）。")
else:
    target_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "JNJ", "V", 
                      "JPM", "WMT", "PG", "MA", "UNH", "HD", "DIS", "BAC", "XOM", "CVX",
                      "NFLX", "AMD", "INTC", "QCOM", "IBM", "ORCL", "CRM", "ADBE", "NKE", "MCD"]
    st.sidebar.warning("軽量モード（主要30銘柄）で実行中。")

@st.cache_data(ttl=86400) # 1日キャッシュして高速化
def fetch_stock_data(tickers_tuple):
    data = []
    end_date = datetime.today()
    date_1y = end_date - timedelta(days=365)
    
    for ticker in tickers_tuple:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # 過去1年間の株価履歴取得
            hist = stock.history(start=date_1y)
            if hist.empty or len(hist) < 5:
                continue
            
            current_price = hist['Close'].iloc[-1]
            
            # 過去1年の最高値と最安値
            high_1y = hist['High'].max()
            low_1y = hist['Low'].min()
            
            # 暴落率：最高値から現在値への下落率（%） -> マイナス値
            drop_from_high = ((current_price - high_1y) / high_1y) * 100 if high_1y > 0 else 0.0
            
            # 暴騰率：最安値から現在値への上昇率（%） -> プラス値
            surge_from_low = ((current_price - low_1y) / low_1y) * 100 if low_1y > 0 else 0.0
            
            # 1ヶ月騰落率
            date_1m = end_date - timedelta(days=30)
            sub_hist_1m = hist.loc[hist.index >= pd.Timestamp(date_1m, tz=hist.index.tz)]
            return_1m = ((current_price - sub_hist_1m['Close'].iloc[0]) / sub_hist_1m['Close'].iloc[0]) * 100 if not sub_hist_1m.empty else 0.0
            
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
                "過去1年最高値 ($)": high_1y,
                "過去1年最安値 ($)": low_1y,
                "暴落率(最高値比) (%)": drop_from_high,
                "暴騰率(最安値比) (%)": surge_from_low,
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
                "1ヶ月騰落率 (%)": return_1m
            })
        except Exception:
            continue
            
    return pd.DataFrame(data)

with st.spinner(f"対象銘柄（{len(target_tickers)}社）の財務・チャートデータを読み込み・解析中..."):
    df = fetch_stock_data(tuple(target_tickers))

if df.empty:
    st.error("データを取得できませんでした。時間をおいて再読み込みしてください。")
else:
    # 銘柄リスト（重複なし・アルファベット順）
    all_tickers_list = sorted(df["Ticker"].unique().tolist())

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
        st.markdown("各項目の **「チェックボックスをON/OFF」** して、必要な条件だけで絞り込んでください。")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### ① 財務・成長・バリュエーション")
            use_rev = st.checkbox("売上上昇率の条件を有効にする", value=True, key="c_rev")
            min_rev_growth = st.slider("売上上昇率の下限（前年比 %以上）", -50.0, 100.0, 0.0, 1.0, key="s_rev")
            
            use_margin = st.checkbox("利益率の条件を有効にする", value=True, key="c_margin")
            min_profit_margin = st.slider("利益率の下限（%以上）", -20.0, 80.0, 5.0, 1.0, key="s_margin")
            
            use_pe = st.checkbox("予想PERの条件を有効にする", value=True, key="c_pe")
            max_forward_pe = st.slider("予想PERの上限（倍以下）", 5.0, 300.0, 50.0, 5.0, key="s_pe")
            
            use_pbr = st.checkbox("PBRの条件を有効にする", value=True, key="c_pbr")
            max_pbr = st.slider("PBRの上限（倍以下）", 0.5, 100.0, 20.0, 1.0, key="s_pbr")

        with col2:
            st.markdown("##### ② 収益性・株価変動（暴落/暴騰）")
            use_roe = st.checkbox("ROEの条件を有効にする", value=True, key="c_roe")
            min_roe = st.slider("ROEの下限（%以上）", -10.0, 100.0, 10.0, 1.0, key="s_roe")
            
            use_drop = st.checkbox("暴落率（過去1年最高値からの下落）の条件を有効にする", value=False, key="c_drop")
            max_drop = st.slider("暴落率の上限（最高値比 %以下。例: -20%以下なら-20）", -90.0, 0.0, -20.0, 5.0, key="s_drop")
            
            use_surge = st.checkbox("暴騰率（過去1年最安値からの上昇）の条件を有効にする", value=False, key="c_surge")
            min_surge = st.slider("暴騰率の下限（最安値比 %以上。例: +50%以上なら50）", 0.0, 300.0, 50.0, 10.0, key="s_surge")

        # フィルター適用ロジック
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
        
        st.markdown("---")
        st.write(f"条件に一致した銘柄: **{len(filtered_df)}件** / 対象全{len(df)}銘柄中")
        
        if not filtered_df.empty:
            st.dataframe(
                filtered_df.style.format({
                    "現在株価 ($)": "${:,.2f}",
                    "過去1年最高値 ($)": "${:,.2f}",
                    "暴落率(最高値比) (%)": "{:+.2f}%",
                    "暴騰率(最安値比) (%)": "{:+.2f}%",
                    "売上上昇率 (%)": "{:+.2f}%",
                    "利益率 (%)": "{:.2f}%",
                    "予想PER": "{:.2f}",
                    "PBR": "{:.2f}",
                    "ROE (%)": "{:.2f}%"
                }),
                use_container_width=True
            )
        else:
            st.info("条件に一致する銘柄が見つかりませんでした。条件やチェックボックスを調整してみてください。")

        with tab3:
            st.subheader("🔎 銘柄個別チェッカー（スクリーニング合否＆理由の色分け）")
            st.markdown("全取得銘柄から任意の銘柄を選んで、現在有効なスクリーニング条件を満たしているかを個別判定できます。")
            
            search_ticker = st.selectbox("判定する銘柄を選択・検索", all_tickers_list, key="chk_ticker_main")
            st.markdown("---")
            st.markdown("##### 現在の有効な条件との照合結果:")
            
            matched_rows = df[df["Ticker"] == search_ticker]
            if matched_rows.empty:
                st.warning("選択された銘柄のデータが見つかりませんでした。")
            else:
                row = matched_rows.iloc[0]
                
                checks = []
                if use_rev:
                    checks.append(("売上上昇率", row["売上上昇率 (%)"], min_rev_growth, lambda v, th: v is not None and v >= th, f"{min_rev_growth}%以上", "%"))
                if use_margin:
                    checks.append(("利益率", row["利益率 (%)"], min_profit_margin, lambda v, th: v is not None and v >= th, f"{min_profit_margin}%以上", "%"))
                if use_pe:
                    checks.append(("予想PER", row["予想PER"], max_forward_pe, lambda v, th: v is not None and v <= th, f"{max_forward_pe}倍以下", "倍"))
                if use_pbr:
                    checks.append(("PBR", row["PBR"], max_pbr, lambda v, th: v is not None and v <= th, f"{max_pbr}倍以下", "倍"))
                if use_roe:
                    checks.append(("ROE", row["ROE (%)"], min_roe, lambda v, th: v is not None and v >= th, f"{min_roe}%以上", "%"))
                if use_drop:
                    checks.append(("暴落率(最高値比)", row["暴落率(最高値比) (%)"], max_drop, lambda v, th: v is not None and v <= th, f"{max_drop}%以下（より深く下落）", "%"))
                if use_surge:
                    checks.append(("暴騰率(最安値比)", row["暴騰率(最安値比) (%)"], min_surge, lambda v, th: v is not None and v >= th, f"{min_surge}%以上", "%"))

                if not checks:
                    st.info("現在、すべてのスクリーニング条件のチェックボックスがOFFになっています。")
                else:
                    all_passed = True
                    for label, val, threshold, eval_func, desc, unit in checks:
                        passed = eval_func(val, threshold)
                        if not passed:
                            all_passed = False
                        
                        val_str = f"{val:,.2f}{unit}" if pd.notnull(val) else "データなし"
                        if unit == "%" and pd.notnull(val) and "率" in label:
                            val_str = f"{val:+.2f}%"

                        if passed:
                            st.success(f"✅ **{label}**: 合格 (実績値: **{val_str}** / 条件: {desc})")
                        else:
                            st.error(f"❌ **{label}**: 不合格 (外れています ⚠️ 実績値: **{val_str}** / 条件: {desc})")
                    
                    st.markdown("---")
                    if all_passed:
                        st.balloons()
                        st.markdown(f"### 🎉 判定結果： **{row['社名']} ({search_ticker})** は現在有効なすべてのスクリーニング条件をクリアしています！")
                    else:
                        st.warning(f"⚠️ 判定結果： **{row['社名']} ({search_ticker})** は一部の条件を満たしていないため除外されています。")

        with tab4:
            st.subheader("📈 個別銘柄のチャート ＆ 出来高分析")
            selected_ticker = st.selectbox("チャートを表示する銘柄を選択", all_tickers_list, key="chart_select_main")
            
            chart_rows = df[df["Ticker"] == selected_ticker]
            if chart_rows.empty:
                st.warning("選択された銘柄のデータが見つかりませんでした。")
            else:
                selected_row = chart_rows.iloc[0]
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("暴落率(最高値比)", f"{selected_row['暴落率(最高値比) (%)']:+.2f}%")
                c2.metric("暴騰率(最安値比)", f"{selected_row['暴騰率(最安値比) (%)']:+.2f}%")
                c3.metric("予想PER", f"{selected_row['予想PER']:.2f}倍" if pd.notnull(selected_row['予想PER']) else "N/A")
                c4.metric("PBR", f"{selected_row['PBR']:.2f}倍" if pd.notnull(selected_row['PBR']) else "N/A")
                
                st.markdown("---")
                st.markdown(f"**【{selected_row['社名']} ({selected_ticker}) の株価推移（1年間）】**")
                
                stock_history = yf.Ticker(selected_ticker).history(period="1y")
                if not stock_history.empty:
                    st.line_chart(stock_history['Close'])
                    st.markdown(f"**【同期間の出来高（Volume）推移】**")
                    st.bar_chart(stock_history['Volume'])
                else:
                    st.info("チャートデータを取得できませんでした。")
