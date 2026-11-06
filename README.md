# SAIL 2025 crowd monitoring dashboard (TIL6022, Group 5)

This is the group project of Group 5 for TIL6022 Python Programming at TU Delft, 2026-2027. We use the pedestrian counts measured during SAIL Amsterdam 2025 (20 to 24 August) to build a dashboard that shows crowd managers where and when walkways around the IJ came close to critical conditions, and we study how other factors, such as train arrivals, affect the crowds. The project is joint with TIL4030 Research and Design Methods, where the same group designs the dashboard on paper.

Status: Submitted. The proposal dates from 2 October 2026 and the final report is due on 6 November 2026.

## What is in this repository

- `Report.ipynb`: the project notebook. It is the final report and it walks through the dashboard and how it answers the research questions.
- `Report.pdf`: a PDF export of the notebook, readable without Python.
- `requirements.txt`: the Python packages the project needs.
- `streamlit_dashboard_initialization.py`: It is the main script in this repository. It combines all other scripts necessary to run the dashboard. 
- `Population_of_dictionary_with_pedestrian_data.py`: a script that reads the sensor counts and locations and puts them in a dataframe.
- `find_start_end_datetimes.py`: a script that looks into `external/sail2025_program.csv` and retrieves the start and end of the event. 
- `lab8/`: our Lab 8 group assignment (part 2), with its notebook and Git diagram. This repository started as the Lab 8 repository of our group.
- `Data_Transformation.ipynb`: a jupyter notebook that allowed us to explore the data. It is the basis on which we could build our data manipulation functions.
- `subcategories.txt`: a text file including all vessel categories that are present in the original dataset.
- `check_zones.py`: a script that was used to perform a visual check of data/external/sensor_zones.csv: every sensor on a map, coloured by zone.
- `src/`: a folder including many scripts that are fundamental to the dashboard's execution
    - `day_overview.py`: a script that is used to generate the plots in the "The day in numbers" section 
    - `event_impact.py`: a script that is used to calculate the impact of an event visualized in "Did the SAIL events change the crowds?"
    - `event_plots.py`: a script that generates the plot in "Did the SAIL events change the crowds?"
    - `events.py`: combines the 2 previously described files to analyze events' effect
    - `flow.py`: a script that calculates flow per meter from raw count
    - `sensor_status.py`: a script that calculates whether a sensor is off
    - `station_sensors.py`: a script that calculates pedestrian flows around the station
    - `train_effect.py`: compares the trains per 3 minutes (trains.py) with the pedestrians per 3 minutes at
    the sensors near the station (station_sensors.py). The 3-minute intervals are put in
    groups by the number of trains that arrived in them. For each group we look at the
    people counted in the next 15 minutes, compared with the average of that hour.
    - `train_pedestrian_graph.py`: A script that creates the visualizations in the Do train arrivals explain the peaks in the pedestrian counts? section of the dashboard
    - `trains.py`: a script that downloads and retrieves train arrivals and departures at Amsterdam Centraal during SAIL 2025


- `data/` a folder where you will put the data from the TU Delft data folder
    - `external/`: this folder includes data that we manually searched for, the file have been writte by us
        - `event_zone_links.csv`: a file created by us that links zones to events
        - `sail2025_event_locations.csv`: a file including where events happen
        - `sail2025_program.csv`: a file that links events to their starting and ending times
        - `sensor_zones.csv`: a file that links each zone to a sensor


## How to run the project

1. Clone this repository.
2. Download the data from the TU Delft data folder shared by the teaching team (you need to sign in with a TU Delft account). Put `SAIL2025_LVMA_data_3min_20August-25August2025_flow.csv`, `sensor-location.xlsx` and `Vesselposition_data_20-24Aug2025.csv` in a folder called `data` inside the repository folder. Git ignores that folder, so the data never end up on GitHub.
3. Install the packages with `pip install -r requirements.txt`.
4. Type `streamlit run streamlit_dashboard_initialization.py` in your terminal
5. Use the dashboard to visualize crowd, vessel and train data

## Data

The SAIL 2025 data are not in this repository: the teaching team asked us not to upload the datasets to GitHub, and two of the files are larger than GitHub allows anyway. We also use three public sources, which the code downloads itself: the crowd monitor archive of the City of Amsterdam for a normal week (https://api.data.amsterdam.nl/v1/crowdmonitor/passanten/), and the train archive of Rijden de Treinen (https://www.rijdendetreinen.nl/en/open-data/train-archive). The notebook (section Available data) describes every dataset and where it comes from.

## Authors

Andrea Della Corte (`andreadellacorte3`), Mateo Gonzalez (`mateogonzalezbrown`), Daniele Bini (`Danielebini27`), Roberto Cortes Camilo De Sales (`cortesjose36-png`) and Davide Pighin (`Dpighin`).
