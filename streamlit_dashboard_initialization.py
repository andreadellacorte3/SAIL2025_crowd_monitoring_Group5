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
from Population_of_dictionary_with_pedestrian_data import load_data as load_pedestrian_data
from find_start_end_datetimes import load_program
import time
import numpy as np
from src.events import load_sensors, sensor_totals
from src.flow import load_effective_widths, flow_per_metre
from src.trains import train_counts
from src.sensor_status import LOS_LIMITS, level_of_service, find_off_sensors, off_periods
from src.event_impact import show_event_impact
from src.train_pedestrian_graph import show_trains_impact
from src.day_overview import show_day_overview
import os

# Colour of each level of service: green when it is fine, then yellow and red, black for a crisis (NFC1).
# Every level is darker than the one before, so the levels can be told apart also without seeing colours.
LOS_COLORS = {"A": [199, 233, 192],"B": [253, 208, 73],"C": [253, 141, 60],
    "D": [215, 48, 39],"E": [127, 0, 0],"F": [0, 0, 0]}
OFF_COLOR = [150, 150, 150]

# Flow per metre (persons/m/min) above which a location is highlighted on the map (FC5).
# The report says the threshold differs between walkways, streets and ferry landings,
# but the values are not decided yet: for now all three use the start of level D.
HIGHLIGHT_THRESHOLD = {"SAIL walkway": 49,"Ferry landing": 49,"City centre street": 49}

MODERATE_THRESHOLD = {"SAIL walkway": 35,"Ferry landing": 35,"City centre street": 35}

AMSTERDAM_CENTRAAL = {"lat": 52.3789, "lon": 4.9003}


@st.cache_data(show_spinner = False)
def get_processed_vessels():
    parquet_cache = "data/processed_vessels.parquet"
    if os.path.exists(parquet_cache):
        return pd.read_parquet(parquet_cache)

    csv_file = "Vesselposition_data_20-24Aug2025.csv"
    if not os.path.exists(csv_file):
        csv_file = os.path.join("data", "Vesselposition_data_20-24Aug2025.csv")

    cols_to_load = [
        "mmsi-number", 
        "name", 
        "destination", 
        "sub-category", 
        "update-time", 
        "lat", 
        "lon", 
        "orientation"
    ]
    
    vessels_df = pd.read_csv(csv_file, engine = "pyarrow", usecols = cols_to_load)

    mask_1 = ["Exhibition Vessel","Frigate","Museum, Stationary",
        "Passenger Ship","Passenger/Cruise","Sail Training Ship",
        "Sailing Vessel","Yacht","Yacht (Sailing)",]

    is_target_cat = vessels_df["sub-category"].isin(mask_1)
    is_sail_dest = (
        vessels_df["sub-category"].isna() 
        & vessels_df["destination"].str.contains("SAIL", case=False, na=False)
    )

    ships_with_data = vessels_df[is_target_cat | is_sail_dest].dropna(subset=["lat", "lon"])    

    del vessels_df

    ships_with_data["update-time"] = (
        pd.to_datetime(
        ships_with_data["update-time"], utc=True, format="ISO8601", cache = True)
         .dt.tz_convert("Europe/Amsterdam")#.dt.strftime("%H%M").astype(int)
    )

    columns_to_be_used = [
        "mmsi-number",
        "name",
        "lat",
        "lon",
        "update-time",
        "orientation",
    ]

    ships_with_data = ships_with_data[columns_to_be_used].dropna(subset=["lat", "lon"])
    to_return = (
        ships_with_data
        .sort_values(by=["mmsi-number", "update-time"])
        .reset_index(drop=True)
        )

    to_return.to_parquet(parquet_cache, index = False)
    return to_return




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
@st.cache_data(show_spinner = False)
def compute_alarms(flow, off, sensors, thresholds, min_intervals = 1):
    """Boolean table (same shape as flow): True when a sensor is in alarm at that interval.

    An alarm needs `min_intervals` consecutive 3-minute intervals above the threshold,
    so a single noisy peak does not count. Off sensors never raise an alarm (FC3).
    """
    cols = [c for c in flow.columns if c in sensors.index and c in off.columns]
    limits = sensors.loc[cols, "family_description"].map(thresholds)

    above = flow[cols].gt(limits, axis = 1) & ~off[cols]
    # True only if the last `min_intervals` intervals were all above the threshold
    return above.rolling(min_intervals).sum().eq(min_intervals)


