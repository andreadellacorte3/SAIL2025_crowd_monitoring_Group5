"""SAIL 2025 programme events and the sensor zones relate to (SQ3).

Input files are located in: data/external/
-----------------------------
Manual (made by the roberto):
- sail2025_program.csv : the 85 programme events with start and end times,
  transcribed from the official SAIL 2025 daily programme available on sail.nl.

- sail2025_event_locations.csv : the location of each event as published
  on the sail.nl programme pages (SAIL Amsterdam Foundation).

- sensor_zones.csv : the zone of each LVMA sensor. Assigned by the authors
  from the location names and coordinates in sensor-location.xlsx, with
  three rules: ferry landings are grouped by destination (e.g. "CS - ri.
  NDSM" is the ferry from Central Station to NDSM), walkways near Central
  Station by position (IJBoulevard, east entrance, Oosterdok), and the other
  sensors by neighbourhood (Amsterdam-Noord, eastern docklands, Wallen, Dam).
    
Checked visually on a map with "check_zones.py" with the help of a test notebook.
Any change must be done directly with the csv file, easy to check and change

- event_zone_links.csv : which zones each event is expected to affect, and
  how (at, near, route, access, wide, none), with a confidence level and a
  note. These are our assumptions, written down so they can be reviewed.

Computed in this code:
- load_sensors() : sensor table with location name, family, coordinates and zone.
- load_program_events() : programme catalogue with timezone-aware times.
- program_grid() : which events are running in every 3-minute interval.
- zone_flow() : average flow per metre per zone (both directions per sensor).
- event_effect() : how unusual each single-day event was in its linked zones.
- sensor_totals() : flow per sensor, both walking directions added up.
- sensor_excess() : how far above or below a normal day each sensor was, per interval.
- sensor_totals() : flow per sensor, both walking directions added up.
- sensor_excess() : how far above or below a normal day each sensor was, per interval.
"""
import pandas as pd

# Sensor families as described in the (TIL6022) SAIL 2025 project slides
FAMILY_DESCRIPTIONS = {
    "GASA": "SAIL walkway",
    "GVCV": "Ferry landing",
    "CMSA": "City centre street",
    "GACM": "City centre street",
}

def load_sensors(location_path="data/sensor-location.xlsx",
                 zones_path="data/external/sensor_zones.csv"):
    
    """Return one row per sensor with its location name, family, coordinates and zone."""

    locations = pd.read_excel(location_path)
    sensors = pd.DataFrame({
        "sensor": locations["Objectummer"],
        "location_name": locations["Locatienaam"].str.strip(),
    })
  
    sensors["family"] = sensors["sensor"].str.split("-").str[0]   # "GVCV-11" -> "GVCV"
    sensors["family_description"] = sensors["family"].map(FAMILY_DESCRIPTIONS)
    
    sensors[["lat", "lon"]] = locations["Lat/Long"].str.split(",", expand=True).astype(float)
    zones = pd.read_csv(zones_path)
    sensors = sensors.merge(zones, on="sensor", how="left")
    return sensors.set_index("sensor")

def load_program_events(path="data/external/sail2025_program.csv"):
    
    """Return the programme catalogue with timezone-aware start and end times."""

    program = pd.read_csv(path)
    program["start_datetime"] = pd.to_datetime(program["start_datetime"])
    program["end_datetime"] = pd.to_datetime(program["end_datetime"])
    return program

def program_grid(program, timestamps):
    
    """For every 3-minute interval, mark which programme events are running.

    An interval counts as active when the event has started and not yet ended
    at the interval's timestamp (start <= t < end).
    """
    
    grid = pd.DataFrame(index=timestamps)
    for event in program["event"].unique():
        rows = program[program["event"] == event]
        active = pd.Series(False, index=timestamps)
        for _, row in rows.iterrows():
            active = active | ((timestamps >= row["start_datetime"]) & (timestamps < row["end_datetime"]))
        grid[event] = active
    grid["n_active_events"] = grid.sum(axis=1)
    return grid

def zone_flow(flow, sensors):
  
    """Average flow per metre in each zone.

    The two walking directions of a sensor are added up first, then the
    sensors of a zone are averaged.
    """
    
    sensor_flow = pd.DataFrame(index=flow.index)
    for column in flow.columns:
        sensor = column.split("_")[0]          # "GVCV-11_50" -> "GVCV-11"
        if sensor in sensor_flow.columns:
            sensor_flow[sensor] = sensor_flow[sensor] + flow[column]
        else:
            sensor_flow[sensor] = flow[column]

    zones = pd.DataFrame(index=flow.index)
    for zone in sensors["zone"].unique():
        members = [s for s in sensors.index[sensors["zone"] == zone] if s in sensor_flow.columns]
        zones[zone] = sensor_flow[members].mean(axis=1)
    return zones

