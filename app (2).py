import streamlit as st
import pandas as pd
import plotly.express as px

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Vilnius Traffic Violations Dashboard",
    page_icon="🚗",
    layout="wide"
)

# -----------------------------------------------------------------------------
# DATA LOADING & PREPROCESSING
# -----------------------------------------------------------------------------
@st.cache_data
def load_data():
    """
    Loads and preprocesses the violations dataset.
    Using @st.cache_data prevents reloading the CSV on every user interaction.
    """
    try:
        df = pd.read_csv("violations_cleaned.csv")
        
        # Convert time column to datetime objects
        if 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'], errors='coerce')
            
        return df
    except FileNotFoundError:
        st.error("Error: 'violations_cleaned.csv' not found. Please ensure the file is in the same directory.")
        return pd.DataFrame() # Return empty dataframe to prevent hard crashes

# Load the data
df = load_data()

# Stop execution if data failed to load
if df.empty:
    st.stop()



# -----------------------------------------------------------------------------
# EXTRA ANALYSIS FROM "MY PART" NOTEBOOK
# -----------------------------------------------------------------------------
def simplify_violation(v):
    """Group detailed violation text into simpler categories for presentation."""
    if pd.isna(v):
        return "other"

    v = str(v).lower()

    if "not paid" in v:
        return "not_paid"
    elif "sign 332" in v:
        return "sign_332"
    elif "sign 333" in v:
        return "sign_333"
    elif "sidewalk" in v:
        return "sidewalk"
    elif "non-traffic" in v:
        return "non_traffic"
    elif "reserved" in v:
        return "reserved"
    elif "obstruct" in v:
        return "obstruction"
    elif "parking" in v:
        return "parking_general"
    elif "stopping" in v:
        return "stopping"
    else:
        return "other"

# Create columns used in the analysis tab, only if the needed raw columns exist
if "violation" in df.columns:
    df["violation_simple"] = df["violation"].apply(simplify_violation)

if "time" in df.columns:
    df["hour"] = df["time"].dt.hour
    df["year"] = df["time"].dt.year
    df["month"] = df["time"].dt.month

# -----------------------------------------------------------------------------
# SIDEBAR FILTERS
# -----------------------------------------------------------------------------
st.sidebar.header("Dashboard Filters")

# Filter by Date
min_date = df['time'].min()
max_date = df['time'].max()

# Only show date filter if time data is valid
if pd.notna(min_date) and pd.notna(max_date):
    date_range = st.sidebar.date_input(
        "Select Date Range",
        value=(min_date.date(), max_date.date()),
        min_value=min_date.date(),
        max_value=max_date.date()
    )
    
    # Apply date filter
    if len(date_range) == 2:
        start_date, end_date = date_range
        # Filter dataframe based on selection
        mask = (df['time'].dt.date >= start_date) & (df['time'].dt.date <= end_date)
        filtered_df = df.loc[mask]
    else:
        filtered_df = df
else:
    filtered_df = df

# Filter by EV status
ev_options = st.sidebar.multiselect(
    "Vehicle Type (Electric)",
    options=filtered_df['is_electric'].dropna().unique(),
    default=filtered_df['is_electric'].dropna().unique()
)
filtered_df = filtered_df[filtered_df['is_electric'].isin(ev_options)]

# -----------------------------------------------------------------------------
# MAIN DASHBOARD LAYOUT
# -----------------------------------------------------------------------------
st.title("🚗 Vilnius Parking & Traffic Violations")
st.markdown("Analysis of administrative road traffic offenses recorded in Vilnius City.")

# Create Tabs !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
tab1, tab2, tab3 = st.tabs(["Overview Metrics", "Geospatial Map", "My Analysis: 3 Key Insights"])

