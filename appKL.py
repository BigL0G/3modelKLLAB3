import streamlit as st
import pandas as pd

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
    """Load and preprocess the violations dataset."""
    try:
        df = pd.read_csv("vilnius_data.zip")

        if "time" in df.columns:
            df["time"] = pd.to_datetime(df["time"], errors="coerce")

        return df
    except FileNotFoundError:
        st.error("Error: 'violations_cleaned.csv' not found. Please upload it together with app.py.")
        return pd.DataFrame()


def simplify_violation(v):
    """Group detailed violation text into simpler categories for presentation."""
    if pd.isna(v):
        return "other"

    v = str(v).lower()

    if "not paid" in v or "payment" in v:
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


# Load data
df = load_data()
if df.empty:
    st.stop()

# Extra columns for analysis
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

filtered_df = df.copy()

if "time" in df.columns:
    min_date = df["time"].min()
    max_date = df["time"].max()

    if pd.notna(min_date) and pd.notna(max_date):
        date_range = st.sidebar.date_input(
            "Select Date Range",
            value=(min_date.date(), max_date.date()),
            min_value=min_date.date(),
            max_value=max_date.date()
        )

        if len(date_range) == 2:
            start_date, end_date = date_range
            mask = (filtered_df["time"].dt.date >= start_date) & (filtered_df["time"].dt.date <= end_date)
            filtered_df = filtered_df.loc[mask]

if "is_electric" in filtered_df.columns:
    ev_options = st.sidebar.multiselect(
        "Vehicle Type (Electric)",
        options=filtered_df["is_electric"].dropna().unique(),
        default=filtered_df["is_electric"].dropna().unique()
    )
    filtered_df = filtered_df[filtered_df["is_electric"].isin(ev_options)]

# -----------------------------------------------------------------------------
# MAIN DASHBOARD LAYOUT
# -----------------------------------------------------------------------------
st.title("🚗 Vilnius Parking & Traffic Violations")
st.markdown("Analysis of administrative road traffic offenses recorded in Vilnius City.")

# Modify/add tabs here. This is the main place for your part.
tab1, tab2, tab3, tab4 = st.tabs([
    "Overview Metrics",
    "Geospatial Map",
    "My 3 Questions",
    "Grid Hotspots"
])

# -----------------------------------------------------------------------------
# TAB 1: OVERVIEW METRICS
# -----------------------------------------------------------------------------
with tab1:
    st.header("Overview")

    total_count = filtered_df.shape[0]

    if "longitude" in filtered_df.columns:
        missing_count = filtered_df["longitude"].isna().sum()
        missing_pct = round((missing_count / total_count) * 100, 2) if total_count > 0 else 0
    else:
        missing_count = "N/A"
        missing_pct = "N/A"

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Violations Recorded", f"{total_count:,}")
    col2.metric("Missing Coordinates (%)", f"{missing_pct}%", delta=f"{missing_count} rows", delta_color="inverse")

    if "is_towed" in filtered_df.columns:
        towed_count = filtered_df["is_towed"].sum()
    else:
        towed_count = 0
    col3.metric("Total Vehicles Towed", f"{towed_count:,}")

    st.divider()
    st.subheader("Violations Over Time")

    if "time" in filtered_df.columns:
        time_df = filtered_df.dropna(subset=["time"]).groupby(filtered_df["time"].dt.date).size().reset_index(name="count")
        time_df = time_df.rename(columns={"time": "date"}).set_index("date")
        st.line_chart(time_df["count"])
    else:
        st.info("Time column is needed for this chart.")

# -----------------------------------------------------------------------------
# TAB 2: GEOSPATIAL MAP
# -----------------------------------------------------------------------------
with tab2:
    st.header("Geospatial Distribution of Violations")

    if "latitude" in filtered_df.columns and "longitude" in filtered_df.columns:
        map_df = filtered_df.dropna(subset=["latitude", "longitude"]).copy()

        # The dataset appears to have latitude and longitude reversed, so this corrects it.
        map_df = map_df.rename(columns={"latitude": "longitude", "longitude": "latitude"})

        agg_map_df = map_df.groupby(["latitude", "longitude"]).size().reset_index(name="violation_count")
        st.caption(f"Aggregated map showing {len(agg_map_df):,} unique coordinate areas.")

        st.map(agg_map_df, latitude="latitude", longitude="longitude", size="violation_count")
    else:
        st.info("Map requires parsed 'latitude' and 'longitude' columns.")

