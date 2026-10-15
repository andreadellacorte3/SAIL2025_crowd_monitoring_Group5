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

Computed here (by code):
- load_sensors() : sensor table with location name, family, coordinates and zone.
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