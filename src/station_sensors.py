"""Pedestrian counts at the sensors near Amsterdam Centraal, every 3 minutes.

Used to compare the crowd around the station with the trains (see trains.py).
"""
from pathlib import Path

import numpy as np
import pandas as pd

DATA_FILE = (Path(__file__).resolve().parent.parent / "data"
             / "SAIL2025_LVMA_data_3min_20August-25August2025_flow.csv")

# The 13 sensors within about 400 m of Amsterdam Centraal, on the station side of the IJ
STATION_SENSORS = [
    "GASA-01-A1", "GASA-01-A2", "GASA-01-B", "GASA-01-C",       # IJboulevard, behind the station
    "GVCV-01", "GVCV-03", "GVCV-04", "GVCV-05-A", "GVCV-05-B",  # ferry landings
    "GACM-04",                                                  # Damrak, in front of the station
    "GASA-02-01", "GASA-02-02", "GASA-04",                      # east side of the station
]

# Periods in which a sensor was off: the file shows 0 there, but nobody was counted.
# Each entry is (sensors, first interval, last interval). Zeros at the ferry landings
# (GVCV) are kept, because people arrive there in waves and the count can really be 0.
OFF_PERIODS = [
    ([s for s in STATION_SENSORS if s.startswith("GASA")], "2025-08-20 00:00", "2025-08-20 08:09"),
    (["GASA-01-A1", "GASA-01-A2"], "2025-08-22 09:15", "2025-08-22 10:15"),
    (["GASA-02-01", "GASA-02-02"], "2025-08-23 10:48", "2025-08-23 13:24"),
]


def station_counts():
    """Return the pedestrians counted every 3 minutes at the sensors near Amsterdam Centraal.

    The result has one column per sensor (the two walking directions added up) and one
    row per 3-minute interval from 20 to 24 August 2025, the same intervals as
    train_counts(). Intervals in which a sensor was off are NaN, not 0.
    For the total of all sensors use station_counts().sum(axis=1).
    """
    flow = pd.read_csv(DATA_FILE)
    flow.index = pd.to_datetime(flow["timestamp"])

    people = pd.DataFrame(index=flow.index)
    for sensor in STATION_SENSORS:
        # the file has one column per direction, named <sensor>_<direction in degrees>
        directions = [c for c in flow.columns if c.rsplit("_", 1)[0] == sensor]
        people[sensor] = flow[directions].sum(axis=1).astype(float)  # float, so NaN is allowed

    for sensors, first, last in OFF_PERIODS:
        people.loc[first:last, sensors] = np.nan
    return people


if __name__ == "__main__":
    people = station_counts()
    print(people.shape)
    print(people.isna().sum())
    print(people.loc["2025-08-20 08:03":"2025-08-20 08:18", ["GACM-04", "GASA-01-B", "GASA-04"]])
