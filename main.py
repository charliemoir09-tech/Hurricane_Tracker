import pandas as pd
import streamlit as st
import os


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

target_sid = "2024181N09320"

storm = df[df["SID"] == target_sid].sort_values(by="ISO_TIME")

st.subheader("Selected Storm Data")
st.subheader("Storm Name: Tropical Storm BERYL | SID:2024181N09320")
st.write(storm)
st.write("Nature: Tropical Storm")
st.write("Basin: North Atlantic")
st.write("Subbasin: North Atlantic and Carribean")
st.write("Season: 2024")


#USE ctrl_(shift)_b TO START PROGRAM