# --- TAB 1: OVERVIEW METRICS (As requested) ---
with tab1:
    st.header("Overview")
    
    # Calculate metrics
    total_count = filtered_df.shape[0]
    
    # Calculate missing coordinates
    if 'longitude' in filtered_df.columns:
        missing_count = filtered_df["longitude"].isna().sum()
        missing_pct = round((missing_count / total_count) * 100, 2) if total_count > 0 else 0
    else:
        missing_count = "N/A"
        missing_pct = "N/A"
        st.warning("Column 'longitude' not found in dataset. Assuming raw 'geometry_adp' is used instead.")

    # Display Metrics in columns
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(label="Total Violations Recorded", value=f"{total_count:,}")
        
    with col2:
        st.metric(label="Missing Coordinates (%)", value=f"{missing_pct}%", delta=f"{missing_count} rows", delta_color="inverse")
        
    with col3:
        towed_count = filtered_df['is_towed'].sum() if 'is_towed' in filtered_df.columns else 0
        st.metric(label="Total Vehicles Towed", value=f"{towed_count:,}")

    st.divider()
    
    # Add a time-series chart to make the first tab more visually appealing
    st.subheader("Violations Over Time")
    if 'time' in filtered_df.columns:
        # Group by Date
        time_df = filtered_df.groupby(filtered_df['time'].dt.date).size().reset_index(name='count')
        fig = px.line(time_df, x='time', y='count', title="Daily Violations Recorded", labels={'time':'Date', 'count': 'Number of Violations'})
        st.plotly_chart(fig, use_container_width=True)


# --- TAB 2: GEOSPATIAL MAP ---
with tab2:
    st.header("Geospatial Distribution of Violations")
    
    if 'latitude' in filtered_df.columns and 'longitude' in filtered_df.columns:
        # Filter out rows with missing coordinates
        map_df = filtered_df.dropna(subset=['latitude', 'longitude']).copy()
        
        # FIX: Swap latitude and longitude columns to fix the "Dubai instead of Vilnius" issue
        map_df = map_df.rename(columns={
            'latitude': 'longitude', 
            'longitude': 'latitude'
        })
        
        # AGGREGATE: Group by exact coordinates and count the number of violations
        # This reduces tens of thousands of rows down to just a few dozen/hundred unique spots
        agg_map_df = map_df.groupby(['latitude', 'longitude']).size().reset_index(name='violation_count')
        
        
        st.caption(f"Aggregated map showing {len(agg_map_df)} unique coordinate areas.")
        
        # Plot the map using the aggregated data, using 'bubble_size' to scale the dots
        st.map(
            agg_map_df,
            latitude='latitude',
            longitude='longitude'
        )
    else:
        st.info("To display the map, ensure your cleaned dataset has parsed 'latitude' and 'longitude' columns extracted from 'geometry_adp'.")

