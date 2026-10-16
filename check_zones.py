"""Visual check of data/external/sensor_zones.csv: every sensor on a map, coloured by zone.

Run from the repository root:  python check_sensor_zones.py
"""
import matplotlib.pyplot as plt

from src.events import load_sensors

sensors = load_sensors()

fig, ax = plt.subplots(figsize=(11, 8))
colours = plt.get_cmap("tab20").colors  # 20 distinct colours, one per zone
for i, (zone, group) in enumerate(sensors.groupby("zone")):
    ax.scatter(group["lon"], group["lat"], s=60, color=colours[i], label=zone)
for name, row in sensors.iterrows():
    ax.annotate(name, (row["lon"], row["lat"]), fontsize=6,
                xytext=(3, 3), textcoords="offset points")

ax.set_title("LVMA sensors coloured by zone (data/external/sensor_zones.csv)")
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.legend(fontsize=7, loc="upper left", bbox_to_anchor=(1.01, 1))
plt.tight_layout()
plt.show()