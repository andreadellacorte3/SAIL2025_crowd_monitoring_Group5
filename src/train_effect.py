"""Do people near Amsterdam Centraal react to train arrivals? (sub-question 5)

Compares the trains per 3 minutes (trains.py) with the pedestrians per 3 minutes at
the sensors near the station (station_sensors.py), for delays of 0 to 21 minutes.
"""
import numpy as np
import pandas as pd
import plotly.express as px

from station_sensors import station_counts
from trains import train_counts

HOURS = (9, 22)   # only compare during the day, when the sensors count most people
WINDOW = 20       # 20 intervals of 3 minutes = 1 hour
MAX_LAG = 7       # 7 intervals of 3 minutes = 21 minutes


def remove_daily_pattern(series, window=WINDOW):
    """Subtract the moving average of the last and next hour.

    Trains and people both increase during the day. Without this step they look related
    just because of the time of day, not because people react to trains.
    """
    return series - series.rolling(window, center=True, min_periods=window // 2).mean()


def lagged_correlations(trains, people, max_lag=MAX_LAG):
    """Correlation between the trains and the people counted `lag` intervals later.

    trains: Series with the trains per interval (for example train_counts()["arrivals"]).
    people: DataFrame with one column per sensor, same intervals as `trains`.
    Returns a DataFrame with one row per sensor and one column per delay in minutes.
    Intervals in which a sensor was off (NaN) are left out of its correlation.
    """
    trains = remove_daily_pattern(trains)
    people = people.apply(remove_daily_pattern)
    daytime = (people.index.hour >= HOURS[0]) & (people.index.hour < HOURS[1])

    result = {}
    for lag in range(max_lag + 1):
        later = people.shift(-lag)   # the people counted `lag` intervals after the train
        result[3 * lag] = [trains[daytime].corr(later[sensor][daytime]) for sensor in people.columns]
    return pd.DataFrame(result, index=people.columns).rename_axis(columns="delay (minutes)")


def correlation_heatmap(correlations, title):
    """Heat map: sensors on the vertical axis, delay after the train on the horizontal axis."""
    return px.imshow(correlations, zmin=-0.3, zmax=0.3, color_continuous_scale="RdBu_r",
                     aspect="auto", labels={"x": "delay after the train (minutes)", "y": "sensor",
                                            "color": "correlation"}, title=title)


if __name__ == "__main__":
    people = station_counts()
    trains = train_counts()
    arrivals = lagged_correlations(trains["arrivals"], people)
    print(arrivals.round(2).to_string())
    total = lagged_correlations(trains["arrivals"], people.sum(axis=1, skipna=False).to_frame("total"))
    print("\nTotal of all sensors (intervals with a sensor off are left out):")
    print(total.round(2).to_string())
