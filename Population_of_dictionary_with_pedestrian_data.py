import streamlit as st

# @st.cache_data(show_spinner = False)
# def load_data(
#         sensor_location_path:str = "data/sensor-location.xlsx", 
#         flow_data_path:str = "data/SAIL2025_LVMA_data_3min_20August-25August2025_flow.csv"
#         ) -> dict:
#     import pandas as pd
#     df = pd.read_excel(sensor_location_path)
#     df = df.set_index("Objectummer")


#     data = {}
#     for sensor_name in df.index:
#         x,y = map(float,df.loc[sensor_name,"Lat/Long"].split(","))
#         data[sensor_name] = {
#             "x": x,
#             "y": y
#         }

#     df = pd.read_csv(flow_data_path)

#     non_sensors = (
#         "hour",
#         "timestamp",
#         "minute",
#         "day",
#         "month",
#         "weekday",
#         "is_weekend",
#         )

#     sensors_not_in_sensor_location = ( # The sensor "GASA-06-B" is not present in the sensor-location.xlsx file
#         "GASA-06-B_275",
#         "GASA-06-B_95"
#     )

#     def retrieve_all_counts(i:int, data:dict = data) -> dict:
#         """
#         Given the number of digits of the orientation in degrees i the data dictionary will be populated
#         """
#         if "orientation" not in data[column[:-i-1]]:
#             data[column[:-i-1]]["orientation"] = {}
#         data[column[:-i-1]]["orientation"][column[-i:]] = list(df[column])

#     for column in df:
#         if (column in non_sensors) or (column in sensors_not_in_sensor_location): continue

#         if str(column[-3:]).isdigit():
#             retrieve_all_counts(3)
#             continue
#         if str(column[-2:]).isdigit():
#             retrieve_all_counts(2)
#             continue
#         retrieve_all_counts(1)
#     df["timestamp"] = pd.to_datetime(df.timestamp).dt.tz_localize(None)
#     data["timestamp"] = df["timestamp"]
#     return data
import pandas as pd

@st.cache_data(show_spinner = False)
def load_data(        
    sensor_location_path:str = "data/sensor-location.xlsx", 
    flow_data_path:str = "data/SAIL2025_LVMA_data_3min_20August-25August2025_flow.csv"
    ) -> pd.DataFrame:
    """
    The dataframe has the sensor's names as columns. Some column names are duplicate since each column refers
    to a specific sensor and orientation.

    Most rows are timestamps, while
    """

    sensors_not_in_sensor_location = { # The sensor "GASA-06-B" is not present in the sensor-location.xlsx file
        "GASA-06-B_275",
        "GASA-06-B_95"
    }

    df_loc = pd.read_excel(sensor_location_path)
    df_counts = pd.read_csv(flow_data_path)

    col = "Effectieve\xa0 breedte"
    df_loc["Effectieve breedte"] = pd.to_numeric(
        df_loc[col].astype(str)
            .str.replace(",", ".")
            .str.replace(r"\s+", "", regex=True), 
        errors="coerce"
    )
    df_loc.set_index("Objectummer", inplace = True)

    del df_loc[col]
    del df_loc["Breedte"]
    names = set()

    for sensor in df_counts.columns:
        if "-" not in sensor: continue # All sensors have "-" in the name
        name, orientation = sensor.split("_")
        df_counts.loc["orientation",sensor] = int(orientation)
        df_counts.loc["name_without_orientation",sensor] = name
        if name in df_loc.index:
            lat,long = map(float,df_loc.loc[name,"Lat/Long"].split(","))
            df_counts.loc["lat",sensor] = lat
            df_counts.loc["long",sensor] = long


        names.add(name)


    for sensor in sensors_not_in_sensor_location:
        name = sensor
        if name not in df_counts.columns: continue
        del df_counts[name]
    
    df_counts["timestamp"] = pd.to_datetime(df_counts["timestamp"]).dt.tz_localize(None)
    
    return df_counts

    

    

if __name__ == "__main__":
    load_data()