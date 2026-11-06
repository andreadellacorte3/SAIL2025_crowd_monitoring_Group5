## THESE COMMENTED LINES ARE A MATPLOTLIB TEST OF THE GRAPH

# import pandas as pd
# import plotly.graph_objects as go
# # import streamlit as st
# import matplotlib.pyplot as plt
# import datetime as dt
# from trains import train_counts
# import sys
# from pathlib import Path

# # Resolve the parent directory of the current file and add it to sys.path
# parent_dir = str(Path(__file__).resolve().parent.parent)
# sys.path.append(parent_dir)

# # Now you can import the module from the parent directory
# from Population_of_dictionary_with_pedestrian_data import load_data as load_pedestrian_data


# def create_plot(
#         current_datetime: dt.datetime,
#         pedestrian_counts: pd.DataFrame,
#         train_arrivals: pd.DataFrame
#         ) -> None:

#     SENSORS_CLOSE_TO_THE_STATION = (
#         'GASA-01-A1_135', 'GASA-01-A1_315',
#         'GASA-01-A2_135', 'GASA-01-A2_315', 
#         'GASA-01-B_135', 'GASA-01-B_315',
#         'GASA-01-C_135', 'GASA-01-C_315',

#         'GASA-02-01_135', 'GASA-02-01_315',
#         'GASA-02-02_135', 'GASA-02-02_315',

#         'GASA-04_135', 'GASA-04_315',
#         'GACM-04_50', 'GACM-04_230'
#     )
#     time = pedestrian_counts[
#                         (pedestrian_counts["timestamp"] >= dt.datetime.combine(current_datetime.date(), dt.time())) &
#                         (pedestrian_counts["timestamp"] <= current_datetime)
#                     ]["timestamp"]
    
#     pedestrian_counts["sum"] = pedestrian_counts[[i for i in SENSORS_CLOSE_TO_THE_STATION]].sum(axis=1)
#     pedestrians = pedestrian_counts[
#                 (pedestrian_counts["timestamp"] >= dt.datetime.combine(current_datetime.date(), dt.time())) &
#                 (pedestrian_counts["timestamp"] <= current_datetime)
#             ]["sum"]

#     trains: pd.Series = train_arrivals[
#                 (train_arrivals.index.tz_convert(None) >= dt.datetime.combine(current_datetime.date(), dt.time(0))) &
#                 (train_arrivals.index.tz_convert(None) <= current_datetime)
#             ]["arrivals"].rolling("18min").mean()
#     fig, ax1 = plt.subplots()

#     color = 'tab:red'
#     ax1.set_xlabel('time (s)')
#     ax1.set_ylabel('Pedestrian count around the station', color=color)
#     ax1.plot(time, pedestrians, color=color)
#     ax1.tick_params(axis='y', labelcolor=color)

#     ax2 = ax1.twinx()  # instantiate a second Axes that shares the same x-axis

#     color = 'tab:blue'
#     ax2.set_ylabel('Train-arrivals during the day', color=color)  # we already handled the x-label with ax1
#     ax2.plot(time, trains, color=color)
#     ax2.tick_params(axis='y', labelcolor=color)

#     fig.tight_layout()  # otherwise the right y-label is slightly clipped
#     plt.show()


# if __name__ == "__main__":
#     create_plot(
#         current_datetime = dt.datetime(2025,8,22,20),
#         pedestrian_counts = load_pedestrian_data(),
#         train_arrivals = train_counts()
#     )

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import datetime as dt
import sys
from pathlib import Path

