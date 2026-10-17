import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta

def calculate_metrics(df):
    start_price = df["Close"].iloc[0]
    latest_price = df["Close"].iloc[-1]

    return {
    "Latest Price": latest_price,
    "Period Return": (latest_price - start_price)/ start_price,
    "52Week High": df["Close"].max(),
    "52Week Low": df["Close"].min(),
    "Annualized Volatility": df["Close"].pct_change()
    .std() * (252 ** 0.5),
    "Max Drawdown": ((df["Close"] - df["Close"]
                      .cummax()) / df["Close"]
                      .cummax()).min(),
    "Avg Daily Volume": df["Volume"].mean()}


# ==========================================
# 1. PAGE SETUP & SIDEBAR INPUTS
# ==========================================
st.set_page_config(page_title="Equity Research Dashboard", layout="wide")
st.title("📊 Interactive Equity Research Dashboard")

st.sidebar.header("User Parameters")
ticker = st.sidebar.text_input("Stock Ticker", value="AAPL").strip().upper()
benchmark = st.sidebar.selectbox("Benchmark", ["^GSPC", "^HSI", "^IXIC"])
peers_input = st.sidebar.text_input("Peer Tickers (comma-separated)",
                                    value="2388.HK, 0011.HK, 2888.HK"
                                    )
start_date = st.sidebar.date_input("Start Date", 
                                   value=date.today() - timedelta(days=365))
end_date = st.sidebar.date_input("End Date", value=date.today())

# ==========================================
# 2. DATA INGESTION & ERROR HANDLING
# ==========================================
df = yf.download(ticker, start=start_date, end=end_date)

if df.empty:
    st.error(f"Could not find any data for ticker '{ticker}'. Please check the spelling or date range.")
