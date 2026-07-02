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