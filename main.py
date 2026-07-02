import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
from datetime import timedelta


URL = "https://data.humdata.org/dataset/96b309bf-cedb-4f63-8ca3-eb56cdcae876/resource/d1b9b02a-53c7-4134-ada5-234efd2efec2/download/ibtracs_all_list_v04r01.csv"

LOCAL_PATH = "2_ibtracs_all_list_v04r01.csv"


def download_if_needed():
    if not os.path.exists(LOCAL_PATH):
        st.info("Downloading IBTrACS dataset (first time only)...")
        df = pd.read_csv(URL, low_memory=False)
        df.to_csv(LOCAL_PATH, index=False)
    else:
        df = pd.read_csv(LOCAL_PATH, low_memory=False)

    return df
    
@st.cache_data
def load_data():
    df = download_if_needed()

    #Clean bad header row
    df = df[df["SID"] != "sid"].copy()

    # Convert types FIRST
    df["LAT"] = pd.to_numeric(df["LAT"], errors="coerce")
    df["LON"] = pd.to_numeric(df["LON"], errors="coerce")
    df["ISO_TIME"] = pd.to_datetime(df["ISO_TIME"], format="%d/%m/%Y %H:%M", errors="coerce")
 
    return df

st.title("🌪 Hurricane Tracker")

#step 2: Pick ONE storm (for now Tropical storm BERYL- SID= 2024181N09320)

df = load_data()

target_sid = "2024181N09320"

storm = df[df["SID"] == target_sid].sort_values(by="ISO_TIME")

st.subheader("Selected Storm Data")
st.subheader("Storm Name: Tropical Storm BERYL | SID:2024181N09320")

# Replace: st.write(storm)

storm_clean = storm.dropna(subset=["LAT", "LON", "ISO_TIME"]).reset_index(drop=True)

if storm_clean.empty:
    st.warning("No valid track data for this storm.")
else:
    # Time bounds for the slider, as native Python datetimes
    start_time = storm_clean["ISO_TIME"].min().to_pydatetime()
    end_time = storm_clean["ISO_TIME"].max().to_pydatetime()

    # Labels showing the full range of the storm, above the slider
    label_col1, label_col2 = st.columns(2)
    with label_col1:
        st.caption(f"Start: {start_time.strftime('%b %d, %Y %H:%M UTC')}")
    with label_col2:
        st.markdown(
            f"<div style='text-align: right; font-size: 0.85rem; color: gray;'>"
            f"End: {end_time.strftime('%b %d, %Y %H:%M UTC')}</div>",
            unsafe_allow_html=True,
        )

    # Slider operates on actual datetimes; the thumb label is formatted
    # to show the currently-selected time as you drag it
    selected_time = st.slider(
        "Track position",
        min_value=start_time,
        max_value=end_time,
        value=start_time,
        step=timedelta(hours=3),
        format="MMM DD, YYYY - HH:mm",
        label_visibility="collapsed",
    )

    # Snap to the nearest real observation to the selected slider time
    nearest_idx = (storm_clean["ISO_TIME"] - selected_time).abs().idxmin()
    current = storm_clean.loc[nearest_idx]

    fig = go.Figure()

    # Full track as a line, for context
    fig.add_trace(go.Scattergeo(
        lon=storm_clean["LON"],
        lat=storm_clean["LAT"],
        mode="lines",
        line=dict(width=2, color="gray"),
        name="Full track"
    ))

    # The moving dot at the selected timestamp
    fig.add_trace(go.Scattergeo(
        lon=[current["LON"]],
        lat=[current["LAT"]],
        mode="markers",
        marker=dict(size=14, color="red"),
        name="Current position"
    ))

    fig.update_layout(
        geo=dict(
            projection_type="natural earth",
            showland=True,
            landcolor="rgb(235, 235, 235)",
            showcountries=True,
            showcoastlines=True,
            fitbounds="locations",
        ),
        height=500,
        margin=dict(l=0, r=0, t=0, b=0),
    )

    st.plotly_chart(fig, use_container_width=True)
    st.write(f"**Time:** {current['ISO_TIME']}  |  **Lat:** {current['LAT']}  |  **Lon:** {current['LON']}")

st.write("Nature: Tropical Storm")
st.write("Basin: North Atlantic")
st.write("Subbasin: North Atlantic and Carribean")
st.write("Season: 2024")


#USE ctrl_(shift)_b TO START PROGRAM
