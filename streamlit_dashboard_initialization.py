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

# set the streamlit app main page configuration
st.set_page_config(page_title="SAIL 2025 crowd monitoring dashboard", layout="wide")
st.title("SAIL 2025 crowd monitoring dashboard", anchor = False)
st.sidebar.header("Filters")

#These are to change based on the catalogue
min_date = "2025-08-20"
max_date = "2025-08-24"

chosen_date = st.sidebar.date_input(
    label = "Date", 
    format = "DD/MM/YYYY", 
    min_value = min_date, 
    max_value = max_date, 
    )   

#These are to change based on the catalogue and the current day
min_time = datetime.time(8,0)
max_time = datetime.time(17,0)

chosen_time = st.sidebar.slider(
    value = datetime.time(14,0),
    label = "Time",
    format = "HH:mm",
    min_value = min_time,
    max_value = max_time,
    step = datetime.timedelta(minutes = 3)
    )


st.header("IJ's map")
selected_layers = st.pills("Map layers",options = ["Sensors", "Vessels"],selection_mode = "multi")

data = load_data()

# The following logic must be eventually moved to a different file.
for_pdk_layer = []
for sensor in data:
    total_count = 0
    for counts in data[sensor]["orientation"].values():
        total_count += sum(counts)
    for_pdk_layer.append(
        {
            "name": sensor,
            "pos": list((data[sensor]["y"],data[sensor]["x"])),
            "count_to_visualize": math.sqrt(total_count)/25,
            "count": total_count
        }
    )


# Creates the layer to plot based on the previous data
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
    get_position= "pos",
    get_radius="count_to_visualize",
    get_fill_color=[255, 140, 0],
    get_line_color=[0, 0, 0],
)

layers = []
if "Sensors" in selected_layers:
    layers.append(crowd_count_layer)
if "Vessels" in selected_layers:
    pass # layers.append(vessels_layer) when vessels_layer is defined
# this sets the default initial view point
amsterdam = pdk.ViewState(latitude=52.380450, longitude = 4.900310, zoom=11) 
# The map is plotted
st.pydeck_chart(pdk.Deck(
    layers=layers,
    tooltip={"text": "{name} to {count}"},
    initial_view_state = amsterdam
))