# -----------------------------------------------------------------------------
# TAB 3: MY 3 MOST INTERESTING QUESTIONS
# -----------------------------------------------------------------------------
with tab3:
    st.header("My Part: 3 Most Interesting Questions")
    st.markdown(
        "I shortened my original questions into three presentation-friendly questions. "
        "The goal is to show patterns, changes over time, and repeat behavior."
    )

    if "violation_simple" not in filtered_df.columns:
        st.warning("This tab needs a 'violation' column so categories can be created.")
    else:
        # ------------------------------------------------------------------
        # QUESTION 1: PARETO RULE
        # ------------------------------------------------------------------
        st.subheader("1. Does the Pareto rule hold — do the top 3 types cover about 90%?")

        violation_counts = filtered_df["violation_simple"].value_counts().reset_index()
        violation_counts.columns = ["violation_type", "count"]

        total_violations = int(violation_counts["count"].sum())
        top3_total = int(violation_counts.head(3)["count"].sum())
        top3_pct = round((top3_total / total_violations) * 100, 2) if total_violations > 0 else 0

        c1, c2, c3 = st.columns(3)
        c1.metric("Total violations", f"{total_violations:,}")
        c2.metric("Top 3 violations", f"{top3_total:,}")
        c3.metric("Top 3 share", f"{top3_pct}%")

        if top3_pct >= 85:
            st.success("The Pareto-style pattern mostly holds: a small number of categories explain most violations.")
        else:
            st.info("The top 3 categories are important, but they do not fully dominate after the selected filters.")

        st.bar_chart(violation_counts.head(10).set_index("violation_type")["count"])
        st.dataframe(violation_counts.head(10), use_container_width=True)

        st.divider()

        # ------------------------------------------------------------------
        # QUESTION 2: DOMINANT TYPE SHIFT + FASTEST GROWING TYPE
        # ------------------------------------------------------------------
        st.subheader("2. Has the dominant type shifted, and which type is growing fastest?")

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

                pivot_counts = yearly_counts.pivot(index="year", columns="violation_simple", values="count").fillna(0)
                st.line_chart(pivot_counts)

                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Dominant type by year**")
                    st.dataframe(dominant_per_year, use_container_width=True)

                with c2:
                    st.markdown("**Fastest proportional growth**")
                    growth_rows = []
                    for violation_type in pivot_counts.columns:
                        series = pivot_counts[violation_type]
                        nonzero = series[series > 0]
                        if len(nonzero) >= 2:
                            first_year = nonzero.index.min()
                            last_year = nonzero.index.max()
                            first_value = nonzero.loc[first_year]
                            last_value = nonzero.loc[last_year]
                            growth_pct = ((last_value - first_value) / first_value) * 100
                            growth_rows.append({
                                "violation_type": violation_type,
                                "first_year": int(first_year),
                                "last_year": int(last_year),
                                "first_count": int(first_value),
                                "last_count": int(last_value),
                                "growth_%": round(growth_pct, 2)
                            })

                    growth_df = pd.DataFrame(growth_rows).sort_values("growth_%", ascending=False) if growth_rows else pd.DataFrame()
                    if not growth_df.empty:
                        st.dataframe(growth_df.head(5), use_container_width=True)
                    else:
                        st.info("Not enough yearly data to calculate growth.")
            else:
                st.info("Not enough yearly data after filtering.")
        else:
            st.info("This question requires a valid 'time' column.")

        st.divider()

        # ------------------------------------------------------------------
        # QUESTION 3: REPEAT VIOLATIONS + CLUSTERING
        # ------------------------------------------------------------------
        st.subheader("3. How common are repeat violations, and do they cluster by hour or location?")

        if "lic_plate_format" in filtered_df.columns:
            plate_df = filtered_df.dropna(subset=["lic_plate_format"]).copy()

            # Exclude obviously masked/anonymized placeholder plates when possible.
            clean_plate_df = plate_df[~plate_df["lic_plate_format"].astype(str).str.contains("X", na=False)]

            plate_counts = clean_plate_df["lic_plate_format"].value_counts()
            repeat_plates = plate_counts[plate_counts > 1]
            repeat_df = clean_plate_df[clean_plate_df["lic_plate_format"].isin(repeat_plates.index)]

            unique_plates = clean_plate_df["lic_plate_format"].nunique()
            repeat_record_count = len(repeat_df)
            repeat_plate_share = round((len(repeat_plates) / unique_plates) * 100, 2) if unique_plates > 0 else 0

            c1, c2, c3 = st.columns(3)
            c1.metric("Unique plate formats", f"{unique_plates:,}")
            c2.metric("Repeat violation records", f"{repeat_record_count:,}")
            c3.metric("Repeat plate share", f"{repeat_plate_share}%")

            st.caption(
                "Important: because plate values may be anonymized, this should be explained as repeat records, "
                "not guaranteed real-world repeat offenders."
            )

            if "hour" in repeat_df.columns and not repeat_df.empty:
                repeat_by_hour = repeat_df["hour"].value_counts().sort_index()
                st.markdown("**Repeat violations by hour**")
                st.bar_chart(repeat_by_hour)

            if {"latitude", "longitude"}.issubset(repeat_df.columns) and not repeat_df.empty:
                repeat_map_df = repeat_df.dropna(subset=["latitude", "longitude"]).copy()
                repeat_map_df = repeat_map_df.rename(columns={"latitude": "longitude", "longitude": "latitude"})
                repeat_locations = (
                    repeat_map_df.groupby(["latitude", "longitude"])
                    .size()
                    .reset_index(name="repeat_count")
                    .sort_values("repeat_count", ascending=False)
                )

                st.markdown("**Top repeat-violation locations**")
                st.map(repeat_locations.head(200), latitude="latitude", longitude="longitude", size="repeat_count")
                st.dataframe(repeat_locations.head(10), use_container_width=True)
        else:
            st.info("Repeat analysis requires the 'lic_plate_format' column.")

    st.divider()
    st.subheader("Short 2-minute speaking script")
    st.markdown(
        """
        **First**, I checked whether a Pareto-style rule holds. The idea is to see whether just three violation types explain almost all cases.  
        **Second**, I compared categories across years to see whether the leading violation type changed and which category grew the fastest proportionally.  
        **Third**, I looked at repeat violation records and whether they cluster by hour or location. I am careful with this point because plate formats may be anonymized, so I describe them as repeat records rather than guaranteed repeat offenders.
        """
    )

