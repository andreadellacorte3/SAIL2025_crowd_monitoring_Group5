import streamlit as st
import pandas as pd

@st.cache_data(show_spinner = False)
def load_program():
    program = pd.read_csv("data/external/sail2025_program.csv")
    program["start_datetime"] = pd.to_datetime(program["start_datetime"]).dt.tz_localize(None)
    program["end_datetime"] = pd.to_datetime(program["end_datetime"]).dt.tz_localize(None)
    program["start_date"] = program["start_datetime"].dt.date
    program["end_date"] = program["end_datetime"].dt.date

    program = program.rename(columns={
        "event": "Event",
        "start_time": "Start",
        "end_time": "End"
    })
    program = program.set_index("Event")
    return program

