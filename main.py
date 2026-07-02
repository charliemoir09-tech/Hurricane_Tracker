import pandas as pd
import streamlit as st
import os
import plotly.graph_objects as go


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
    df["ISO_TIME"] = pd.to_datetime(df["ISO_TIME"], format="%Y-%m-%d %H:%M:%S", errors="coerce")

    return df

st.title("🌪 Hurricane Tracker")

#step 2: Pick ONE storm (for now Tropical storm BERYL- SID= 2024181N09320)

df = load_data()
print (df.head())

target_sid = "2024181N09320"

storm = df[df["SID"] == target_sid].sort_values(by="ISO_TIME")

st.subheader("Selected Storm Data")
st.subheader("Storm Name: Tropical Storm BERYL | SID:2024181N09320")

# Replace: st.write(storm)

storm_clean = storm.dropna(subset=["LAT", "LON"]).reset_index(drop=True)

if storm_clean.empty:
    st.warning("No valid track data for this storm.")
else:
    # Slider to step through the storm's timeline
    idx = st.slider(
        "Track position",
        min_value=0,
        max_value=len(storm_clean) - 1,
        value=0,
        format=""
    )

    current = storm_clean.iloc[idx]

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
