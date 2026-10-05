def main():
    import pandas as pd
    df = pd.read_excel("sensor-location.xlsx")
    df = df.set_index("Objectummer")


    data = {}
    for sensor_name in df.index:
        x,y = map(float,df.loc[sensor_name,"Lat/Long"].split(","))
        data[sensor_name] = {
            "x": x,
            "y": y
        }

    df = pd.read_csv("SAIL2025_LVMA_data_3min_20August-25August2025_flow.csv")

    non_sensors = (
        "hour",
        "timestamp",
        "minute",
        "day",
        "month",
        "weekday",
        "is_weekend",
        )

    sensors_not_in_sensor_location = ( # The sensor "GASA-06-B" is not present in the sensor-location.xlsx file
        "GASA-06-B_275",
        "GASA-06-B_95"
    )

    def retrieve_all_counts(i:int, data:dict = data) -> dict:
        """
        Given the number of digits of the orientation in degrees i the data dictionary will be populated
        """
        if "orientation" not in data[column[:-i-1]]:
            data[column[:-i-1]]["orientation"] = {}
        data[column[:-i-1]]["orientation"][column[-i:]] = list(df[column])

    for column in df:
        if (column in non_sensors) or (column in sensors_not_in_sensor_location): continue

        if str(column[-3:]).isdigit():
            retrieve_all_counts(3)
            continue
        if str(column[-2:]).isdigit():
            retrieve_all_counts(2)
            continue
        retrieve_all_counts(1)


if __name__ == "__main__":
    main()