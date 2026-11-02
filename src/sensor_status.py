"""Which sensors were off, and how busy every sensor was, for the dashboard.

Both follow the requirements of our TIL4030 design report (chapter 2):
- FC3: mark a sensor that is off instead of showing zero counts.
  A sensor counts as off when both directions report zero for at least one
  hour (20 intervals of 3 minutes) while similar sensors (same family:
  SAIL walkway, ferry landing or city centre street) still count people.
- FC5: highlight a location when its flow per metre exceeds the threshold.
  The levels of service A to F are the ones of Fruin (1971) for walkways,
  converted from persons per foot per minute to persons per metre per minute.
"""
import pandas as pd

# Upper limit of each level of service, in persons per metre per minute (Fruin, 1971).
# Above 82 the level is F.
LOS_LIMITS = {"A": 23, "B": 33, "C": 49, "D": 66, "E": 82}


def level_of_service(flow):
    """Return the level of service (A to F) of a flow per metre, or "" when the flow is unknown."""
    if pd.isna(flow):
        return ""
    for level, limit in LOS_LIMITS.items():
        if flow <= limit:
            return level
    return "F"


def find_off_sensors(totals, sensors, min_intervals=20):
    """True in every 3-minute interval in which a sensor was off (FC3).

    totals: pedestrians per sensor and interval, both directions added up
            (sensor_totals() in events.py).
    sensors: the table of load_sensors() in events.py, for the family of each sensor.
    A run of zeros of at least min_intervals intervals counts as off when the
    similar sensors counted people during that run.
    """
    off = pd.DataFrame(False, index=totals.index, columns=totals.columns)
    for sensor in totals.columns:
        family = sensors.loc[sensor, "family_description"]
        similar = [s for s in totals.columns
                   if s != sensor and sensors.loc[s, "family_description"] == family]
        others_counting = totals[similar].sum(axis=1) > 0

        zero = totals[sensor] == 0
        run = (zero != zero.shift()).cumsum()     # every run of zeros gets its own number
        for _, period in zero[zero].groupby(run[zero]):
            if len(period) >= min_intervals and others_counting[period.index].any():
                off.loc[period.index, sensor] = True
    return off


def off_periods(off):
    """One row per period in which a sensor was off, with its first and last interval."""
    rows = []
    for sensor in off.columns:
        is_off = off[sensor]
        run = (is_off != is_off.shift()).cumsum()
        for _, period in is_off[is_off].groupby(run[is_off]):
            rows.append({"sensor": sensor, "start": period.index[0], "end": period.index[-1]})
    return pd.DataFrame(rows, columns=["sensor", "start", "end"])
