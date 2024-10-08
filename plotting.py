import pandas as pd
import matplotlib.pyplot as plt
import os

file_path = 'geodesy_data/cleaned_combined_api_data.csv'
df = pd.read_csv(file_path, low_memory=False)

output_dir = 'geodesy_data/plots'
os.makedirs(output_dir, exist_ok=True)

unique_stations = df['Station ID'].unique()

for station in unique_stations:
    df_filtered = df[df['Station ID'] == station]
    plt.figure(figsize=(10, 6))
    plt.scatter(df_filtered['Distance from Epicenter'], df_filtered['Displacement'], color='blue', alpha=0.7)
    plt.xlabel('Distance from Epicenter (km)')
    plt.ylabel('Displacement (meters)')
    plt.title(f'Distance vs Displacement for Station {station}')
    plt.grid(True)
    # Save the plot
    output_path = os.path.join(output_dir, f'distance_vs_displacement_{station}.png')
    plt.savefig(output_path)
    plt.close()