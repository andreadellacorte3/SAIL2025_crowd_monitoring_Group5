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

# set the streamlit app main page configuration
st.set_page_config(page_title="SAIL 2025 crowd monitoring dashboard", layout="wide")
st.title("SAIL 2025 crowd monitoring dashboard", anchor = False)
st.sidebar.header("Filters")



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

chosen_time = st.sidebar.slider(
    value = datetime.time(14),
    label = "Time",
    format = "HH:mm",
    min_value = min_time,
    max_value = max_time,
    step = datetime.timedelta(minutes = 3),
    # key = "saved_time"
    )

chosen_datetime = datetime.datetime.combine(chosen_date,chosen_time)


st.header("IJ's map")
selected_layers = st.pills("Map layers",options = ["Sensors", "Vessels"],selection_mode = "multi")



# The following logic must be eventually moved to a different file.
# The metric is now only to represent something, the actual data will be 
# calculated later
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





st.header("Ongoing events")
st.dataframe(program[
    (program["start_datetime"] <= chosen_datetime) & 
    (program["end_datetime"] >= chosen_datetime)]
    [["Start","End"]])
