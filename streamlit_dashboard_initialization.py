"""
Run this file from a terminal with:
    streamlit run streamlit_dashboard_initialization.py

The dashboard follows the requirements of our TIL4030 report (chapter 2):
FC1-FC5 for what the map shows, NFC1 for the colour scale and the legend,
FO1-FO3 for the events, trains and vessels around the counts.
"""

# install all required packages first
import streamlit as st
import datetime
import pydeck as pdk
import pandas as pd
from Population_of_dictionary_with_pedestrian_data import load_data
import math
from find_start_end_datetimes import load_program
import time
import numpy as np
from src.events import load_sensors, sensor_totals
from src.flow import load_effective_widths, flow_per_metre
from src.trains import train_counts
from src.sensor_status import LOS_LIMITS, level_of_service, find_off_sensors, off_periods


# Colour of each level of service: green when it is fine, then yellow and red, black for a crisis (NFC1).
# Every level is darker than the one before, so the levels can be told apart also without seeing colours.
LOS_COLORS = {
    "A": [199, 233, 192],
    "B": [253, 208, 73],
    "C": [253, 141, 60],
    "D": [215, 48, 39],
    "E": [127, 0, 0],
    "F": [0, 0, 0],
}
OFF_COLOR = [150, 150, 150]

# Flow per metre (persons/m/min) above which a location is highlighted on the map (FC5).
# The report says the threshold differs between walkways, streets and ferry landings,
# but the values are not decided yet: for now all three use the start of level D.
HIGHLIGHT_THRESHOLD = {
    "SAIL walkway": 49,
    "Ferry landing": 49,
    "City centre street": 49,
}

AMSTERDAM_CENTRAAL = {"lat": 52.3789, "lon": 4.9003}


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


@st.cache_data(show_spinner = False)
def prepare_sensor_data(_crowd_count_data):
    """Pedestrians, flow per metre and off intervals per sensor, one row per 3-minute interval.

    The two walking directions of a sensor are added up. The underscore in front of the
    argument tells streamlit not to check the whole table every time (it never changes).
    """
    counts = _crowd_count_data[_crowd_count_data["timestamp"].notna()].set_index("timestamp")
    counts = counts[[c for c in counts.columns if "-" in c]].astype(float)

    sensors = load_sensors()
    totals = sensor_totals(counts)
    totals = totals[[s for s in totals.columns if s in sensors.index]]
    flow = sensor_totals(flow_per_metre(counts, load_effective_widths()))
    off = find_off_sensors(totals, sensors)
    return sensors, totals, flow, off, off_periods(off)


@st.cache_data(show_spinner = False)
def load_trains():
    """Train arrivals and departures at Amsterdam Centraal per 3 minutes (FO2)."""
    trains = train_counts()
    trains.index = trains.index.tz_localize(None)   # same clock time as the sensor data
    return trains


def show_legend():
    """Legend of the map (NFC1)."""
    def box(color):
        return f'<span style="display:inline-block;width:14px;height:14px;background:rgb({color[0]},{color[1]},{color[2]});border:1px solid #444;vertical-align:middle;margin:0 4px 0 12px"></span>'

    ring = '<span style="display:inline-block;width:14px;height:14px;border:3px solid #000;border-radius:50%;vertical-align:middle;margin:0 4px 0 12px"></span>'

    text = "<b>Level of service</b> (flow per metre):"
    lower = 0
    for level, color in LOS_COLORS.items():
        if level in LOS_LIMITS:
            text += box(color) + f"{level} {lower}-{LOS_LIMITS[level]}"
            lower = LOS_LIMITS[level]
        else:
            text += box(color) + f"{level} above {lower}"
    text += "<br>" + box(OFF_COLOR) + "sensor off, no data" + ring + "above the threshold"
    text += "&nbsp;&nbsp;&nbsp;&nbsp;Arc size = pedestrians counted, one arc per walking direction"
    st.markdown(text, unsafe_allow_html = True)


