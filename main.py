import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
from datetime import timedelta
import requests


URL = "https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.ALL.list.v04r01.csv"

LOCAL_PATH = "ibtracs.ALL.list.v04r01.csv"

IBTRACS_COLUMNS = [
    "SID", "SEASON", "NUMBER", "BASIN", "SUBBASIN", "NAME",
    "ISO_TIME", "NATURE", "LAT", "LON", "WMO_WIND", "WMO_PRES",
]

def download_if_needed():
    if not os.path.exists(LOCAL_PATH):
        TEMP_RAW_PATH = "ibtracs_raw_temp.csv"

        response = requests.get(URL, stream=True)
        response.raise_for_status()
        total_size = int(response.headers.get("content-length", 0))

        progress_bar = st.progress(0, text="Downloading IBTrACS dataset (first time only)...")
        bytes_downloaded = 0

        # Stream the full raw file to a temporary path — this is never
        # kept around long-term, just used as scratch space to read from
        with open(TEMP_RAW_PATH, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):  # 1MB chunks
                f.write(chunk)
                bytes_downloaded += len(chunk)
                if total_size > 0:
                    percent_complete = min(bytes_downloaded / total_size, 1.0)
                    mb_done = bytes_downloaded / (1024 * 1024)
                    mb_total = total_size / (1024 * 1024)
                    progress_bar.progress(
                        percent_complete,
                        text=f"Downloading IBTrACS dataset... {mb_done:.0f} MB / {mb_total:.0f} MB",
                    )

        progress_bar.progress(1.0, text="Filtering and saving dataset...")

        # Read only the columns we need from the raw file
        df = pd.read_csv(TEMP_RAW_PATH, low_memory=False, usecols=IBTRACS_COLUMNS)

        # The row directly below the header is a units row (e.g. "Year",
        # "kts", "mb"), not real data. Coercing SEASON to numeric turns
        # that row's "Year" entry into NaN, and any row before 2000
        # into a value we can filter out in the same step.
        df["SEASON"] = pd.to_numeric(df["SEASON"], errors="coerce")
        df = df.dropna(subset=["SEASON"])
        df = df[df["SEASON"] >= 2000].copy()
        df["SEASON"] = df["SEASON"].astype(int)

        # Save only the filtered, narrowed data locally
        df.to_csv(LOCAL_PATH, index=False)

        # Discard the full raw download — only the filtered file is kept
        os.remove(TEMP_RAW_PATH)

        progress_bar.empty()
    else:
        df = pd.read_csv(LOCAL_PATH, low_memory=False, usecols=IBTRACS_COLUMNS)

    return df
    

@st.cache_data
def load_data():
    df = download_if_needed()
    st.write(list(df.columns))

  

    # Convert types FIRST
    df["LAT"] = pd.to_numeric(df["LAT"], errors="coerce")
    df["LON"] = pd.to_numeric(df["LON"], errors="coerce")
    df["WMO_WIND"] = pd.to_numeric(df["WMO_WIND"], errors="coerce")
    df["WMO_PRES"] = pd.to_numeric(df["WMO_PRES"], errors="coerce")
    df["ISO_TIME"] = pd.to_datetime(df["ISO_TIME"], format="%d/%m/%Y %H:%M", errors="coerce")

    return df

st.title("🌪 Hurricane Tracker")

#step 2: Pick ONE storm (for now Tropical storm BERYL- SID= 2024181N09320)

df = load_data()

target_sid = "2024181N09320"

storm = df[df["SID"] == target_sid].sort_values(by="ISO_TIME")

st.subheader("Selected Storm Data")
st.subheader("Storm Name: Tropical Storm BERYL | SID:2024181N09320")

storm_clean = storm.dropna(subset=["LAT", "LON", "ISO_TIME"]).reset_index(drop=True)

if storm_clean.empty:
    st.warning("No valid track data for this storm.")
