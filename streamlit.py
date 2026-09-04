import sqlite3

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st

st.set_page_config(page_title="National Airfare Index (APIx)", layout="wide")
st.title("✈️ Real-time Airfare Price Index")


# 1. Ingest Data from SQLite
@st.cache_data
def load_data():
    conn = sqlite3.connect("airfares.db")
    query = """
        SELECT origin, dest, carrier_name, travel_date, 
               advance_days, total_fare, flight_count 
        FROM fares
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    # Precompute route for consistent filtering
    df["route"] = df["origin"] + "-" + df["dest"]
    return df


df = load_data()

# 2. Sidebar Filters
st.sidebar.header("Filter Settings")
route_list = sorted(df["route"].unique())
selected_route = st.sidebar.selectbox("Select Route", route_list)

# Filtered slices
filtered_df = df[df["route"] == selected_route]

# 3. KPI Display
col1, col2, col3, col4 = st.columns(4)
min_fare = filtered_df["total_fare"].min()
avg_fare = filtered_df["total_fare"].mean()
max_fare = filtered_df["total_fare"].max()
tracked_flights = filtered_df["flight_count"].sum()

col1.metric("Lowest Fare", f"₹{int(min_fare):,}")
col2.metric("Average Fare", f"₹{int(avg_fare):,}")
col3.metric("Highest Fare", f"₹{int(max_fare):,}")
col4.metric("Tracked Flight Volume", f"{int(tracked_flights):,}")

# 4. Multi-Metric Visualizations via Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "📈 Lead-Time Curves",
        "🗺️ Sector Heatmap",
        "📦 Carrier Pricing",
        "🎯 Frequency vs. Fare",
        "📋 Raw Feed",
    ]
)

with tab1:
    st.subheader(f"Lead-Time Fare Trajectory: {selected_route}")
    fig1, ax1 = plt.subplots(figsize=(10, 4.5))
    sns.lineplot(
        data=filtered_df,
        x="advance_days",
        y="total_fare",
        hue="carrier_name",
        marker="o",
        ax=ax1,
    )
    ax1.set_xlabel("Days Prior to Departure (Lead Time)")
    ax1.set_ylabel("Total Fare (₹)")
    ax1.grid(True, linestyle="--", alpha=0.5)
    st.pyplot(fig1)
    plt.close(fig1)

with tab2:
    st.subheader("Sector-wise Average Fare Matrix (All Routes)")
    matrix_data = df.pivot_table(
        index="route",
        columns="travel_date",
        values="total_fare",
        aggfunc="mean",
    )
    fig2, ax2 = plt.subplots(figsize=(10, 3.5))
    sns.heatmap(
        matrix_data,
        annot=True,
        fmt=".0f",
        cmap="YlOrRd",
        cbar_kws={"label": "Avg Fare (₹)"},
        ax=ax2,
    )
    ax2.set_xlabel("Travel Date")
    ax2.set_ylabel("Route")
    st.pyplot(fig2)
    plt.close(fig2)

with tab3:
    st.subheader(f"Carrier Fare Dispersion: {selected_route}")
    fig3, ax3 = plt.subplots(figsize=(8, 4))
    sns.boxplot(
        data=filtered_df,
        x="carrier_name",
        y="total_fare",
        palette="Set2",
        ax=ax3,
    )
    sns.stripplot(
        data=filtered_df,
        x="carrier_name",
        y="total_fare",
        color="black",
        alpha=0.6,
        jitter=0.2,
        ax=ax3,
    )
    ax3.set_xlabel("Carrier")
    ax3.set_ylabel("Total Fare (₹)")
    st.pyplot(fig3)
    plt.close(fig3)

with tab4:
    st.subheader("Route Frequency vs. Airfare Impact (Network-wide)")
    fig4, ax4 = plt.subplots(figsize=(10, 4.5))
    sns.scatterplot(
        data=df,
        x="flight_count",
        y="total_fare",
        hue="carrier_name",
        style="route",
        s=80,
        ax=ax4,
    )
    ax4.set_xlabel("Daily Flight Count Available")
    ax4.set_ylabel("Total Fare (₹)")
    ax4.grid(True, linestyle="--", alpha=0.5)
    st.pyplot(fig4)
    plt.close(fig4)

with tab5:
    st.subheader("Live Extraction Feed")
    st.dataframe(
        filtered_df.drop(columns=["route"]).sort_values(
            by=["advance_days", "total_fare"]
        ),
        use_container_width=True,
    )