def alarm_summary(alarms, flow, sensors, until = None):
    """One row per sensor: number of alarm episodes, minutes in alarm and peak flow."""
    if until is not None:
        alarms = alarms[alarms.index <= until]
    flow = flow.loc[alarms.index]   # peak flow of the same period as the alarms (the chosen day)

    # an episode starts when the alarm is on now but was off in the previous interval
    starts = alarms & ~alarms.shift(1, fill_value = False)

    summary = pd.DataFrame({"location": sensors.loc[alarms.columns, "location_name"],
        "alarm episodes": starts.sum(),
        "minutes in alarm": alarms.sum() * 3,
        "peak flow (persons/m/min)": flow[alarms.columns].max().round(1)})
    return summary.sort_values("alarm episodes", ascending = False)


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
    text += (f'<span style="display:inline-block;width:14px;height:14px;background:purple;border-radius:50%;border:1px solid #444;vertical-align:middle;margin:0 4px 0 12px"></span>' +
        ' Vessels')

    text += "&nbsp;&nbsp;&nbsp;&nbsp;Arc size = pedestrians counted, one arc per walking direction"
    st.markdown(text, unsafe_allow_html = True, width = "stretch")


def show_alarm_summary(level_alarms, in_view, thresholds, current_datetime, min_intervals, window):
    day_start = datetime.datetime.combine(chosen_date, datetime.time(0, 0))
    day_end = day_start + datetime.timedelta(days = 1)
    day_alarms = level_alarms[(level_alarms.index >= day_start) & (level_alarms.index < day_end)]

    until = current_datetime if window == "Chosen day until chosen time" else None
    summary = alarm_summary(day_alarms, flow, sensors, until)

    # only the sensors of the chosen area (FC4)
    if chosen_area != "Whole IJ":
        summary = summary[summary.index.isin(in_view.index)]

    limits = ", ".join(k + ": " + str(v) for k, v in thresholds.items())
    st.caption("Flow per metre above the threshold (" + limits + ") for at least "
               + str(min_intervals * 3) + " minutes. Off sensors are excluded.")
    
    col_x, col_y = st.columns(2)
    col_x.metric("Total alarm episodes", int(summary["alarm episodes"].sum()))
    col_y.metric("Sensors with at least one alarm", int((summary["alarm episodes"] > 0).sum()))

    st.dataframe(summary[summary["alarm episodes"] > 0])
    st.bar_chart(summary["alarm episodes"])

