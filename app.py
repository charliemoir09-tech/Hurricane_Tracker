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
                        text=f"Downloading & filtering... {mb_done:.0f}/{mb_total:.0f} MB — {rows_written} rows",
                    )

        progress_bar.empty()

    return pd.read_csv(LOCAL_PATH, low_memory=False)


@st.cache_data
def load_data():
    df = download_if_needed()

    for col in df.select_dtypes(include=["object", "str"]):
        df[col] = df[col].str.strip()

    df["LAT"] = pd.to_numeric(df["LAT"], errors="coerce")
    df["LON"] = pd.to_numeric(df["LON"], errors="coerce")
    df["WMO_WIND"] = pd.to_numeric(df["WMO_WIND"], errors="coerce")
    df["WMO_PRES"] = pd.to_numeric(df["WMO_PRES"], errors="coerce")
    df["ISO_TIME"] = pd.to_datetime(df["ISO_TIME"], errors="coerce")

    return df


# ================= UI =================
st.set_page_config(page_title="Hurricane Tracker", layout="wide")

st.title("🌪 Hurricane Tracker")


def saffir(windspeed):
    if windspeed >= 137: return "Category 5"
    if windspeed >= 113: return "Category 4"
    if windspeed >= 96: return "Category 3"
    if windspeed >= 83: return "Category 2"
    if windspeed >= 64: return "Category 1"
    return "Tropical Storm"


def translate_basin(code):
    return {
        "NA": "North Atlantic",
        "EP": "Eastern Pacific",
        "WP": "Western Pacific",
        "NI": "North Indian",
        "SI": "South Indian",
        "SP": "South Pacific",
        "SA": "South Atlantic",
    }.get(code, "Unknown")


def translate_subbasin(code):
    return {
        "CS": "Caribbean Sea",
        "GM": "Gulf of Mexico",
        "BB": "Bay of Bengal",
        "AS": "Arabian Sea",
        "WA": "Western Australia",
        "EA": "Eastern Australia",
    }.get(code, "Unknown")


def translate_nature(code):
    return {
        "DS": "Disturbance",
        "TS": "Tropical",
        "ET": "Extratropical",
        "SS": "Subtropical",
        "MX": "Mixture",
    }.get(code, "Unknown")

df = load_data()

storm_options = (
    df[["SID", "NAME"]]
    .dropna()
    .drop_duplicates()
    .sort_values("NAME")
)

storm_label_map = {
    f"{row['NAME']} ({row['SID'][:4]})": row["SID"]
    for _, row in storm_options.iterrows()
}

selected_label = st.selectbox(
    "Select Storm",
    ["-- Select a storm --"] + list(storm_label_map.keys())
)

if selected_label == "-- Select a storm --":
    st.info("Please select a storm to display the map 🌪")
    st.stop()

target_sid = storm_label_map[selected_label]

storm = df[df["SID"] == target_sid].sort_values("ISO_TIME")
storm_name = storm["NAME"].iloc[0] if not storm.empty else "Unknown"

st.subheader(f"{storm_name} ({target_sid[:4]})")

storm_clean = storm.dropna(subset=["LAT", "LON", "ISO_TIME"]).reset_index(drop=True)

if storm_clean.empty:
    st.warning("No valid track data.")
    st.stop()


def make_label(row):
    wind_str = f"{row['WMO_WIND']:.0f} kts" if pd.notna(row["WMO_WIND"]) else "N/A"
    pressure_str = f"{row['WMO_PRES']:.0f} mb" if pd.notna(row["WMO_PRES"]) else "N/A"

    return (
        f"{row['ISO_TIME'].strftime('%b %d %H:%M UTC')}<br>"
        f"Lat {row['LAT']:.1f} Lon {row['LON']:.1f}<br>"
        f"Wind {wind_str} Pressure {pressure_str}<br>"
        f"Category {saffir(row['WMO_WIND'])  if pd.notna(row["WMO_WIND"]) else 'N/A'}<br>"
    )


fig = go.Figure()

fig.add_trace(go.Scattergeo(
    lon=storm_clean["LON"],
    lat=storm_clean["LAT"],
    mode="lines",
    line=dict(width=2, color="white"),
    name="Track"
))

fig.add_trace(go.Scattergeo(
    lon=[storm_clean.loc[0, "LON"]],
    lat=[storm_clean.loc[0, "LAT"]],
    mode="markers",
    marker=dict(size=12, color="red"),
    name="Current"
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
                xref="paper",
                yref="paper",
                x=0.02,
                y=0.98,
                showarrow=False,
                bgcolor="rgba(0,0,0,0.5)",
                font=dict(color="white")
            )]
        )
    ))

fig.frames = frames


fig.update_layout(
    geo=dict(
        projection_type="natural earth",
        showland=True,
        landcolor="rgb(40, 60, 40)",
        showocean=True,
        oceancolor="rgb(10,25,45)",
        showcountries=True,
        showcoastlines=True,
        coastlinecolor="rgba(255,255,255,0.3)",
        fitbounds="locations",
    ),

    height=600,
    margin=dict(l=0, r=0, t=0, b=0),

    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",

    modebar=dict(
        orientation="v",
        bgcolor="rgba(0,0,0,0.2)"
    ),

    sliders=[dict(
        active=0,
        currentvalue=dict(font=dict(color="white")),
        bgcolor="rgba(255,255,255,0.1)",
        steps=[
            dict(
                method="animate",
                args=[[str(i)], dict(mode="immediate")],
                label=row["ISO_TIME"].strftime("%b %d %H:%M"),
            )
            for i, row in storm_clean.iterrows()
        ],
    )],
)


col1, col2 = st.columns([1, 2])  # left smaller, right bigger

with col2:
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displayModeBar": False}
    )

with col1:
    # st.markdown("### Storm Details")

    st.write("Season:", str(int(storm["SEASON"].iloc[0])))
    st.write("Storm ID:", storm["SID"].iloc[0])
    st.write("Nature:", translate_nature(storm["NATURE"].iloc[0]))
    st.write("Basin:", translate_basin(storm["BASIN"].iloc[0]))
    st.write("Subbasin:", translate_subbasin(storm["SUBBASIN"].iloc[0]))
    st.write("Max. strength:", saffir(storm["WMO_WIND"].max()) if pd.notna(storm["WMO_WIND"].max()) else "N/A")