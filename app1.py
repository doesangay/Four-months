import sys
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit import runtime
from streamlit.web import cli as stcli

# ==========================================
# 1. DATA ENGINE & COLOR CONFIG
# ==========================================
COLOR_MAP = {
    'Crossword': '#00e5ff', 'Bingo': '#df20df', 'Spin the Wheel': '#f1c40f',
    'Race 6': '#10d25f', 'Spin Roulette': '#38b284', 'Crossword Paradise': '#f06277',
    'Terdrup': '#8b5cf6', 'Pick 3': '#3b82f6', 'Lotto': '#a855f7',
    'Pick 4': '#f97316', 'Free Roll': '#0ea5e9'
}

@st.cache_data
def load_data():
    try:
        df = pd.read_csv('Online sales1.csv')
    except FileNotFoundError:
        return pd.DataFrame(), []

    product_cols = list(COLOR_MAP.keys())

    # Clean numeric data (Removing commas and quotes)
    cols_to_fix = product_cols + ['Wagers/sales']
    for col in cols_to_fix:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '').str.replace('"', ''), errors='coerce')

    # Date handling
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce', dayfirst=True)
    df = df.dropna(subset=['Date']).sort_values('Date')
    
    # Derived Columns
    df['Month'] = df['Date'].dt.month_name()
    df['Total Sales'] = df[product_cols].sum(axis=1)
    
    return df, product_cols

# ==========================================
# 2. MAIN DASHBOARD FUNCTION
# ==========================================
def main():
    st.set_page_config(page_title="AI Sales Assistant", layout="wide", page_icon="🤖")
    df, product_cols = load_data()

    if df.empty:
        st.error("⚠️ Data file not found. Please ensure 'Online sales1.csv' is available.")
        return

    st.title("🤖 AI Sales Data Assistant")
    st.markdown("Use the **Search Insights** bar at the bottom to generate custom reports and graphs instantly.")

    # Top KPI Row
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Revenue", f"${df['Total Sales'].sum():,.0f}")
    col2.metric("Best Product", df[product_cols].sum().idxmax())
    col3.metric("Avg Daily Sales", f"${df['Total Sales'].mean():,.0f}")

    # --- PERMANENT TABS FOR QUICK BROWSING ---
    tab1, tab2 = st.tabs(["📊 Performance Overview", "🗄️ Raw Data"])
    
    with tab1:
        # Standard Horizontal Bar Chart
        totals = df[product_cols].sum().sort_values(ascending=True).reset_index()
        totals.columns = ['Product', 'Sales']
        fig_total = go.Figure(go.Bar(
            x=totals['Sales'], y=totals['Product'], orientation='h',
            marker_color=[COLOR_MAP.get(p) for p in totals['Product']],
            text=totals['Sales'], texttemplate='%{text:,.0f}', textposition='outside'
        ))
        fig_total.update_layout(title="Total Revenue per Product", template="plotly_dark", height=500)
        st.plotly_chart(fig_total, use_container_width=True)

    with tab2:
        st.dataframe(df, use_container_width=True)

    st.divider()

    # ==========================================
    # 3. INTERACTIVE "PROMPT TO GRAPH" ENGINE
    # ==========================================
    st.subheader("🔍 Search & Analyze")
    user_query = st.text_input("Ask me something (e.g., 'Compare Lotto and Bingo', 'Show monthly', 'Trend analysis')", 
                               placeholder="Type your question here...")

    if user_query:
        q = user_query.lower()
        st.write("### 📢 Insight Result")

        # CASE 1: PRODUCT COMPARISON (Comparison Logic)
        if "compare" in q or "vs" in q:
            # Detect which products are in the query
            found_products = [p for p in product_cols if p.lower() in q]
            
            if len(found_products) >= 2:
                p1, p2 = found_products[0], found_products[1]
                diff = df[p1].sum() - df[p2].sum()
                winner = p1 if diff > 0 else p2
                
                st.info(f"⚖️ **Comparison:** {p1} vs {p2}. **{winner}** is higher by **${abs(diff):,.0f}** in total sales.")
                
                fig_comp = px.line(df, x='Date', y=[p1, p2], title=f"Timeline: {p1} vs {p2}",
                                   color_discrete_map={p1: COLOR_MAP[p1], p2: COLOR_MAP[p2]})
                st.plotly_chart(fig_comp, use_container_width=True)
            else:
                st.warning("Please mention at least two valid products (e.g., 'Compare Lotto and Bingo').")

        # CASE 2: MONTHLY PERFORMANCE
        elif "month" in q:
            month_data = df.groupby('Month')[product_cols].sum().reset_index()
            # Sort by total monthly sales
            month_data['Total'] = month_data[product_cols].sum(axis=1)
            best_month = month_data.loc[month_data['Total'].idxmax(), 'Month']
            
            st.success(f"📅 **Monthly Analysis:** Your strongest month is **{best_month}**.")
            
            melted = month_data.drop(columns='Total').melt(id_vars='Month')
            fig_month = px.bar(melted, x='Month', y='value', color='variable', 
                               title="Monthly Product Breakdown", barmode='group',
                               color_discrete_map=COLOR_MAP)
            fig_month.update_layout(template="plotly_dark")
            st.plotly_chart(fig_month, use_container_width=True)

        # CASE 3: TREND / MOVING AVERAGE
        elif "trend" in q or "moving average" in q:
            df['7DMA'] = df['Total Sales'].rolling(window=7).mean()
            st.info("📈 **Trendline:** Showing the 7-day moving average to smooth out daily fluctuations.")
            
            fig_trend = px.scatter(df, x='Date', y='Total Sales', title="Sales Trend & 7-Day Moving Average")
            fig_trend.add_trace(go.Scatter(x=df['Date'], y=df['7DMA'], name='7-Day Avg', line=dict(color='limegreen', width=3)))
            st.plotly_chart(fig_trend, use_container_width=True)

        # CASE 4: RISK / STRUGGLING PRODUCTS
        elif "risk" in q or "worst" in q or "low" in q:
            bottom_3 = df[product_cols].sum().sort_values().head(3)
            st.warning(f"⚠️ **Low Performance Warning:** The products **{', '.join(bottom_3.index)}** have the lowest revenue.")
            
            fig_risk = px.pie(names=bottom_3.index, values=bottom_3.values, hole=0.4, 
                              title="Revenue Share of Lowest Performers",
                              color_discrete_sequence=['#ff4b4b', '#ff7676', '#ffb1b1'])
            st.plotly_chart(fig_risk, use_container_width=True)

        else:
            st.write("🤔 I'm not sure how to answer that yet. Try asking about **'comparisons'**, **'monthly sales'**, or **'trends'**.")

# ==========================================
# 4. EXECUTION
# ==========================================
if __name__ == '__main__':
    if runtime.exists():
        main()
    else:
        sys.argv = ["streamlit", "run", sys.argv[0]]
        sys.exit(stcli.main())
        