# @st.fragment
def update_visuals(chosen_time: datetime.time):
    st.header("IJ's map")
    selected_layers = st.pills(
        "Map layers",
        options = ["Sensors", "Trains", "Vessels"],
        selection_mode = "multi", 
        default = ["Sensors","Vessels","Trains"],
        key = "map_layers_pills"
        )

    chosen_datetime = datetime.datetime.combine(chosen_date,chosen_time)
    interval_end = chosen_datetime + datetime.timedelta(minutes = 3)
    # FC2: every view says which moment its data belong to
    time_label = chosen_datetime.strftime("%A %d %B %Y, %H:%M") + "-" + interval_end.strftime("%H:%M")

    if chosen_datetime not in totals.index:
        st.warning("There are no sensor data for " + time_label)
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
    (crowd_count_data.index == "name_without_orientation")].T
    crowd_sensor_time_data.drop(["minute","day","weekday","month","hour","is_weekend","timestamp"], inplace = True)



    crowd_sensor_time_data["orientation"] = crowd_sensor_time_data["orientation"].astype(int,errors = "ignore")
    crowd_sensor_time_data = crowd_sensor_time_data.rename(columns={crowd_sensor_time_data.columns[0]: "count"})
    crowd_sensor_time_data["sensor"] = crowd_sensor_time_data["name_without_orientation"]
    crowd_sensor_time_data = crowd_sensor_time_data[crowd_sensor_time_data["sensor"].isin(now.index)]

    # An off sensor gets no arcs: its zeros are not real counts (FC3)
    sensor_off = crowd_sensor_time_data["sensor"].map(now["off"]).astype(bool)
    crowd_sensor_time_data.loc[sensor_off, "count"] = 0


    crowd_sensor_time_data["polygon"] = crowd_sensor_time_data.apply(lambda row: generate_arc_polygon(lon= float(row["long"]),
            lat=float(row["lat"]),
            direction_degrees=int(row["orientation"]),
            count= int(row["count"])), axis = 1)

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
    view = pdk.ViewState(latitude = (in_view["lat"].min() + in_view["lat"].max()) / 2,
        longitude = (in_view["lon"].min() + in_view["lon"].max()) / 2,
        zoom = zoom)

    # with visuals.container():
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
    crowd_count_position_layer = pdk.Layer("ScatterplotLayer",now,
        pickable=True,
        opacity=0.9,
        stroked=True,
        filled=True,
        line_width_min_pixels=1,
        radius_min_pixels=6,
        get_position= "[lon,lat]",
        get_radius="marker_radius",
        get_fill_color="marker_color",
        get_line_color=[0, 0, 0])

    crowd_count_layer = pdk.Layer("PolygonLayer",crowd_sensor_time_data,
        get_polygon="polygon",
        get_fill_color='color',
        get_line_color=[60, 60, 60],
        line_width_min_pixels=1,
        stroked=True,
        filled=True,
        extruded=False,
        wireframe=False,
        pickable=True)

    # A black ring around the locations above the threshold (FC5)
    highlight_layer = pdk.Layer("ScatterplotLayer",now[now["above_threshold"]],
        pickable=False,
        stroked=True,
        filled=False,
        get_position="[lon,lat]",
        get_radius=70,
        radius_min_pixels=14,
        line_width_min_pixels=4,
        get_line_color=[0, 0, 0])

    label_layer = pdk.Layer("TextLayer",now[now["label"] != ""],
        get_position="[lon,lat]",
        get_text="label",
        get_size=14,
        get_color=[0, 0, 0],
        get_pixel_offset=[0, -22],
        background=True,
        get_background_color=[255, 255, 255, 220])

    vessels_now = vessels_data[
            (vessels_data["update-time"] <= pd.Timestamp(chosen_datetime, tz="Europe/Amsterdam") + datetime.timedelta(minutes = 2))
        ].drop_duplicates(subset="mmsi-number", keep = "last")
    vessels_layer = pdk.Layer(
        "ScatterplotLayer",
        vessels_now,
        stroked=True,
        filled=True,
        line_width_min_pixels=1,
        radius_min_pixels=6,
        get_position= "[lon,lat]",
        get_radius=10,
        get_fill_color=[128,0,128],
        get_line_color=[0, 0, 0])


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
        layers.append(pdk.Layer("ScatterplotLayer",
            station,
            pickable=True,
            opacity=0.6,
            get_position="[lon,lat]",
            get_radius="radius",
            get_fill_color=[40, 70, 160]))

    if "Vessels" in selected_layers:
        layers.append(vessels_layer) 

    # The map is plotted
    st.pydeck_chart(
        pdk.Deck(
            layers=layers,
            tooltip = {"text": "{tooltip-info}"},
            initial_view_state = view,
            map_style = "light"
            ),
        key = "IJ Map"
        )
    show_legend()


    st.header("Ongoing events")
    st.caption("Events running on " + time_label)   # FC2
    st.dataframe(program[
        (program["start_datetime"] <= chosen_datetime) &
        (program["end_datetime"] >= chosen_datetime)]
        [["Start","End"]])

    st.header("Flow alarms per sensor")
    # the alarm options only change this section, so they are here and not in the sidebar
    col_on, col_min, col_window = st.columns(3)
    show_alarms = col_on.toggle("Count alarms per sensor", key = "show_alarms")
    min_intervals = col_min.slider("Minimum duration of an alarm (intervals of 3 min)",
        min_value = 1, max_value = 5, value = 1, disabled = not show_alarms, key = "alarm_min_intervals")
    window = col_window.radio("Count alarms over",
        options = ["Whole chosen day", "Chosen day until chosen time"],
        disabled = not show_alarms, key = "alarm_window")

    if show_alarms:
        alarms_critical = compute_alarms(flow, off, sensors, HIGHLIGHT_THRESHOLD, min_intervals)
        alarms_moderate = compute_alarms(flow, off, sensors, MODERATE_THRESHOLD, min_intervals)
        tab_critical, tab_moderate = st.tabs(["Critical", "Moderate"])
        with tab_critical:
            show_alarm_summary(alarms_critical, in_view, HIGHLIGHT_THRESHOLD, chosen_datetime,
                min_intervals, window)
        with tab_moderate:
            show_alarm_summary(alarms_moderate, in_view, MODERATE_THRESHOLD, chosen_datetime,
                min_intervals, window)

    show_trains_impact(chosen_datetime)
    
    return


