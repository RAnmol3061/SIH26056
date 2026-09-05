import sqlite3

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

import streamlit as st

# Page configuration
st.set_page_config(page_title="National Airfare Index (APIx)", layout="wide")
st.title("✈️ Real-time Airfare Price Index & Analytics Dashboard")


# 1. Ingest Data from SQLite
@st.cache_data
def load_data():
    conn = sqlite3.connect("airfares.db")
    query = """
        SELECT origin, dest, carrier_name, travel_date, 
               advance_days, base_fare, taxes, total_fare, 
               fare_class, scrape_date
        FROM fares
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    # Precompute route for consistent filtering
    df["route"] = df["origin"] + "-" + df["dest"]
    return df


df = load_data()

if df.empty:
    st.warning("No fare data found in the database. Please run your scraper first.")
    st.stop()

# 2. Sidebar Filters
st.sidebar.header("Filter Settings")
route_list = sorted(df["route"].unique())
selected_route = st.sidebar.selectbox("Select Route", route_list)

# Filtered slices for price trends
filtered_df = df[df["route"] == selected_route]

# 3. Main Layout Split: Left for Price Trends (70%), Right for Airfare Index (30%)
main_col, index_col = st.columns([2.3, 1], gap="medium")

with main_col:
    st.subheader(f"Market Trends: {selected_route}")

    # KPI Display
    col1, col2, col3, col4 = st.columns(4)
    min_fare = filtered_df["total_fare"].min() if not filtered_df.empty else 0
    avg_fare = filtered_df["total_fare"].mean() if not filtered_df.empty else 0
    max_fare = filtered_df["total_fare"].max() if not filtered_df.empty else 0
    tracked_flights = len(filtered_df)

    col1.metric("Lowest Fare", f"₹{int(min_fare):,}")
    col2.metric("Average Fare", f"₹{int(avg_fare):,}")
    col3.metric("Highest Fare", f"₹{int(max_fare):,}")
    col4.metric("Data Points", f"{int(tracked_flights):,}")

    # Multi-Metric Visualizations via Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "Lead-Time Curves",
            "Sector Heatmap",
            "Carrier Pricing",
            "Scatter View",
            "Raw Feed",
        ]
    )

    with tab1:
        st.markdown(f"**Lead-Time Fare Trajectory for {selected_route}**")
        fig1, ax1 = plt.subplots(figsize=(8, 4))
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
        st.markdown("**Sector-wise Average Fare Matrix (All Routes)**")
        matrix_data = df.pivot_table(
            index="route",
            columns="travel_date",
            values="total_fare",
            aggfunc="mean",
        )
        fig2, ax2 = plt.subplots(figsize=(8, 3.5))
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
        st.markdown(f"**Carrier Fare Dispersion: {selected_route}**")
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
        st.markdown("**Route Fare Distribution vs Advance Days**")
        fig4, ax4 = plt.subplots(figsize=(8, 4))
        sns.scatterplot(
            data=df,
            x="advance_days",
            y="total_fare",
            hue="carrier_name",
            style="route",
            s=80,
            ax=ax4,
        )
        ax4.set_xlabel("Advance Days")
        ax4.set_ylabel("Total Fare (₹)")
        ax4.grid(True, linestyle="--", alpha=0.5)
        st.pyplot(fig4)
        plt.close(fig4)

    with tab5:
        st.markdown("**Live Extraction Feed**")
        st.dataframe(
            filtered_df.drop(columns=["route"]).sort_values(
                by=["advance_days", "total_fare"]
            ),
            use_container_width=True,
        )

with index_col:
    st.subheader("📈 Airfare Index (APIx)")
    st.markdown(
        "Laspeyres-style weighted market index tracking price movement[cite: 2]."
    )

    # Dynamic Index Integration Logic
    available_dates = sorted(df["scrape_date"].unique())

    if len(available_dates) > 0:
        default_base = available_dates[0]
        default_current = available_dates[-1]

        base_date = st.selectbox("Base Date (Baseline)", available_dates, index=0)
        current_date = st.selectbox(
            "Current Date (Comparison)", available_dates, index=len(available_dates) - 1
        )

        # Import compute_index function from index_calc module
        try:
            from index_calc import compute_index

            index_data = compute_index(current_date=current_date, base_date=base_date)

            # Display Overall Index Metric with Delta
            overall = index_data.get("overall_index")
            if overall:
                delta_val = round(overall - 100.0, 2)
                st.metric(
                    label=f"Overall Index ({current_date} vs {base_date})",
                    value=f"{overall}",
                    delta=f"{delta_val}% vs Base",
                )
            else:
                st.warning(
                    "Insufficient data to compute overall index for selected date range."
                )

            st.markdown("---")
            st.markdown("### Route Breakdown")
            routes_info = index_data.get("routes", {})

            for r_key, r_val in routes_info.items():
                with st.container(border=True):
                    st.markdown(f"**Route: `{r_key}`**")
                    if "error" in r_val:
                        st.caption(f"Status: {r_val['error']}")
                    else:
                        st.text(f"Current Fare: ₹{r_val.get('total_fare', 0):,.2f}")
                        st.text(f"Route Index: {r_val.get('route_index', 0)}")
        except ImportError:
            st.error(
                "Could not import `compute_index` from `index_calc.py`. Ensure both files share the same directory."
            )
    else:
        st.info("Record a scrape session to view index movements.")