# --- TAB 3: MY PART ANALYSIS ---
with tab3:
    st.header("My Analysis: 3 Key Insights")
    st.markdown(
        "These are the three strongest points from my notebook analysis, "
        "chosen for a short 2-minute presentation."
    )

    if "violation_simple" not in filtered_df.columns:
        st.warning("The column 'violation' is needed for this analysis tab.")
    else:
        # ------------------------------------------------------------------
        # INSIGHT 1: Pareto / top violation concentration
        # ------------------------------------------------------------------
        st.subheader("1. Top violation categories do not fully dominate the dataset")

        violation_counts = filtered_df["violation_simple"].value_counts().reset_index()
        violation_counts.columns = ["violation_type", "count"]

        total_violations = violation_counts["count"].sum()
        top3_total = violation_counts.head(3)["count"].sum()
        top3_pct = round((top3_total / total_violations) * 100, 2) if total_violations > 0 else 0

        c1, c2 = st.columns([1, 2])
        with c1:
            st.metric("Top 3 category share", f"{top3_pct}%")
            st.write(
                "The Pareto principle does **not** strongly hold here. "
                "The top categories explain only part of the violations, "
                "so the problem is more diverse than just one or two causes."
            )
        with c2:
            fig_top = px.bar(
                violation_counts.head(8),
                x="violation_type",
                y="count",
                title="Most common simplified violation categories",
                labels={"violation_type": "Violation type", "count": "Number of violations"}
            )
            st.plotly_chart(fig_top, use_container_width=True)

        st.divider()

        # ------------------------------------------------------------------
        # INSIGHT 2: Dominant violation changed over time
        # ------------------------------------------------------------------
        st.subheader("2. The dominant violation type changes over the years")

        if "year" in filtered_df.columns:
            year_df = filtered_df.dropna(subset=["year"]).copy()
            year_df = year_df[year_df["violation_simple"] != "other"]

            yearly_counts = (
                year_df.groupby(["year", "violation_simple"])
                .size()
                .reset_index(name="count")
            )

            if not yearly_counts.empty:
                dominant_per_year = (
                    yearly_counts.sort_values(["year", "count"], ascending=[True, False])
                    .groupby("year")
                    .first()
                    .reset_index()
                )

                c1, c2 = st.columns([1, 2])
                with c1:
                    st.write(
                        "The leading violation type is not constant. "
                        "In some years unpaid parking is strongest, while in other years "
                        "traffic sign violations become dominant."
                    )
                    st.dataframe(dominant_per_year, use_container_width=True)
                with c2:
                    fig_year = px.line(
                        yearly_counts,
                        x="year",
                        y="count",
                        color="violation_simple",
                        markers=True,
                        title="Violation categories over time",
                        labels={"year": "Year", "count": "Number of violations", "violation_simple": "Violation type"}
                    )
                    st.plotly_chart(fig_year, use_container_width=True)
            else:
                st.info("Not enough yearly data after filtering to show this insight.")
        else:
            st.info("Year analysis requires a valid 'time' column.")

        st.divider()

        # ------------------------------------------------------------------
        # INSIGHT 3: Repeat violations need careful interpretation
        # ------------------------------------------------------------------
        st.subheader("3. Repeat violations exist, but anonymized plates make interpretation risky")

        if "lic_plate_format" in filtered_df.columns:
            plate_df = filtered_df.dropna(subset=["lic_plate_format"]).copy()

            # Remove masked/anonymized placeholder values containing X, based on notebook finding
            clean_plate_df = plate_df[~plate_df["lic_plate_format"].astype(str).str.contains("X", na=False)]

            plate_counts = clean_plate_df["lic_plate_format"].value_counts()
            repeat_plates = plate_counts[plate_counts > 1]
            repeat_df = clean_plate_df[clean_plate_df["lic_plate_format"].isin(repeat_plates.index)]

            unique_plates = clean_plate_df["lic_plate_format"].nunique()
            repeat_pct = round((len(repeat_plates) / unique_plates) * 100, 2) if unique_plates > 0 else 0

            c1, c2, c3 = st.columns(3)
            c1.metric("Unique plates", f"{unique_plates:,}")
            c2.metric("Repeat plates", f"{len(repeat_plates):,}")
            c3.metric("Repeat plate share", f"{repeat_pct}%")

            st.write(
                "Many plates appear more than once, but the dataset contains anonymized or masked plate values. "
                "Because of that, this should be presented carefully: it shows repeat records, "
                "not guaranteed real-world repeat offenders."
            )

            if "hour" in repeat_df.columns and not repeat_df.empty:
                repeat_by_hour = repeat_df["hour"].value_counts().sort_index().reset_index()
                repeat_by_hour.columns = ["hour", "count"]

                fig_hour = px.bar(
                    repeat_by_hour,
                    x="hour",
                    y="count",
                    title="Repeat violation records by hour",
                    labels={"hour": "Hour of day", "count": "Repeat violation records"}
                )
                st.plotly_chart(fig_hour, use_container_width=True)
        else:
            st.info("Repeat violation analysis requires the 'lic_plate_format' column.")

    st.divider()
    st.subheader("2-minute presentation script")
    st.markdown(
        """
        **First**, I grouped detailed violation descriptions into simpler categories. The top 3 categories do not explain everything, so violations are quite diverse.  
        **Second**, I checked how the dominant violation type changed by year. The leading category shifts over time, especially between unpaid parking and sign-related violations.  
        **Third**, I looked at repeat violations. Many plate formats appear more than once, but because some plates are anonymized, I interpret this carefully and do not claim they are definitely real repeat offenders.
        """
    )