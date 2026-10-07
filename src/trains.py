"""Train arrivals and departures at Amsterdam Centraal during SAIL 2025 (sub-question 5).

Data: open train archive of Rijden de Treinen,
https://www.rijdendetreinen.nl/en/open-data/train-archive
"""
from pathlib import Path
from urllib.request import urlretrieve

import pandas as pd

URL = "https://opendata.rijdendetreinen.nl/public/services/services-2025-08.csv.gz"
DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "services-2025-08.csv.gz"
STATION = "ASD"  # station code of Amsterdam Centraal
START = pd.Timestamp("2025-08-20 00:00:00+02:00")  # same time window as the sensor data
END = pd.Timestamp("2025-08-25 00:00:00+02:00")
COLUMNS = ["Service:Type", "Stop:Station code",
           "Stop:Arrival time", "Stop:Arrival delay", "Stop:Arrival cancelled",
           "Stop:Departure time", "Stop:Departure delay", "Stop:Departure cancelled"]


def train_counts(interval="3min"):
    """Count the train arrivals and departures at Amsterdam Centraal in each time interval.

    A train counts at its actual time (planned time plus delay in minutes).
    Cancelled stops and replacement buses are left out. The result has one row
    per interval from 20 to 24 August 2025, with the columns 'arrivals' and 'departures'.
    """
    if not DATA_FILE.exists():  # download the 32 MB file only the first time
        DATA_FILE.parent.mkdir(exist_ok=True)
        urlretrieve(URL, DATA_FILE)

    stops = pd.read_csv(DATA_FILE, usecols=COLUMNS)
    stops = stops[(stops["Stop:Station code"] == STATION)
                  & ~stops["Service:Type"].str.contains("bus", case=False, na=False)]

    counts = {}
    for kind in ["Arrival", "Departure"]:
        planned = pd.to_datetime(stops[f"Stop:{kind} time"], format="ISO8601")
        delay = pd.to_timedelta(stops[f"Stop:{kind} delay"].fillna(0), unit="min")
        actual = (planned + delay)[planned.notna() & (stops[f"Stop:{kind} cancelled"] != True)]
        actual = actual[(actual >= START) & (actual < END)]
        counts[kind.lower() + "s"] = actual.dt.floor(interval).value_counts()

    every_interval = pd.date_range(START, END, freq=interval, inclusive="left")
    return pd.DataFrame(counts).reindex(every_interval, fill_value=0).fillna(0).astype(int)


if __name__ == "__main__":
    counts = train_counts()
    print(counts.sum())
    print(counts.sort_values("arrivals", ascending=False).head())