# Resolve the parent directory of the current file and add it to sys.path
parent_dir = str(Path(__file__).resolve().parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import modules from the parent directory
from src.trains import train_counts
from Population_of_dictionary_with_pedestrian_data import load_data as load_pedestrian_data

SENSORS_CLOSE_TO_THE_STATION = (
    'GASA-01-A1_135', 'GASA-01-A1_315', 'GASA-01-A2_135', 'GASA-01-A2_315', 
    'GASA-01-B_135', 'GASA-01-B_315', 'GASA-01-C_135', 'GASA-01-C_315',
    'GASA-02-01_135', 'GASA-02-01_315', 'GASA-02-02_135', 'GASA-02-02_315',
    'GASA-04_135', 'GASA-04_315', 'GACM-04_50', 'GACM-04_230'
)


@st.cache_data(show_spinner=False)
def load_all_data():
    """Load pedestrian counts and train arrivals data efficiently into cache."""
    pedestrian_counts = load_pedestrian_data()
    train_arrivals = train_counts()
    return pedestrian_counts, train_arrivals


def train_pedestrian_chart(current_datetime: dt.datetime, pedestrian_counts: pd.DataFrame, train_arrivals: pd.DataFrame) -> go.Figure:
    """Creates a dual-axis Plotly chart for pedestrians and trains."""
    # Filter and calculate pedestrian data
    pedestrian_mask = (pedestrian_counts["timestamp"] >= dt.datetime.combine(current_datetime.date(), dt.time())) & \
                      (pedestrian_counts["timestamp"] <= current_datetime)
    
    pedestrians_filtered = pedestrian_counts.loc[pedestrian_mask].copy()
    pedestrians_filtered["sum"] = pedestrians_filtered[[i for i in SENSORS_CLOSE_TO_THE_STATION]].sum(axis=1)
    
    time = pedestrians_filtered["timestamp"]
    pedestrians = pedestrians_filtered["sum"]

    # Filter and smooth train data
    train_mask = (train_arrivals.index.tz_convert(None) >= dt.datetime.combine(current_datetime.date(), dt.time(0))) & \
                 (train_arrivals.index.tz_convert(None) <= current_datetime)
                 
    trains_filtered = train_arrivals.loc[train_mask].copy()
    trains = trains_filtered["arrivals"].rolling("18min").mean()
    train_time = trains.index.tz_convert(None)

    # Instantiate a Plotly figure with a secondary y-axis (equivalent to ax1.twinx())
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Add Pedestrian line (Primary y-axis, Tab:Red equivalent)
    fig.add_trace(
        go.Scatter(x=time, y=pedestrians, name="Pedestrian count", line=dict(color="#d62728", width=2)),
        secondary_y=False,
    )

    # Add Train line (Secondary y-axis, Tab:Blue equivalent)
    fig.add_trace(
        go.Scatter(x=train_time, y=trains, name="Train arrivals (18m avg)", line=dict(color="#1f77b4", width=2)),
        secondary_y=True,
    )

    # Update layout to match your friend's dashboard aesthetics
    fig.update_layout(
        xaxis=dict(title="time (s)"),
        legend=dict(orientation="h", y=-0.25),
        height=420,
        margin=dict(t=30, b=10)
    )

    # Color coordinate the y-axis labels
    fig.update_yaxes(title_text="Pedestrian count around the station", color="#d62728", secondary_y=False)
    fig.update_yaxes(title_text="Train arrivals during the day", color="#1f77b4", secondary_y=True)

    return fig, pedestrians, trains


def show_trains_impact(current_datetime: dt.datetime):
    """Section of the dashboard matching the target layout style."""
    st.header("Do train arrivals explain the peaks in the pedestrian counts?", anchor = False)

    pedestrian_counts, train_arrivals = load_all_data()
    fig, pedestrians, trains = train_pedestrian_chart(current_datetime, pedestrian_counts, train_arrivals)
    
    # Render the chart
    st.plotly_chart(fig)

    # Add summary metrics underneath the chart in three columns
    col1, col2, col3 = st.columns(3)
    
    max_pedestrians = pedestrians.max() if not pedestrians.empty else 0
    max_trains = trains.max() if not trains.empty else 0
    
    col1.metric("Date visualised", f"{current_datetime:%d %B %Y}")
    col2.metric("Highest pedestrian peak", f"{max_pedestrians:,.0f}", 
                help=f"Maximum aggregated sensor count up to {current_datetime.strftime('%H:%M')}")
    col3.metric("Highest train arrivals", f"{max_trains:.1f}", 
                help=f"Maximum 18-minute rolling average up to {current_datetime.strftime('%H:%M')}")


if __name__ == "__main__":
    st.set_page_config(page_title="Train & Pedestrian Counts", layout="wide")
    
    # Passing your hardcoded date into the main Streamlit function
    show_trains_impact(
        current_datetime=dt.datetime(2025, 8, 22, 20)
    )