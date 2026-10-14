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