# set the streamlit app main page configuration
st.set_page_config(page_title="SAIL 2025 crowd monitoring dashboard", layout="wide",page_icon = ":sailboat:")
st.title("SAIL 2025 crowd monitoring dashboard", anchor = False)
st.sidebar.header("Filters")

with st.spinner("Processing 4.7 GB vessel dataset. This will take a moment..."):
    vessels_data = get_processed_vessels()
    
if "toast_shown" not in st.session_state:
    st.session_state.toast_shown = True
    st.toast("Vessel data loaded successfully!", icon = "✅")

crowd_count_data = load_pedestrian_data()
program  = load_program()
sensors, totals, flow, off, off_list = prepare_sensor_data(crowd_count_data)
trains = load_trains()

#These are to change based on the catalogue
min_date = min(program["start_datetime"].dt.date)
max_date = max(program["end_datetime"].dt.date)


chosen_date = st.sidebar.date_input(label = "Date",format = "DD/MM/YYYY",min_value = min_date,max_value = max_date, value = datetime.date(2025,8,20))

# FC4: the whole day can be chosen, in steps of 3 minutes like the sensor data
min_time = datetime.time(0, 0)
max_time = datetime.time(23, 57)

if "current_time" not in st.session_state:
    st.session_state.current_time = datetime.time(19, 0)
if "playing" not in st.session_state:
    st.session_state.playing = False

def sync_time():
    if "main_time_slider" in st.session_state:
        st.session_state.current_time = st.session_state.main_time_slider
    else:
        st.session_state.main_time_slider = st.session_state.current_time

# --- ADVANCE TIME BEFORE SLIDER RENDERS ---
if st.session_state.playing:
    today = datetime.date.today()
    current_dt = datetime.datetime.combine(today, st.session_state.current_time)
    next_dt = current_dt + datetime.timedelta(minutes=3)
    
    if next_dt.time() > max_time:
        st.session_state.playing = False
    else:
        st.session_state.current_time = next_dt.time()
        st.session_state.main_time_slider = next_dt.time() # Safely updates the slider

time_slider = st.sidebar.empty()

if "main_time_slider" not in st.session_state:
    st.session_state.main_time_slider = st.session_state.current_time

chosen_time = time_slider.slider(
    # value=st.session_state.current_time,  # NO MORE HARDCODED 14:00
    label="Time",
    format="HH:mm",
    min_value=min_time,
    max_value=max_time,
    step=datetime.timedelta(minutes=3), 
    key="main_time_slider", 
    on_change=sync_time
)

chosen_time = st.session_state.current_time
time_container = st.sidebar.container()

chosen_datetime = datetime.datetime.combine(chosen_date,chosen_time)

# FC4: the part of the IJ to look at (zones of data/external/sensor_zones.csv)
chosen_area = st.sidebar.selectbox("Area",options = ["Whole IJ"] + sorted(sensors["zone"].dropna().unique()))

non_sensors = ("hour","timestamp","minute","day","month","weekday","is_weekend")


# visuals = st.empty()

# update_visuals(chosen_time = chosen_time)
col1, col2 = time_container.columns(2)
play = col1.button("▶  Play")
stop = col2.button("⏹  Stop")
if play:
    st.session_state.playing = True
    st.rerun()
if stop:
    st.session_state.playing = False
    st.rerun()
speed = time_container.number_input("Play speed",value = 1,min_value = 0,step = 1)
time_container.divider()

# if play.button("▶  Play"):
#     today = datetime.date.today()
#     max_dt = datetime.datetime.combine(today,max_time)
#     chosen_dt = datetime.datetime.combine(today,chosen_time)
#     max_range = int((max_dt-chosen_dt)/ datetime.timedelta(minutes = 3)) + 1
#     range_to_go = [(chosen_dt + datetime.timedelta(minutes = i*3)).time() for i in range(max_range)]
#     for i in range_to_go:
#         chosen_time = time_slider.slider(label = "Time",min_value=min_time,max_value=max_time,value=i,
#             step=datetime.timedelta(minutes=3))
#         update_visuals(chosen_time)
#         time.sleep(0.5/speed)

update_visuals(chosen_time=chosen_time)
# The day overview and the event analysis summarise the whole day, so they do not change
# with the time. They are left out while playing, so the animation stays smooth.

show_day_overview(chosen_date, totals, flow, off, vessels_data, sensors, chosen_area)
show_event_impact(chosen_date)

# --- SLEEP AND RERUN AT THE END ---
if st.session_state.playing:
    safe_speed = max(speed, 0.1) 
    time.sleep(1 / safe_speed)
    st.rerun()