else:
    # Flatten MultiIndex columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)

    # ==========================================
    # 3. FINANCIAL CALCULATIONS
    # ==========================================
    main_metrics= calculate_metrics(df)
    peer_list = [p.strip().upper()for p in peers_input.split(",") if p.strip()]
    peer_summary = []
    main_metrics["Ticker"] = ticker
    peer_summary.append(main_metrics)
    for peer in peer_list:
        peer_df = yf.download(peer, start=start_date, end=end_date)

        if peer_df.empty or len(peer_df) < 2:
            st.warning(f"Could not retrieve data for peer '{peer}'. Skipping.")
            continue
        if isinstance(peer_df.columns, pd.MultiIndex):
            peer_df.columns = peer_df.columns.droplevel(1)
        metrics = calculate_metrics(peer_df)
        metrics["Ticker"] = peer
        peer_summary.append(metrics)

    # Technical Indicators (Moving Averages)
    df["SMA_20"] = df["Close"].rolling(20).mean()
    df["SMA_50"] = df["Close"].rolling(50).mean()

    # ==========================================
    # 4. KEY METRICS DISPLAY (KPI CARDS)
    # ==========================================
    stock = yf.Ticker(ticker)
    info = stock.info
    company_name = info.get("longName", ticker)
    sector = info.get("sector","N/A")
    industry = info.get("industry", "N/A")
    pe_ratio = info.get("trailingPE", "N/A")
    pb_ratio = info.get("priceToBook", "N/A")
    div_yield = info.get("dividendYield", "N/A")
    market_cap = info.get("marketCap", "N/A")
    st.header(f"🏢 {company_name}")
    st.caption(f"**Sector:** {sector} | **Industry:** {industry}")
    st.subheader(f"Key Performance Indicators: {ticker}")
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    col_f1.metric(
        label="Market Cap",
        value=f"${(market_cap / 1e9):.2f}B"
        if isinstance(market_cap, (int, float)) else "N/A"
    )
    col_f2.metric(
        label="Trailing P/E",
        value=f"{pe_ratio:.2f}"
        if isinstance(pe_ratio, (int, float)) else "N/A"
    )
    col_f3.metric(
        label="Price-to-Book (P/B)",
        value=f"{pb_ratio:.2f}"
        if isinstance(pb_ratio, (int, float)) else "N/A"
    )
    col_f4.metric(
        label="Dividend Yield",
        value=f"{div_yield:.2f}"
        if isinstance(div_yield, (int, float)) else "N/A"
    )
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        label="Latest Price",
        value=f"${main_metrics['Latest Price']:.2f}",
        delta=f"{main_metrics['Period Return'] * 100:.2f}%"
    )
    col2.metric(label="Period High", 
                value=f"${main_metrics['52Week High']:.2f}")
    col3.metric(label="Period Low", 
                value=f"${main_metrics['52Week Low']:.2f}")
    col4.metric(label="Avg Daily Volume", 
                value=f"{main_metrics['Avg Daily Volume']:,.0f}")

    col5, col6 = st.columns(2)
    col5.metric(label="Annualized Volatility", 
                value=f"{main_metrics['Annualized Volatility'] * 100:.2f}%")
    col6.metric(label="Maximum Drawdown", 
                value=f"{main_metrics['Max Drawdown'] * 100:.2f}%")

    st.markdown("---")

    # ==========================================
    # 5. CHART 1: PRICE & MOVING AVERAGES
    # ==========================================
    st.subheader("📈 Historical Price & Moving Averages")
    
    fig = go.Figure()
    fig.add_scatter(x=df.index, y=df["Close"], mode="lines", name="Close Price")
    fig.add_scatter(x=df.index, y=df["SMA_20"], mode="lines", name="20-day SMA")
    fig.add_scatter(x=df.index, y=df["SMA_50"], mode="lines", name="50-day SMA")
    
    fig.update_layout(
        template="plotly_white",
        yaxis_title="Stock Price (USD / Local)",
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

    # ==========================================
    # 6. CHART 2: BENCHMARK COMPARISON
    # ==========================================
    st.subheader(f"⚖️ Performance Comparison: {ticker} vs. {benchmark}")

    df_bench = yf.download(benchmark, start=start_date, end=end_date)
    
    if df_bench.empty:
        st.warning(f"Could not retrieve benchmark data for {benchmark}.")
    else:
        if isinstance(df_bench.columns, pd.MultiIndex):
            df_bench.columns = df_bench.columns.droplevel(1)

        # Normalize both series (Rebased to 100)
        df["Normalized_Value"] = (df["Close"] / df["Close"].iloc[0]) * 100
        df_bench["Normalized_Value"] = (df_bench["Close"] / df_bench["Close"].iloc[0]) * 100

        stock_return = df["Close"].pct_change()
        bench_return = df_bench["Close"].pct_change()

        covariance = stock_return.cov(bench_return)
        variance = bench_return.var()
        correlation = stock_return.corr(bench_return)
        beta = covariance / variance
        bench_period_return = ((df_bench["Close"].iloc[-1] -
                                df_bench["Close"].iloc[0])
                                / df_bench["Close"].iloc[0])
        col1, col2, col3 = st.columns(3)
        col1.metric(
            label = "Benchmark Return",
            value = f"{bench_period_return:.2f}"
        )
        col2.metric(
            label = "Beta Sensitivity",
            value = f"{beta:.2f}"
        )
        col3.metric(
            label = "Correlation",
            value = f"{correlation:.2f}"
        )

        fig_compare = go.Figure()
        fig_compare.add_scatter(x=df.index, 
                                y=df["Normalized_Value"], mode="lines", 
                                name=ticker)
        fig_compare.add_scatter(x=df_bench.index, 
                                y=df_bench["Normalized_Value"], 
                                mode="lines", name=benchmark)

        fig_compare.update_layout(
            template="plotly_white",
            yaxis_title="Normalized Return (Base = 100)",
            hovermode="x unified"
        )
        st.plotly_chart(fig_compare, use_container_width=True)

    # ==========================================
    # 7. PEER PERFORMANCE RANKING TABLE
    # ==========================================
    st.subheader("🏁 Peer Performance Ranking")
    peer_table = pd.DataFrame(peer_summary)
    cols = ["Ticker"] + [c for c in peer_table.columns if c != "Ticker"]
    peer_table = peer_table[cols]

    st.dataframe(peer_table, use_container_width=True)

    csv_data = peer_table.to_csv(index=False)
    st.download_button(label="📥 Download Peer Comparison (CSV)",
                       data= csv_data,
                       file_name= f"{ticker}_peer_analysis.csv",
                       mime= "text/csv")


    # ==========================================
    # 8. RISK-RETURN SCATTER PLOT
    # ==========================================

    fig_risk = go.Figure()
    fig_risk.add_scatter(
        x = peer_table["Annualized Volatility"] * 100,
        y = peer_table["Period Return"] * 100,
        mode = "markers+text",
        text = peer_table["Ticker"],
        textposition = "top center"
    )
    fig_risk.update_layout(
        template= "plotly_white",
        xaxis_title = "Annualized Volatility (%) — [Risk]",
        yaxis_title = "Period Return (%) — [Reward]"
    )
    st.plotly_chart(fig_risk, use_container_width=True)

    # ==========================================
    # 9.Underwater Chart
    # ==========================================

    peak = df["Close"].cummax()
    st.subheader(f"🌊{ticker} Historical Drawdown (Underwater chart)")
    drawdown = ((df["Close"] - peak) / peak) * 100
    fig_drawdown = go.Figure()
    fig_drawdown.add_scatter(
        x = df.index,
        y = drawdown,
        mode = "lines",
        name = f"{ticker} Drawdown",
        fill="tozeroy"
    )
    fig_drawdown.update_layout(
        template = "plotly_white",
        xaxis_title = "Date",
        yaxis_title = "Drawdown(%)"
    )
    st.plotly_chart(fig_drawdown, use_container_width=True)

    # ==========================================
    # The Automated Factual Research Summary
    # ==========================================
    diff = abs(main_metrics["Period Return"]- bench_period_return) * 100
    if main_metrics["Period Return"] >= bench_period_return:
        perf_status = f"Outperformed {benchmark} by {diff:.2f} percentage points"
    else:
        perf_status = f"underperformed {benchmark} by {diff:.2f} percentage points"

    if beta > 1.0:
        beta_status = "more volatile than the general market (aggressive profile)"
    else:
        beta_status = "less volatile than the general market (defensive profile)"

    summary_text = f"""
Between **{start_date}** and **{end_date}**, **{company_name} ({ticker})** generated a total return of **{main_metrics['Period Return'] * 100:.2f}%**, which {perf_status}.

Over the same period, the stock registered an annualized volatility of **{main_metrics['Annualized Volatility'] * 100:.2f}%** and experienced a maximum drawdown of **{main_metrics['Max Drawdown'] * 100:.2f}%**. With a market Beta of **{beta:.2f}**, the security was historically {beta_status}.
"""
    st.subheader("📝 Executive Research Summary")
    st.info(summary_text)