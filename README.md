# SAIL 2025 crowd monitoring dashboard (TIL6022, Group 5)

This is the group project of Group 5 for TIL6022 Python Programming at TU Delft, 2026-2027. We use the pedestrian counts measured during SAIL Amsterdam 2025 (20 to 24 August) to build a dashboard that shows crowd managers where and when walkways around the IJ came close to critical conditions, and we study how other factors, such as rain and train arrivals, affect the crowds. The project is joint with TIL4030 Research and Design Methods, where the same group designs the dashboard on paper.

Status: work in progress. The proposal dates from 2 October 2026 and the final report is due on 6 November 2026.

## What is in this repository

- `SAIL2025_crowd_monitoring.ipynb`: the project notebook. It holds the proposal now and will become the final report.
- `SAIL2025_crowd_monitoring.pdf`: a PDF export of the notebook, readable without Python.
- `requirements.txt`: the Python packages the project needs.
- `Population_of_dictionary_with_pedestrian_data.py`: a first script that reads the sensor counts and locations.
- `lab8/`: our Lab 8 group assignment (part 2), with its notebook and Git diagram. This repository started as the Lab 8 repository of our group.

## How to run the project

The proposal is text only. From the next phase on, the notebook will contain code, and you will need these steps:

1. Clone this repository.
2. Download the data from the TU Delft data folder shared by the teaching team (you need to sign in with a TU Delft account). Put `SAIL2025_LVMA_data_3min_20August-25August2025_flow.csv` and `sensor-location.xlsx` in a folder called `data` inside the repository folder. Git ignores that folder, so the data never end up on GitHub.
3. Install the packages with `pip install -r requirements.txt`.
4. Open the notebook and run all cells.

## Data

The SAIL 2025 data are not in this repository: the teaching team asked us not to upload the datasets to GitHub, and two of the files are larger than GitHub allows anyway. We also use three public sources, which the code downloads itself: the crowd monitor archive of the City of Amsterdam for a normal week (https://api.data.amsterdam.nl/v1/crowdmonitor/passanten/), hourly weather data from KNMI (https://www.knmi.nl/nederland-nu/klimatologie/uurgegevens) and the train archive of Rijden de Treinen (https://www.rijdendetreinen.nl/en/open-data/train-archive). The notebook (section Available data) describes every dataset and where it comes from.

## Authors

Andrea Della Corte (`andreadellacorte3`), Mateo Gonzalez (`mateogonzalezbrown`), Daniele Bini (`Danielebini27`), Roberto Cortes Camilo De Sales (`cortesjose36-png`) and Davide Pighin (`Dpighin`).
