import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Set page config for wide layout
st.set_page_config(page_title="SuperStore Dashboard", layout="wide")

# ---- Load Data ----
@st.cache_data
def load_data():
    df = pd.read_excel("Sample - Superstore.xlsx", engine="openpyxl")
    if not pd.api.types.is_datetime64_any_dtype(df["Order Date"]):
        df["Order Date"] = pd.to_datetime(df["Order Date"])
    return df

df_original = load_data()

# ---- Sidebar Filters ----
st.sidebar.title("Filters")

# Region Filter (Multi-select option)
all_regions = sorted(df_original["Region"].dropna().unique())
selected_regions = st.sidebar.multiselect("Select Region(s)", options=["All"] + all_regions, default=["All"])

df_filtered = df_original.copy()
if selected_regions != ["All"]:
    df_filtered = df_filtered[df_filtered["Region"].isin(selected_regions)]

# State Filter (Multi-select option)
all_states = sorted(df_filtered["State"].dropna().unique())
selected_states = st.sidebar.multiselect("Select State(s)", options=["All"] + all_states, default=["All"])
if selected_states != ["All"]:
    df_filtered = df_filtered[df_filtered["State"].isin(selected_states)]

# Category Filter
all_categories = sorted(df_filtered["Category"].dropna().unique())
selected_category = st.sidebar.selectbox("Select Category", options=["All"] + all_categories)
if selected_category != "All":
    df_filtered = df_filtered[df_filtered["Category"] == selected_category]

# Sub-Category Filter
all_subcats = sorted(df_filtered["Sub-Category"].dropna().unique())
selected_subcat = st.sidebar.selectbox("Select Sub-Category", options=["All"] + all_subcats)
if selected_subcat != "All":
    df_filtered = df_filtered[df_filtered["Sub-Category"] == selected_subcat]

# ---- Sidebar Date Range ----
if df_filtered.empty:
    min_date, max_date = df_original["Order Date"].min(), df_original["Order Date"].max()
else:
    min_date, max_date = df_filtered["Order Date"].min(), df_filtered["Order Date"].max()

start_date = st.sidebar.date_input("Start Date", value=min_date, min_value=min_date, max_value=max_date)
end_date = st.sidebar.date_input("End Date", value=max_date, min_value=min_date, max_value=max_date)

if start_date > end_date:
    st.sidebar.error("Start Date must be earlier than End Date.")

df = df_filtered[(df_filtered["Order Date"] >= pd.to_datetime(start_date)) & (df_filtered["Order Date"] <= pd.to_datetime(end_date))]

# ---- KPI Calculation ----
if df.empty:
    total_sales, total_quantity, total_profit, margin_rate = 0, 0, 0, 0
else:
    total_sales = df["Sales"].sum()
    total_quantity = df["Quantity"].sum()
    total_profit = df["Profit"].sum()
    margin_rate = total_profit / total_sales if total_sales != 0 else 0

# ---- Store Selected KPI in Session State ----
if "selected_kpi" not in st.session_state:
    st.session_state.selected_kpi = "Sales"  # Default to Sales

# ---- Custom CSS for KPI Tiles ----
st.markdown(
    """
    <style>
    .stButton>button {
        background-color: #1E90FF;
        color: white;
        font-size: 18px;
        font-weight: bold;
        border-radius: 10px;
        padding: 10px 20px;
        border: 2px solid #0056b3;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #0056b3;
        color: #ffffff;
        border: 2px solid #003f7f;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---- KPI Display (Buttons for Filtering) ----
st.subheader("SuperStore KPI Dashboard")

kpi_data = {
    "Sales": f"${total_sales:,.2f}",
    "Quantity": f"{total_quantity:,.0f}",
    "Profit": f"${total_profit:,.2f}",
    "Margin Rate": f"{(margin_rate * 100):,.2f}%"
}

kpi_cols = st.columns(4)
for i, (kpi, value) in enumerate(kpi_data.items()):
    is_selected = "kpi-selected" if st.session_state.selected_kpi == kpi else ""
    with kpi_cols[i]:
        if st.button(
            label=f"""**{kpi}** 
                    \n **{value}**""",
            key=kpi,
            help=f"Click to filter by {kpi}",
        ):
            st.session_state.selected_kpi = kpi  

# Display Selected KPI
st.write(f"### Selected KPI: {st.session_state.selected_kpi}")

# ---- Data Processing for Charts ----
if df.empty:
    st.warning("No data available for the selected filters and date range.")
else:
    daily_grouped = df.groupby("Order Date").agg({"Sales": "sum", "Quantity": "sum", "Profit": "sum"}).reset_index()
    daily_grouped["Margin Rate"] = daily_grouped["Profit"] / daily_grouped["Sales"].replace(0, 1)

    city_grouped = df.groupby("City").agg({"Sales": "sum", "Quantity": "sum", "Profit": "sum"}).reset_index()
    city_grouped["Margin Rate"] = city_grouped["Profit"] / city_grouped["Sales"].replace(0, 1)

    city_grouped.sort_values(by=st.session_state.selected_kpi, ascending=False, inplace=True)
    top_10_city = city_grouped.head(10)

    product_grouped = df.groupby("Product Name").agg({"Sales": "sum", "Quantity": "sum", "Profit": "sum"}).reset_index()
    product_grouped["Margin Rate"] = product_grouped["Profit"] / product_grouped["Sales"].replace(0, 1)

    product_grouped.sort_values(by=st.session_state.selected_kpi, ascending=False, inplace=True)
    top_10_product = product_grouped.head(10)

    # ---- Charts ----
    fig_line = px.line(
        daily_grouped,
        x="Order Date",
        y=st.session_state.selected_kpi,
        title=f"{st.session_state.selected_kpi} Over Time",
        labels={"Order Date": "Date", st.session_state.selected_kpi: st.session_state.selected_kpi},
        template="plotly_white"
    )
    fig_line.update_layout(height=400)
    st.plotly_chart(fig_line, use_container_width=True)
    
    col_left, col_right = st.columns(2)

    with col_left:
        fig_bar = px.bar(
            top_10_city,
            x=st.session_state.selected_kpi,
            y="City",
            orientation="h",
            title=f"Top 10 Cities by {st.session_state.selected_kpi}",
            labels={st.session_state.selected_kpi: st.session_state.selected_kpi, "City": "City"},
            color=st.session_state.selected_kpi,
            color_continuous_scale="Blues",
            template="plotly_white",
        )
        fig_bar.update_layout(height=400, yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_bar, use_container_width=True)
       
    with col_right:
        fig_bar = px.bar(
            top_10_product,
            x=st.session_state.selected_kpi,
            y="Product Name",
            orientation="h",
            title=f"Top 10 Products by {st.session_state.selected_kpi}",
            labels={st.session_state.selected_kpi: st.session_state.selected_kpi, "Product Name": "Product"},
            color=st.session_state.selected_kpi,
            color_continuous_scale="Blues",
            template="plotly_white",
        )
        fig_bar.update_layout(height=400, yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_bar, use_container_width=True)
