import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
import requests
import csv


URL = "https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.ALL.list.v04r01.csv"
LOCAL_PATH = "ibtracs.ALL.list.v04r01.csv"

IBTRACS_COLUMNS = [
    "SID", "SEASON", "NUMBER", "BASIN", "SUBBASIN", "NAME",
    "ISO_TIME", "NATURE", "LAT", "LON", "WMO_WIND", "WMO_PRES",
]


def download_if_needed():
    if not os.path.exists(LOCAL_PATH):
        response = requests.get(URL, stream=True)
        response.raise_for_status()
        total_size = int(response.headers.get("content-length", 0))

        progress_bar = st.progress(0, text="Downloading IBTrACS dataset (first time only)...")
        bytes_seen = 0
        rows_written = 0
        column_indices = None
        season_idx = IBTRACS_COLUMNS.index("SEASON")

        with open(LOCAL_PATH, "w", newline="", encoding="utf-8") as out_f:
            writer = csv.writer(out_f)
            writer.writerow(IBTRACS_COLUMNS)

            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue

                bytes_seen += len(line.encode("utf-8")) + 1
                row = next(csv.reader([line]))

                if column_indices is None:
                    column_indices = [row.index(col) for col in IBTRACS_COLUMNS]
                    progress_bar.progress(0.0, text="Downloading & filtering...")
                    continue

                try:
                    filtered_row = [row[i] for i in column_indices]
                except IndexError:
                    continue

                try:
                    season_num = int(float(filtered_row[season_idx]))
                except ValueError:
                    continue

                if season_num < 2000:
                    continue

                writer.writerow(filtered_row)
                rows_written += 1

                if total_size > 0:
                    percent_complete = min(bytes_seen / total_size, 1.0)
                    mb_done = bytes_seen / (1024 * 1024)
                    mb_total = total_size / (1024 * 1024)
                    progress_bar.progress(
                        percent_complete,
                        text=f"Downloading & filtering... {mb_done:.0f} MB / {mb_total:.0f} MB — {rows_written} rows kept",
                    )

        progress_bar.empty()

    return pd.read_csv(LOCAL_PATH, low_memory=False)


@st.cache_data
def load_data():
    df = download_if_needed()

    # strip whitespace
    for col in df.select_dtypes(include="object"):
        df[col] = df[col].str.strip()

    # convert types
    df["LAT"] = pd.to_numeric(df["LAT"], errors="coerce")
    df["LON"] = pd.to_numeric(df["LON"], errors="coerce")
    df["WMO_WIND"] = pd.to_numeric(df["WMO_WIND"], errors="coerce")
    df["WMO_PRES"] = pd.to_numeric(df["WMO_PRES"], errors="coerce")
    df["ISO_TIME"] = pd.to_datetime(df["ISO_TIME"], errors="coerce")

    return df


st.title("🌪 Hurricane Tracker")

df = load_data()

# =========================
# DROPDOWN STORM SELECTOR
# =========================

storm_options = (
    df[["SID", "NAME"]]
    .dropna()
    .drop_duplicates()
    .sort_values("NAME")
)

storm_label_map = {
    f"{row['NAME']} ({row['SID']})": row["SID"]
    for _, row in storm_options.iterrows()
}

selected_label = st.selectbox(
    "Select storm",
    list(storm_label_map.keys())
)

target_sid = storm_label_map[selected_label]

storm = df[df["SID"] == target_sid].sort_values(by="ISO_TIME")

storm_name = storm["NAME"].iloc[0] if not storm.empty else "Unknown Storm"

st.subheader("Selected Storm Data")
st.subheader(f"{storm_name} | SID: {target_sid}")

storm_clean = storm.dropna(subset=["LAT", "LON", "ISO_TIME"]).reset_index(drop=True)

if storm_clean.empty:
    st.warning("No valid track data for this storm.")
else:

    def make_label(row):
        wind = f"{row['WMO_WIND']:.0f} kts" if pd.notna(row["WMO_WIND"]) else "N/A"
        pres = f"{row['WMO_PRES']:.0f} mb" if pd.notna(row["WMO_PRES"]) else "N/A"
        return (
            f"Time: {row['ISO_TIME'].strftime('%b %d, %Y %H:%M UTC')}<br>"
            f"Lat: {row['LAT']:.1f}   Lon: {row['LON']:.1f}<br>"
            f"Wind: {wind}   Pressure: {pres}"
        )

    fig = go.Figure()

    fig.add_trace(go.Scattergeo(
        lon=storm_clean["LON"],
        lat=storm_clean["LAT"],
        mode="lines",
        line=dict(width=2, color="gray"),
        name="Full track"
    ))

    fig.add_trace(go.Scattergeo(
        lon=[storm_clean.loc[0, "LON"]],
        lat=[storm_clean.loc[0, "LAT"]],
        mode="markers",
        marker=dict(size=14, color="red"),
        name="Current position"
    ))

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

# =========================
# BOTTOM METADATA (SAFE)
# =========================

st.write("Nature:", storm_clean["NATURE"].iloc[0] if not storm_clean.empty else "N/A")
st.write("Basin:", storm["BASIN"].iloc[0] if not storm.empty else "N/A")
st.write("Subbasin:", storm["SUBBASIN"].iloc[0] if not storm.empty else "N/A")
st.write("Season:", int(storm["SEASON"].iloc[0]) if not storm.empty else "N/A")