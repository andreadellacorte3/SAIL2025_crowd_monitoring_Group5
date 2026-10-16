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
import numpy as np


def generate_arc_polygon(lon, lat, direction_degrees, count, base_radius=1):
    """Generates the coordinates for a curved polygon facing a specific direction."""
    # 0 = North, 90 = East. We sweep from -half_span_in_degrees to +half_span_in_degrees degrees to leave a nice gap between the halves.
    if count == 0: return []
    half_span_in_degrees = 20
    start_angle = np.radians(direction_degrees - half_span_in_degrees)
    end_angle = np.radians(direction_degrees + half_span_in_degrees)
    
    # Scale the outer size of the ring by the crowd count
    rescale = 10000
    outer_radius = np.sqrt((base_radius**2)+(count/np.pi)) / rescale
    inner_radius = base_radius / rescale

    # Generate points along the curve
    angles = np.linspace(start_angle, end_angle, 50)
    
    # Longitude correction factor to keep circles round on Web Mercator maps
    lat_ratio = np.cos(np.radians(lat))
    
    
    # Calculate outer edge
    outer_lon = lon + (outer_radius * np.sin(angles)) / lat_ratio
    outer_lat = lat + (outer_radius * np.cos(angles))
    
    # Calculate inner edge (reversed so the polygon closes properly)
    inner_lon = lon + (inner_radius * np.sin(angles[::-1])) / lat_ratio
    inner_lat = lat + (inner_radius * np.cos(angles[::-1]))
    
    # Combine into a single polygon path
    
    polygon = [(x, y) for x, y in np.dstack((outer_lon, outer_lat))[0]] + \
              [(x, y) for x, y in np.dstack((inner_lon, inner_lat))[0]]
              
    return polygon

def update_visuals(chosen_time: datetime.time):
    chosen_datetime = datetime.datetime.combine(chosen_date,chosen_time)

    crowd_sensor_time_data = crowd_count_data[
    (crowd_count_data["timestamp"] == chosen_datetime) |
    (crowd_count_data.index == "lat") |
    (crowd_count_data.index == "long") |
    (crowd_count_data.index == "orientation") |
    (crowd_count_data.index == "name_without_orientation") 
    ].T
    crowd_sensor_time_data.drop(["minute","day","weekday","month","hour","is_weekend","timestamp"], inplace = True)
    # st.dataframe(crowd_sensor_time_data)
    # st.dataframe(crowd_sensor_time_data.transpose())



    crowd_sensor_time_data["orientation"] = crowd_sensor_time_data["orientation"].astype(int,errors = "ignore")
    crowd_sensor_time_data = crowd_sensor_time_data.rename(columns={crowd_sensor_time_data.columns[0]: "count"})
    
    
    # st.dataframe(crowd_sensor_time_data)


    crowd_sensor_time_data["polygon"] = crowd_sensor_time_data.apply(
        lambda row: generate_arc_polygon(
            lon= float(row["long"]), 
            lat=float(row["lat"]), 
            direction_degrees=int(row["orientation"]), 
            count= int(row["count"])
        ),
        axis = 1)
    
    crowd_sensor_time_data["tooltip-info"] = "" + \
    crowd_sensor_time_data["name_without_orientation"].astype(str) + \
    "\nOrientation: " + crowd_sensor_time_data["orientation"].astype(str) + \
    "\nCount: " + crowd_sensor_time_data["count"].astype(int).astype(str)

    crowd_sensor_time_data["color"] =  crowd_sensor_time_data["orientation"].apply(lambda x: [255,128,0,200] if x >= 180 else [0,255,255,200])

    with visuals.container():
        # Creates the layer to plot based on the previous data
        crowd_count_position_layer = pdk.Layer(
            "ScatterplotLayer",
            crowd_sensor_position_data,
            pickable=False,
            opacity=0.8,
            stroked=True,
            filled=True,
            line_width_min_pixels=1,
            get_position= "[long,lat]",
            get_radius=6,
            get_fill_color=[255, 255, 255],
            get_line_color=[0, 0, 0],
        )

        crowd_count_layer = pdk.Layer(
            "PolygonLayer",
            crowd_sensor_time_data,
            get_polygon="polygon",
            get_fill_color='color',
            filled=True,
            extruded=False,
            wireframe=False,
            pickable=True

        )

        layers = []
        if "Sensors" in selected_layers:
            layers.append(crowd_count_position_layer)
            layers.append(crowd_count_layer)

        if "Vessels" in selected_layers:
            pass # layers.append(vessels_layer) when vessels_layer is defined
        # this sets the default initial view point
        amsterdam = pdk.ViewState(latitude=52.380450, longitude = 4.900310, zoom=11) 
        # The map is plotted
        st.pydeck_chart(pdk.Deck(
            layers=layers,
            tooltip = {"text": "{tooltip-info}"},
            initial_view_state = amsterdam
        ))





        st.header("Ongoing events")
        st.dataframe(program[
            (program["start_datetime"] <= chosen_datetime) & 
            (program["end_datetime"] >= chosen_datetime)]
            [["Start","End"]])
        return


# set the streamlit app main page configuration
st.set_page_config(page_title="SAIL 2025 crowd monitoring dashboard", layout="wide",page_icon = ":sailboat:")
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

chosen_datetime = datetime.datetime.combine(chosen_date,chosen_time)

non_sensors = (
        "hour",
        "timestamp",
        "minute",
        "day",
        "month",
        "weekday",
        "is_weekend",
        )


transpose = crowd_count_data.loc[["lat","long","name_without_orientation"]].transpose()
crowd_sensor_position_data = transpose[
    transpose.index.str.contains("-")
]
crowd_sensor_position_data = crowd_sensor_position_data.drop_duplicates()




st.header("IJ's map")
selected_layers = st.pills("Map layers",options = ["Sensors", "Vessels"],selection_mode = "multi")
visuals = st.empty()


        
update_visuals(chosen_time = chosen_time)
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

