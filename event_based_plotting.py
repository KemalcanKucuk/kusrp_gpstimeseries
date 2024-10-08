import pandas as pd
import matplotlib.pyplot as plt
import os

file_path = 'geodesy_data/cleaned_combined_api_data.csv'
df = pd.read_csv(file_path, low_memory=False)

output_dir = 'geodesy_data/earthquake_plots'
os.makedirs(output_dir, exist_ok=True)

unique_events = df['Event ID'].unique()

for event in unique_events:
    df_filtered = df[df['Event ID'] == event]
    plt.figure(figsize=(10, 6))
    plt.scatter(df_filtered['Distance from Epicenter'], df_filtered['Displacement'], color='blue', alpha=0.7)
    plt.xlabel('Distance from Epicenter (km)')
    plt.ylabel('Displacement (meters)')
    plt.title(f'Distance vs Displacement for Event {event}')
    plt.grid(True)

    output_path = os.path.join(output_dir, f'distance_vs_displacement_event_{event}.png')
    plt.savefig(output_path)
    plt.close()