def update_visuals(chosen_time: datetime.time):
    chosen_datetime = datetime.datetime.combine(chosen_date,chosen_time)
    interval_end = chosen_datetime + datetime.timedelta(minutes = 3)
    # FC2: every view says which moment its data belong to
    time_label = chosen_datetime.strftime("%A %d %B %Y, %H:%M") + "-" + interval_end.strftime("%H:%M")

    if chosen_datetime not in totals.index:
        visuals.warning("There are no sensor data for " + time_label)
        return

    # One row per sensor with what it measured at the chosen moment
    now = sensors.copy()
    now["count"] = totals.loc[chosen_datetime]
    now["flow"] = flow.loc[chosen_datetime]
    now["off"] = off.loc[chosen_datetime]
    now["los"] = now["flow"].apply(level_of_service)
    now.loc[now["off"], "los"] = ""     # an off sensor has no level, so it stays out of the colour scale (FC3)
    now["above_threshold"] = (now["flow"] > now["family_description"].map(HIGHLIGHT_THRESHOLD)) & ~now["off"]

    def sensor_tooltip(row):
        text = row["location_name"] + " (" + row.name + ")\nTime: " + time_label
        if row["off"]:
            period = off_list[(off_list["sensor"] == row.name) &
                              (off_list["start"] <= chosen_datetime) & (off_list["end"] >= chosen_datetime)].iloc[0]
            return text + "\nSensor off, no data from " + period["start"].strftime("%a %H:%M") + \
                " to " + period["end"].strftime("%a %H:%M")
        return text + "\nPedestrians (both directions): " + str(int(row["count"])) + \
            "\nFlow: " + str(round(row["flow"], 1)) + " persons/m/min, level " + row["los"]

    now["tooltip-info"] = now.apply(sensor_tooltip, axis = 1)
    # the dot of every sensor has the colour of its level, so it can be read also when zoomed out
    now["marker_color"] = now["los"].apply(lambda level: LOS_COLORS.get(level, OFF_COLOR))
    now["marker_radius"] = now["off"].apply(lambda x: 30 if x else 15)
    # a letter next to the busier sensors, so the level can be read without the colours
    now["label"] = now["los"].apply(lambda x: x if x in ["C", "D", "E", "F"] else "")
    now.loc[now["off"], "label"] = "off"

    crowd_sensor_time_data = crowd_count_data[
    (crowd_count_data["timestamp"] == chosen_datetime) |
    (crowd_count_data.index == "lat") |
    (crowd_count_data.index == "long") |
    (crowd_count_data.index == "orientation") |
    (crowd_count_data.index == "name_without_orientation")
    ].T
    crowd_sensor_time_data.drop(["minute","day","weekday","month","hour","is_weekend","timestamp"], inplace = True)



    crowd_sensor_time_data["orientation"] = crowd_sensor_time_data["orientation"].astype(int,errors = "ignore")
    crowd_sensor_time_data = crowd_sensor_time_data.rename(columns={crowd_sensor_time_data.columns[0]: "count"})
    crowd_sensor_time_data["sensor"] = crowd_sensor_time_data["name_without_orientation"]
    crowd_sensor_time_data = crowd_sensor_time_data[crowd_sensor_time_data["sensor"].isin(now.index)]

    # An off sensor gets no arcs: its zeros are not real counts (FC3)
    sensor_off = crowd_sensor_time_data["sensor"].map(now["off"]).astype(bool)
    crowd_sensor_time_data.loc[sensor_off, "count"] = 0


    crowd_sensor_time_data["polygon"] = crowd_sensor_time_data.apply(
        lambda row: generate_arc_polygon(
            lon= float(row["long"]),
            lat=float(row["lat"]),
            direction_degrees=int(row["orientation"]),
            count= int(row["count"])
        ),
        axis = 1)

    crowd_sensor_time_data["tooltip-info"] = "" + \
    crowd_sensor_time_data["sensor"].map(now["tooltip-info"]) + \
    "\nThis direction (" + crowd_sensor_time_data["orientation"].astype(str) + " degrees): " + \
    crowd_sensor_time_data["count"].astype(int).astype(str)

    # Colour of the arcs = level of service of the sensor (NFC1, FC5)
    crowd_sensor_time_data["color"] = crowd_sensor_time_data["sensor"].map(now["los"]).apply(
        lambda level: LOS_COLORS.get(level, OFF_COLOR) + [220])

    # The part of the IJ the user chose (FC4)
    # the map is centred between the outermost sensors (the mean would lean towards the
    # many sensors in the old centre and leave NDSM out of the picture)
    if chosen_area == "Whole IJ":
        in_view = now
        zoom = 12.5
    else:
        in_view = now[now["zone"] == chosen_area]
        zoom = 15
    view = pdk.ViewState(
        latitude = (in_view["lat"].min() + in_view["lat"].max()) / 2,
        longitude = (in_view["lon"].min() + in_view["lon"].max()) / 2,
        zoom = zoom)

    with visuals.container():
        st.subheader("Data of " + time_label)   # FC2

        # The most critical place in view, readable at a glance (NFO1)
        active_in_view = in_view[~in_view["off"]]
        col_a, col_b, col_c = st.columns(3)
        if len(active_in_view) > 0:
            busiest = active_in_view["flow"].idxmax()
            col_a.metric("Highest flow per metre", str(round(active_in_view.loc[busiest, "flow"], 1)) + " persons/m/min")
            col_a.caption(active_in_view.loc[busiest, "location_name"] + " (" + busiest + "), level " + active_in_view.loc[busiest, "los"])
        col_b.metric("Sensors off", str(int(in_view["off"].sum())) + " of " + str(len(in_view)))
        col_c.metric("Train arrivals at Amsterdam Centraal", int(trains.loc[chosen_datetime, "arrivals"]))

        # Creates the layers to plot based on the previous data
        crowd_count_position_layer = pdk.Layer(
            "ScatterplotLayer",
            now,
            pickable=True,
            opacity=0.9,
            stroked=True,
            filled=True,
            line_width_min_pixels=1,
            radius_min_pixels=6,
            get_position= "[lon,lat]",
            get_radius="marker_radius",
            get_fill_color="marker_color",
            get_line_color=[0, 0, 0],
        )

        crowd_count_layer = pdk.Layer(
            "PolygonLayer",
            crowd_sensor_time_data,
            get_polygon="polygon",
            get_fill_color='color',
            get_line_color=[60, 60, 60],
            line_width_min_pixels=1,
            stroked=True,
            filled=True,
            extruded=False,
            wireframe=False,
            pickable=True

        )

        # A black ring around the locations above the threshold (FC5)
        highlight_layer = pdk.Layer(
            "ScatterplotLayer",
            now[now["above_threshold"]],
            pickable=False,
            stroked=True,
            filled=False,
            get_position="[lon,lat]",
            get_radius=70,
            radius_min_pixels=14,
            line_width_min_pixels=4,
            get_line_color=[0, 0, 0],
        )

        label_layer = pdk.Layer(
            "TextLayer",
            now[now["label"] != ""],
            get_position="[lon,lat]",
            get_text="label",
            get_size=14,
            get_color=[0, 0, 0],
            get_pixel_offset=[0, -22],
            background=True,
            get_background_color=[255, 255, 255, 220],
        )

        layers = []
        if "Sensors" in selected_layers:
            layers.append(crowd_count_position_layer)
            layers.append(crowd_count_layer)
            layers.append(highlight_layer)
            layers.append(label_layer)

        if "Trains" in selected_layers:
            arrivals = int(trains.loc[chosen_datetime, "arrivals"])
            departures = int(trains.loc[chosen_datetime, "departures"])
            station = pd.DataFrame([{
                "lat": AMSTERDAM_CENTRAAL["lat"],
                "lon": AMSTERDAM_CENTRAAL["lon"],
                "radius": 30 + 25 * arrivals,
                "tooltip-info": "Amsterdam Centraal\nTime: " + time_label +
                    "\nTrain arrivals: " + str(arrivals) + "\nTrain departures: " + str(departures),
            }])
            layers.append(pdk.Layer(
                "ScatterplotLayer",
                station,
                pickable=True,
                opacity=0.6,
                get_position="[lon,lat]",
                get_radius="radius",
                get_fill_color=[40, 70, 160],
            ))

        if "Vessels" in selected_layers:
            pass # layers.append(vessels_layer) when vessels_layer is defined (FO3)

        # The map is plotted
        st.pydeck_chart(pdk.Deck(
            layers=layers,
            tooltip = {"text": "{tooltip-info}"},
            initial_view_state = view,
            map_style = "light",
        ))
        show_legend()





        st.header("Ongoing events")
        st.caption("Events running on " + time_label)   # FC2
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
sensors, totals, flow, off, off_list = prepare_sensor_data(crowd_count_data)
trains = load_trains()

#These are to change based on the catalogue
min_date = min(program["start_datetime"].dt.date)
max_date = max(program["end_datetime"].dt.date)


chosen_date = st.sidebar.date_input(
    label = "Date",
    format = "DD/MM/YYYY",
    min_value = min_date,
    max_value = max_date,
    )

# FC4: the whole day can be chosen, in steps of 3 minutes like the sensor data
min_time = datetime.time(0, 0)
max_time = datetime.time(23, 57)


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

# FC4: the part of the IJ to look at (zones of data/external/sensor_zones.csv)
chosen_area = st.sidebar.selectbox(
    "Area",
    options = ["Whole IJ"] + sorted(sensors["zone"].dropna().unique()),
)

non_sensors = (
        "hour",
        "timestamp",
        "minute",
        "day",
        "month",
        "weekday",
        "is_weekend",
        )




st.header("IJ's map")
selected_layers = st.pills("Map layers",options = ["Sensors", "Trains", "Vessels"],selection_mode = "multi", default = ["Sensors"])
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