def event_effect(zones, program, links, day_start="10:00", day_end="21:57", smooth=10):
    """Was a zone unusually busy during a single-day event, compared with the other days?

    For every event-zone pair in the links table (relation not "none"):
    1. Each day's flow is divided by that day's mean flow between day_start
       and day_end, so a generally busier day does not count as an effect.
       The relative flow is smoothed over 30 minutes, because ferry landings
       count people in bursts (one ferry, then nothing).
    2. For each day, the excess is that day's relative flow minus the median
       of the other days at the same clock time, in % of the day's mean flow.
    3. peak_excess_pct is the highest excess on the event day within the
       official event time; rank_of_days says where the event day ranks among
       all days on that same measure (1 = most unusual).
    Only events that take place on one day are measured.
    """
    results = []
    days = sorted(set(zones.index.date))
    for _, link in links[links["relation"] != "none"].iterrows():
        rows = program[program["event"] == link["event"]]
        if len(rows) != 1 or link["zone"] not in zones.columns:
            continue
        start = rows["start_datetime"].iloc[0]
        end = rows["end_datetime"].iloc[0]
        flow = zones[link["zone"]]

        # one column per day, one row per clock time, flow relative to the day's level
        table = {}
        for day in days:
            day_flow = flow[flow.index.date == day]
            level = day_flow.between_time(day_start, day_end).mean()
            relative = day_flow / level if level > 0 else day_flow * float("nan")
            relative = relative.rolling(smooth, center=True, min_periods=1).mean()   # 10 x 3 min = 30 min
            relative.index = relative.index.time
            table[day] = relative
        table = pd.DataFrame(table)
        in_window = (table.index >= start.time()) & (table.index < end.time())

        excess = {}
        for day in days:
            typical = table.drop(columns=day).median(axis=1)
            excess[day] = (table[day] - typical)[in_window].max()

        excess = pd.Series(excess)
        event_day = start.date()
        results.append({
            "event": link["event"], "zone": link["zone"],
            "relation": link["relation"], "confidence": link["confidence"],
            "peak_excess_pct": round(excess[event_day] * 100, 1),
            "rank_of_days": int(excess.rank(ascending=False)[event_day]) if excess.notna().all() else None,
        })
    return pd.DataFrame(results).sort_values("peak_excess_pct", ascending=False)

def sensor_totals(flow):
    """Add up the two walking directions of every sensor (one column per sensor)."""
    totals = pd.DataFrame(index=flow.index)
    for column in flow.columns:
        sensor = column.split("_")[0]          # "GVCV-11_50" -> "GVCV-11"
        if sensor in totals.columns:
            totals[sensor] = totals[sensor] + flow[column]
        else:
            totals[sensor] = flow[column]
    return totals


def sensor_excess(totals, day_start="10:00", day_end="21:57", smooth=10, min_level=0.5):
    """For every sensor and 3-minute interval: how far above or below a normal day it was.

    Each day's flow is divided by that day's mean flow between day_start and
    day_end and smoothed over 30 minutes. The excess is that value minus the
    median of the other days at the same clock time, in % of the day's mean
    flow (+40 means 40% of a normal day's average above what is usual then).
    Sensors whose mean flow over all days is below min_level (ped/m/min) are
    nearly dead (GASA-06, GVCV-09) and are left empty.
    """
    overall = totals.between_time(day_start, day_end).mean()
    totals = totals.copy()
    totals.loc[:, overall < min_level] = float("nan")       # nearly dead sensors
    days = sorted(set(totals.index.date))
    relative = {}
    for day in days:
        day_flow = totals[totals.index.date == day]
        level = day_flow.between_time(day_start, day_end).mean()      # one level per sensor
        rel = day_flow / level.where(level > 0)                        # dead sensors become empty
        rel = rel.rolling(smooth, center=True, min_periods=1).mean()   # 10 x 3 min = 30 min
        rel.index = rel.index.time
        relative[day] = rel

    excess = []
    for day in days:
        others = pd.concat([relative[d] for d in days if d != day])
        typical = others.groupby(level=0).median()                     # median per clock time
        day_excess = (relative[day] - typical) * 100
        day_excess.index = totals.index[totals.index.date == day]
        excess.append(day_excess)
    return pd.concat(excess)