"""Figures for SQ3: do SAIL events explain the peaks in the pedestrian counts?

The numbers come from src/events.py; this file only draws them.
"""
import matplotlib.pyplot as plt
import pandas as pd


def daily_profiles(flow, day_start="10:00", day_end="21:57", smooth=10):
    """One column per day, one row per clock time: flow as % of that day's average.

    Same scaling as sensor_excess() in events.py: 100 = an average moment of
    that day (between day_start and day_end), smoothed over 30 minutes.
    flow: one time series (a zone from zone_flow() or a sensor from sensor_totals()).
    """
    profiles = {}
    for day in sorted(set(flow.index.date)):
        day_flow = flow[flow.index.date == day]
        level = day_flow.between_time(day_start, day_end).mean()
        relative = day_flow / level * 100
        relative = relative.rolling(smooth, center=True, min_periods=1).mean()
        relative.index = relative.index.time
        profiles[day] = relative
    return pd.DataFrame(profiles)


def plot_event_day(flow, program, event, title=None, ax=None):
    """The event day against the other days, for one zone or sensor.

    Red line: the event day. Dashed line: a normal day (median of the other days
    at the same clock time). Grey band: the range of the other days.
    Gold area: the official event time.
    """
    row = program[program["event"] == event].iloc[0]
    if program.loc[program["event"] == event, "date"].nunique() > 1:
        raise ValueError(f"{event} runs on more than one day, so there is no normal day to compare with")
    event_day = row["start_datetime"].date()

    profiles = daily_profiles(flow)
    others = profiles.drop(columns=event_day)
    # clock times as hours (14.5 = 14:30), so the x axis is just a number
    hours = [t.hour + t.minute / 60 for t in profiles.index]

    if ax is None:
        _, ax = plt.subplots(figsize=(10, 4))
    ax.fill_between(hours, others.min(axis=1), others.max(axis=1),
                    color="grey", alpha=0.25, label="range of the other days (max-min)")
    ax.plot(hours, others.median(axis=1), color="grey", linestyle="--", label="normal day (median of the others)")
    ax.plot(hours, profiles[event_day], color="#c1121f", linewidth=2, label=f"{event_day:%A} (event day)")

    start = row["start_datetime"].hour + row["start_datetime"].minute / 60
    end = row["end_datetime"].hour + row["end_datetime"].minute / 60
    ax.axvspan(start, end, color="gold", alpha=0.2, label=f"{event} {row['start_time']}–{row['end_time']}")

    ax.set_xlim(8, 24)
    ax.set_xticks(range(8, 25, 2))
    ax.set_xlabel("time of day (h)")
    ax.set_ylabel("busyness (100 = average of that day)")
    ax.set_title(title or f"{flow.name}: {event} day vs the other SAIL days")
    ax.axhline(100, color="black", linewidth=0.8)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2, fontsize=8)
    return ax