else:
    def make_label(row):
        """Text shown inside the chart for a given storm observation."""
        wind = f"{row['WMO_WIND']:.0f} kts" if pd.notna(row["WMO_WIND"]) else "N/A"
        pres = f"{row['WMO_PRES']:.0f} mb" if pd.notna(row["WMO_PRES"]) else "N/A"
        return (
            f"Time: {row['ISO_TIME'].strftime('%b %d, %Y %H:%M UTC')}<br>"
            f"Lat: {row['LAT']:.1f}   Lon: {row['LON']:.1f}<br>"
            f"Wind: {wind}   Pressure: {pres}"
        )

    fig = go.Figure()

    # Trace 0: full track line, static across all frames
    fig.add_trace(go.Scattergeo(
        lon=storm_clean["LON"],
        lat=storm_clean["LAT"],
        mode="lines",
        line=dict(width=2, color="gray"),
        name="Full track"
    ))

    # Trace 1: the moving dot, starts at the first observation
    fig.add_trace(go.Scattergeo(
        lon=[storm_clean.loc[0, "LON"]],
        lat=[storm_clean.loc[0, "LAT"]],
        mode="markers",
        marker=dict(size=14, color="red"),
        name="Current position"
    ))

    # One frame per real observation. Each frame updates only trace 1
    # (the dot) plus an on-chart annotation with time/lat/lon/wind/pressure.
    frames = []
    for i, row in storm_clean.iterrows():
        frames.append(go.Frame(
            name=str(i),
            data=[go.Scattergeo(lon=[row["LON"]], lat=[row["LAT"]])],
            traces=[1],
            layout=go.Layout(
                annotations=[dict(
                    text=make_label(row),
                    xref="paper", yref="paper",
                    x=0.02, y=0.98,
                    xanchor="left", yanchor="top",
                    showarrow=False,
                    align="left",
                    bgcolor="rgba(255,255,255,0.85)",
                    bordercolor="gray",
                    borderwidth=1,
                    font=dict(size=13),
                )]
            )
        ))
    fig.frames = frames

    # Initial annotation, matching frame 0, so it's visible before any drag
    fig.update_layout(
        annotations=[dict(
            text=make_label(storm_clean.loc[0]),
            xref="paper", yref="paper",
            x=0.02, y=0.98,
            xanchor="left", yanchor="top",
            showarrow=False,
            align="left",
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor="gray",
            borderwidth=1,
            font=dict(size=13),
        )]
    )

    # Plotly's own slider — lives entirely in the browser, so dragging it
    # moves the dot instantly with no round-trip to the Streamlit server
    fig.update_layout(
        geo=dict(
            projection_type="natural earth",
            showland=True,
            landcolor="rgb(235, 235, 235)",
            showcountries=True,
            showcoastlines=True,
            fitbounds="locations",
        ),
        height=550,
        margin=dict(l=0, r=0, t=0, b=0),
        sliders=[dict(
            active=0,
            currentvalue=dict(prefix="Showing: ", font=dict(size=13)),
            pad=dict(t=40),
            steps=[
                dict(
                    method="animate",
                    args=[
                        [str(i)],
                        dict(
                            mode="immediate",
                            frame=dict(duration=0, redraw=True),
                            transition=dict(duration=0),
                        ),
                    ],
                    label=row["ISO_TIME"].strftime("%b %d, %H:%M"),
                )
                for i, row in storm_clean.iterrows()
            ],
        )],
    )

    st.caption(
        f"Start: {storm_clean['ISO_TIME'].min().strftime('%b %d, %Y %H:%M UTC')}  |  "
        f"End: {storm_clean['ISO_TIME'].max().strftime('%b %d, %Y %H:%M UTC')}"
    )
    st.plotly_chart(fig, use_container_width=True)

st.write("Nature: Tropical Storm")
st.write("Basin: North Atlantic")
st.write("Subbasin: North Atlantic and Carribean")
st.write("Season: 2024")

#use ctrl shift b to start program.