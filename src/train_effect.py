"""Do people near Amsterdam Centraal react to train arrivals? (SQ4)

Compares the trains per 3 minutes (trains.py) with the pedestrians per 3 minutes at
the sensors near the station (station_sensors.py). The 3-minute intervals are put in
groups by the number of trains that arrived in them. For each group we look at the
people counted in the next 15 minutes, compared with the average of that hour.
"""
import pandas as pd

from station_sensors import station_counts
from trains import train_counts

HOURS = (9, 22)   # only compare during the day, when the sensors count most people
WINDOW = 20       # 20 intervals of 3 minutes = 1 hour
AFTER = 5         # the interval of the train and the 4 after it = 15 minutes
GROUPS = [-1, 1, 2, 3, 10]                  # 0-1 trains, 2, 3, 4 or more
LABELS = ["0-1", "2", "3", "4 or more"]


def daytime(index):
    """True for the intervals between HOURS[0] and HOURS[1]."""
    return (index.hour >= HOURS[0]) & (index.hour < HOURS[1])


def compared_to_hour(series, window=WINDOW):
    """Count in % above (+) or below (-) the average of the hour around it.

    People increase during the day. Without this step a raw count says more about
    the time of day than about the trains.
    """
    average = series.rolling(window, center=True, min_periods=window // 2).mean()
    return (series / average - 1) * 100


def next_minutes(series, after=AFTER):
    """For each interval: the mean of compared_to_hour over that interval and the next ones."""
    relative = compared_to_hour(series)
    return pd.concat([relative.shift(-k) for k in range(after)], axis=1).mean(axis=1)


def people_after_trains(arrivals, people, after=AFTER):
    """Mean % above or below the hour in the 15 minutes after 0-1, 2, 3 or 4+ train arrivals.

    arrivals: Series with the trains per interval (train_counts()["arrivals"]).
    people: DataFrame with one column per sensor or area, same intervals as `arrivals`.
    Returns one row per group of arrivals and one column per sensor or area.
    Intervals in which a sensor was off (NaN) are left out.
    """
    day = daytime(people.index)
    groups = pd.cut(arrivals, GROUPS, labels=LABELS)
    result = {column: next_minutes(people[column], after)[day].groupby(groups[day], observed=True).mean()
              for column in people.columns}
    return pd.DataFrame(result).rename_axis(index="trains arrived in 3 minutes")


if __name__ == "__main__":
    people = station_counts()
    trains = train_counts()
    people["all sensors"] = people.sum(axis=1, skipna=False)
    print(people_after_trains(trains["arrivals"], people).round(1).to_string())
