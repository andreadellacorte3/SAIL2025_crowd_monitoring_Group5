#Flow per metre for the LVMA sensors

#flow = count / (effective_width * 3) 
#---in pedestrians per metre per minute
#---as defined in the README of the SAIL 2025 dataset.

import pandas as pd

WIDTH_COLUMN = "Effectieve\xa0 breedte"

def load_effective_widths(path="data/sensor-location.xlsx"):
    locations = pd.read_excel(path)
    width = pd.to_numeric(locations[WIDTH_COLUMN].astype(str).str.replace(",", ".")) #convert all numbers with , to .
    width.index = locations["Objectummer"]
    return width

def flow_per_metre(counts, width): #Convert 3-minute counts into flow, in pedestrians per metre per minute. Sensors without a known effective width are left out.
    
    flow = pd.DataFrame(index=counts.index)

    for column in counts.columns:
        if "-" not in column:           
            continue
        sensor = column.split("_")[0]       
        if sensor not in width.index:
            continue
        flow[column] = counts[column] / (width[sensor] * 3)
    return flow