# -----------------------------------------------------------------------------
# TAB 4: GRID HOTSPOTS
# -----------------------------------------------------------------------------
with tab4:
    st.header("Grid Hotspot Analysis")
    st.markdown(
        "This tab checks whether locations are exact points or approximate block-level coordinates. "
        "If many violations share the same coordinate or same grid cell, the map should be interpreted as hotspot zones."
    )

    if "latitude" in filtered_df.columns and "longitude" in filtered_df.columns:
        grid_df = filtered_df.dropna(subset=["latitude", "longitude"]).copy()
        grid_df = grid_df.rename(columns={"latitude": "longitude", "longitude": "latitude"})

        if grid_df.empty:
            st.info("No coordinate data available after filtering.")
        else:
            exact_counts = (
                grid_df.groupby(["latitude", "longitude"])
                .size()
                .reset_index(name="violation_count")
                .sort_values("violation_count", ascending=False)
            )

            total_points = len(grid_df)
            unique_points = len(exact_counts)
            top_point_count = int(exact_counts["violation_count"].max())
            repeated_points = int((exact_counts["violation_count"] > 1).sum())

            c1, c2, c3 = st.columns(3)
            c1.metric("Rows with coordinates", f"{total_points:,}")
            c2.metric("Unique coordinate points", f"{unique_points:,}")
            c3.metric("Most repeated coordinate", f"{top_point_count:,} violations")

            st.write(
                f"There are **{repeated_points:,}** coordinate points that appear more than once. "
                "This suggests the locations may sometimes represent approximate blocks instead of exact car positions."
            )

            st.dataframe(exact_counts.head(10), use_container_width=True)

            st.divider()
            st.subheader("Grid-based hotspot map")

            grid_size = st.slider(
                "Grid cell size in degrees (bigger = wider blocks)",
                min_value=0.001,
                max_value=0.010,
                value=0.003,
                step=0.001
            )

            grid_df["lat_grid"] = (grid_df["latitude"] / grid_size).round() * grid_size
            grid_df["lon_grid"] = (grid_df["longitude"] / grid_size).round() * grid_size

            grid_counts = (
                grid_df.groupby(["lat_grid", "lon_grid"])
                .size()
                .reset_index(name="violation_count")
                .sort_values("violation_count", ascending=False)
            )

            st.caption(f"Vilnius is split into {len(grid_counts):,} grid cells using the selected grid size.")

            st.map(
                grid_counts.rename(columns={"lat_grid": "latitude", "lon_grid": "longitude"}),
                latitude="latitude",
                longitude="longitude",
                size="violation_count"
            )

            st.subheader("Hottest grid cells")
            st.dataframe(grid_counts.head(10), use_container_width=True)
    else:
        st.info("Grid analysis requires parsed 'latitude' and 'longitude' columns.")
