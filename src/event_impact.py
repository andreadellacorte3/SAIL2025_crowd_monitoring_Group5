import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.events import event_effect, load_program_events, load_sensors, zone_flow
from src.event_plots import daily_profiles
from src.flow import flow_per_metre, load_effective_widths

COUNTS_PATH = "data/SAIL2025_LVMA_data_3min_20August-25August2025_flow.csv"
LINKS_PATH = "data/external/event_zone_links.csv"

ZONE_NAMES = {
    "CS_IJBOULEVARD": "Central Station, IJ side", "CS_EAST": "Central Station, east",
    "OOSTERDOK": "Oosterdok", "FERRY_CS_NDSM": "Ferry Central Station to NDSM",
    "FERRY_CS_BUIKSLOTERWEG": "Ferry Central Station to Buiksloterweg",
    "FERRY_CS_IJPLEIN": "Ferry Central Station to IJplein", "FERRY_PONTSTEIGER": "Ferry Pontsteiger",
    "NDSM": "NDSM (Noord)", "BUIKSLOTERWEG": "Buiksloterweg (Noord)", "NOORDERPARK": "Noorderpark",
    "AZARTPLEIN": "Azartplein (east)", "ZEEBURG": "Zeeburg (east)",
    "CENTRE_WALLEN": "City centre, Wallen", "CENTRE_DAM": "City centre, Dam",
}


@st.cache_data(show_spinner=False)
def load_event_data():
    """Flow per zone, the SAIL programme, the event-zone links and the result of every link."""
    counts = pd.read_csv(COUNTS_PATH, index_col="timestamp")
    counts.index = pd.to_datetime(counts.index)
    zones = zone_flow(flow_per_metre(counts, load_effective_widths()), load_sensors())
    program = load_program_events()
    links = pd.read_csv(LINKS_PATH)
    return zones, program, links, event_effect(zones, program, links)


def event_day_chart(flow, row):
    """The event day against the other SAIL days, in the colours of the dashboard."""
    event_day = row["start_datetime"].date()
    profiles = daily_profiles(flow)
    others = profiles.drop(columns=event_day)
    hours = [t.hour + t.minute / 60 for t in profiles.index]
    start = row["start_datetime"].hour + row["start_datetime"].minute / 60
    end = row["end_datetime"].hour + row["end_datetime"].minute / 60

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hours, y=others.max(axis=1), line=dict(width=0),
                             showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=hours, y=others.min(axis=1), fill="tonexty", line=dict(width=0),
                             fillcolor="rgba(150,150,150,0.3)", name="range of the other days",
                             hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=hours, y=others.median(axis=1), name="normal day (median of the others)",
                             line=dict(color="grey", dash="dash")))
    fig.add_trace(go.Scatter(x=hours, y=profiles[event_day], name=f"{event_day:%A} (event day)",
                             line=dict(color="#d62728", width=3)))
    fig.add_vrect(x0=start, x1=end, fillcolor="gold", opacity=0.15, line_width=0,
                  annotation_text=row["event"], annotation_position="top left")
    fig.add_hline(y=100, line_width=1, line_color="grey")
    fig.update_layout(xaxis=dict(title="time of day (h)", range=[8, 24], dtick=2),
                      yaxis_title="busyness (100 = average of that day)",
                      legend=dict(orientation="h", y=-0.25), height=420, margin=dict(t=30, b=10))
    return fig


def show_event_impact(chosen_date):
    """Section of the dashboard: which events changed the crowds on the chosen day, and where."""
    st.divider()
    st.header("Did the SAIL events change the crowds?")
    st.caption("A separate analysis: each zone on the day of an event is compared with the other "
               "SAIL days at the same time. Each day is scaled to its own average, so a busier day "
               "in general does not count as an effect of the event.")

    zones, program, links, effect = load_event_data()

    # overall result, the same as in the report
    n_pairs = len(effect)
    n_first = int((effect["rank_of_days"] == 1).sum())
    strongest = effect.iloc[0]
    col1, col2, col3 = st.columns(3)
    col1.metric("Event-zone pairs tested", n_pairs)
    col2.metric("Event day was the most unusual day", f"{n_first} of {n_pairs}",
                help=f"If events had no effect, this would happen about {n_pairs / 5:.1f} times by chance.")
    col3.metric("Strongest effect", f"{strongest['peak_excess_pct']:+.0f}%",
                help=f"{strongest['event']} at {ZONE_NAMES.get(strongest['zone'], strongest['zone'])}")

    # events of the chosen day that happen only on that day (the others have no normal day to compare with)
    days_per_event = program.groupby("event")["date"].nunique()
    single_day = days_per_event[days_per_event == 1].index
    today = program[(program["date"] == chosen_date.isoformat()) & program["event"].isin(single_day)]
    if today.empty:
        st.info(f"On {chosen_date:%A %d August} every event also took place on other days, so there is "
            "no normal day to compare it with. Choose another date in the sidebar.")
        return

    col_event, col_zone = st.columns(2)
    event = col_event.selectbox(f"Events on {chosen_date:%A %d August}", sorted(today["event"]))
    row = today[today["event"] == event].iloc[0]

    # zones we linked to this event come first
    linked = [z for z in links.loc[(links["event"] == event) & (links["relation"] != "none"), "zone"]
              if z in zones.columns]
    others = [z for z in zones.columns if z not in linked]
    zone = col_zone.selectbox(
        "Zone", linked + others,
        format_func=lambda z: ZONE_NAMES.get(z, z) + ("  (expected to be affected)" if z in linked else ""))

    col_chart, col_result = st.columns([3, 1])
    col_chart.plotly_chart(event_day_chart(zones[zone], row), width="stretch")

    pair = pd.DataFrame({"event": [event], "zone": [zone], "relation": ["selected"], "confidence": ["-"]})
    result = event_effect(zones, program, pair).iloc[0]
    rank = "–" if pd.isna(result["rank_of_days"]) else f"#{int(result['rank_of_days'])} of 5"
    col_result.metric("Highest excess during the event", f"{result['peak_excess_pct']:+.0f}%")
    col_result.metric("Rank of the event day", rank, help="#1: no other day was as unusual at this time.")
    col_result.caption("If the red line leaves the grey band during the event, the event changed how "
                       "many people walked there. A drop counts too: during SAIL-In the ferry to NDSM "
                       "almost stopped carrying people while the parade passed.")

    with st.expander("All event-zone pairs"):
        table = effect.assign(zone=effect["zone"].map(ZONE_NAMES).fillna(effect["zone"]))
        st.dataframe(table[["event", "zone", "relation", "peak_excess_pct", "rank_of_days"]].rename(
            columns={"peak_excess_pct": "highest excess (%)", "rank_of_days": "rank of the event day"}),
            hide_index=True)