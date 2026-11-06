"""For the day and area chosen in the sidebar, made from the data the dashboard has
already loaded:
- three KPIs: busiest moment and busiest place (SQ2), SAIL ships seen (SQ5)
- pedestrians during the day by type of place (SQ2: when, and where)
- the places with the highest flow per metre (SQ2: where)
"""

import streamlit as st

# short names, so they fit in the bar chart
SHORT_NAMES = {
    "CS_IJBOULEVARD": "CS, IJ side", "CS_EAST": "CS, east", "OOSTERDOK": "Oosterdok",
    "FERRY_CS_NDSM": "Ferry CS-NDSM", "FERRY_CS_BUIKSLOTERWEG": "Ferry CS-Buiksloterweg",
    "FERRY_CS_IJPLEIN": "Ferry CS-IJplein", "FERRY_PONTSTEIGER": "Ferry Pontsteiger",
    "NDSM": "NDSM", "BUIKSLOTERWEG": "Buiksloterweg", "NOORDERPARK": "Noorderpark",
    "AZARTPLEIN": "Azartplein", "ZEEBURG": "Zeeburg", "CENTRE_WALLEN": "Wallen", "CENTRE_DAM": "Dam",
}
PLACE_TYPES = {"SAIL walkway": "SAIL walkways", "Ferry landing": "Ferry landings",
               "City centre street": "City centre streets"}


@st.cache_data(show_spinner=False)
def ships_seen(_vessels, chosen_date):
    """Number of different SAIL ships that sent a position on the chosen day.

    The underscore tells streamlit not to hash the large vessel table; the
    result is stored per chosen_date.
    """
    times = _vessels["update-time"].dt.tz_localize(None)    # same clock time as the sensor data
    return _vessels.loc[times.dt.date == chosen_date, "mmsi-number"].nunique()


def show_day_overview(chosen_date, totals, flow, off, vessels, sensors, chosen_area):
    """Section of the dashboard with the main numbers of the chosen day."""
    st.divider()
    st.header("The day in numbers")
    st.caption(f"{chosen_date:%A %d August 2025}, {chosen_area}. Sensors that were off are left out.")

    # sensors of the chosen area, on the chosen day; off sensors do not count
    in_area = sensors.index if chosen_area == "Whole IJ" else sensors.index[sensors["zone"] == chosen_area]
    cols = [s for s in totals.columns if s in in_area and s in off.columns]
    day = totals.index.date == chosen_date
    is_off = off.loc[day, cols]
    people = totals.loc[day, cols].where(~is_off)
    flow_day = flow.loc[day, cols].where(~is_off)

    # where: the highest flow per metre per place (zone for the whole IJ, sensor inside a zone)
    if chosen_area == "Whole IJ":
        peak = flow_day.max().groupby(sensors["zone"]).max()
        peak.index = peak.index.map(lambda z: SHORT_NAMES.get(z, z))
    else:
        peak = flow_day.max()
        peak.index = sensors.loc[peak.index, "location_name"]
    peak = peak.dropna().sort_values(ascending=False).head(8).rename("highest flow (persons/m/min)")

    # KPIs
    total_people = people.sum(axis=1, min_count=1)
    col1, col2, col3 = st.columns(3)
    col1.metric("Busiest moment", f"{total_people.idxmax():%H:%M}",
                help=f"{total_people.max():,.0f} pedestrians counted in 3 minutes.")
    col2.metric("Highest flow (persons/m/min)", f"{peak.iloc[0]:.0f}")
    col2.caption(f"at {peak.index[0]}")
    ships = ships_seen(vessels, chosen_date)
    col3.metric("SAIL ships seen", ships if ships else "no data")

    left, right = st.columns([3, 2])

    # when, and in which type of place
    with left:
        st.subheader("When were people walking, and where?")
        by_type = people.T.groupby(sensors["family_description"]).sum().T
        by_type = by_type.rename(columns=PLACE_TYPES).resample("15min").sum()
        st.area_chart(by_type, x_label="time", y_label="pedestrians per 15 minutes")
        if chosen_area != "Whole IJ":
            st.caption("Each area has one type of place; choose Whole IJ to compare them.")

    # where it was busiest
    with right:
        st.subheader("Busiest places")
        ranked = peak.copy()
        ranked.index = [f"{i}. {name}" for i, name in enumerate(peak.index, start=1)]   # keeps the order
        st.bar_chart(ranked, horizontal=True, x_label="", y_label="highest flow (persons/m/min)")