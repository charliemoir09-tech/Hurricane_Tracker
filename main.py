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
        return df
    else:
        return pd.read_csv(LOCAL_PATH, low_memory=False)
    
@st.cache_data
def load_data():
    df = download_if_needed()

    # Drop the second header row (units row)
    df = df[df["SID"] != "SID"].copy()

    # Convert types
    df["LAT"] = pd.to_numeric(df["LAT"], errors="coerce")
    df["LON"] = pd.to_numeric(df["LON"], errors="coerce")
    df["ISO_TIME"] = pd.to_datetime(df["ISO_TIME"], errors="coerce")

    return df


st.title("🌪 Hurricane Tracker")

df = load_data()

st.success("Data loaded (from local cache if available)")
st.write(df.head())
