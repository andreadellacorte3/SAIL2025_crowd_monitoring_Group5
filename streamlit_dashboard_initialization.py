"""
Run this file from a terminal with:
    streamlit run streamlit_dashboard_initialization.py
"""

# install all required packages first
import streamlit as st
import datetime
import pydeck as pdk
from Population_of_dictionary_with_pedestrian_data import load_data
import math
from find_start_end_datetimes import load_program
import time
import pandas as pd
# set the streamlit app main page configuration
st.set_page_config(page_title="SAIL 2025 crowd monitoring dashboard", layout="wide")
st.title("SAIL 2025 crowd monitoring dashboard", anchor = False)
st.sidebar.header("Filters")

#Starting from here to implement stuff from Data_transformation.ipynb, 
# i'm just copying some codes already written by matteo and some filters made bymiself 
#in order to add it to the dashboard
# --- LOADING AND FILTERING VESSELS ---
vessels_df = pd.read_csv("../Vesselposition_data_20-24Aug2025.csv")

# Time conversion
vessels_df["hourminute"] = (pd.to_datetime(vessels_df["upload-timestamp"], 
    utc=True, format="ISO8601")
    .dt.tz_convert("Europe/Amsterdam")
    .dt.strftime("%H%M")
    .astype(int))

# Filter sail destinations
sail_destinations = vessels_df[
    vessels_df["destination"].str.contains("SAIL", case=False, na=False)]
mask_1 = [
    "Exhibition Vessel", "Frigate", "Museum, Stationary", 
    "Passenger Ship", "Passenger/Cruise", "Sail Training Ship", 
    "Sailing Vessel", "Yacht", "Yacht (Sailing)"]

df_cat = vessels_df[vessels_df["sub-category"].isin(mask_1)]
df_dest = vessels_df[
    (vessels_df["sub-category"].isna()) & 
    (vessels_df["destination"].isin(sail_destinations["destination"].unique()))]

# Concatenation
sail_vessels = pd.concat([df_cat, df_dest]).drop_duplicates().reset_index(drop=True)
 #work in progress from here







crowd_count_data = load_data()
program  = load_program()

#These are to change based on the catalogue
min_date = min(program["start_datetime"].dt.date)
max_date = max(program["end_datetime"].dt.date)


chosen_date = st.sidebar.date_input(
    label = "Date", 
    format = "DD/MM/YYYY", 
    min_value = min_date, 
    max_value = max_date, 
    )   

#These are to change based on the catalogue and the current day
min_time = min(program[
    program["start_datetime"].dt.date == chosen_date
    ]["start_datetime"].dt.time)

max_time = max(program[
    program["end_datetime"].dt.date == chosen_date
    ]["end_datetime"].dt.time)


time_slider = st.sidebar.empty()
chosen_time = time_slider.slider(
    value = datetime.time(14),
    label = "Time",
    format = "HH:mm",
    min_value = min_time,
    max_value = max_time,
    step = datetime.timedelta(minutes = 3),
    # key = "saved_time"
    )


st.header("IJ's map")
selected_layers = st.pills("Map layers",options = ["Sensors", "Vessels"],selection_mode = "multi")
visuals = st.empty()

def update_visuals(chosen_time = chosen_time):
    chosen_datetime = datetime.datetime.combine(chosen_date,chosen_time)

    for_pdk_layer = []
    for sensor in crowd_count_data:
        total_count = 0
        for counts in crowd_count_data[sensor]["orientation"].values():
            total_count += sum(counts)
        for_pdk_layer.append(
            {
                "name": sensor,
                "pos": list((crowd_count_data[sensor]["y"],crowd_count_data[sensor]["x"])),
                "count_to_visualize": math.sqrt(total_count)/25,
                "count": total_count
            }
        )

    with visuals.container():
        
        crowd_count_layer = pdk.Layer(
            "ScatterplotLayer",
            for_pdk_layer,
            pickable=True,
            opacity=0.8,
            stroked=True,
            filled=True,
            radius_scale=6,
            radius_min_pixels=1,
            radius_max_pixels=100,
            line_width_min_pixels=1,
            get_position="pos",
            get_radius="count_to_visualize",
            get_fill_color=[255, 140, 0],
            get_line_color=[0, 0, 0],
        )

        # Layer Vessels
        vessels_layer = pdk.Layer(
            "ScatterplotLayer",
            sail_vessels,
            pickable=True,
            opacity=0.9,
            stroked=True,
            filled=True,
            radius_scale=1,
            radius_min_pixels=5,
            radius_max_pixels=30,
            get_position=["longitude", "latitude"], 
            get_fill_color=[0, 128, 255],            
            get_line_color=[255, 255, 255],
        )

        # 3. dynamics layers
        layers = []
        if "Sensors" in selected_layers:
            layers.append(crowd_count_layer)
        if "Vessels" in selected_layers:
            layers.append(vessels_layer)

        # starting map point Amsterdam
        amsterdam = pdk.ViewState(latitude=52.380450, longitude=4.900310, zoom=11)

        st.pydeck_chart(pdk.Deck(
            layers=layers,
            tooltip={"text": "{name}\n{sub-category}"},
            initial_view_state=amsterdam
        ))





        st.header("Ongoing events")
        st.dataframe(program[
            (program["start_datetime"] <= chosen_datetime) & 
            (program["end_datetime"] >= chosen_datetime)]
            [["Start","End"]])
        return




    

        
update_visuals()
col1, col2 = st.sidebar.columns(2)
play = col1.empty()
stop = col2.button("⏹  Stop")
speed = st.sidebar.number_input(
    "Play speed",
    value = 1.0,
    min_value = 0.0,
    step = 1.0
)


if play.button("▶  Play"):
    today = datetime.date.today()
    max_dt = datetime.datetime.combine(today,max_time)
    chosen_dt = datetime.datetime.combine(today,chosen_time)
    max_range = int((max_dt-chosen_dt)/ datetime.timedelta(minutes = 3)) + 1 
    range_to_go = [(chosen_dt + datetime.timedelta(minutes = i*3)).time() for i in range(max_range)]
    for i in range_to_go:
        chosen_time = time_slider.slider(
            label = "Time",
            min_value=min_time, 
            max_value=max_time, 
            value=i,
            step=datetime.timedelta(minutes=3)
        )
        update_visuals(chosen_time)
        time.sleep(0.5/speed)
