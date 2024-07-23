import numpy as np
import socket
import pandas as pd
import os
from matplotlib import pyplot as plt
from matplotlib.widgets import Button
import preprocessing as pr
import tenv_utils

def main():
    hostname = socket.gethostname()

    # kendi hostnaminizi print ettirin ona göre path ekleyin.
    if hostname == 'Sarps-MBP':
        print("kral hoşgeldin.")
        parent_path = '/Users/sarpvulas/geodesy.unr.edu/gps_timeseries/tenv/'
    elif hostname == 'Kemalcans-MacBook-Pro.local':
        parent_path = '/Users/kemalcankucuk/Documents/kuis-matam-summerproject/geodesy_data'
    elif hostname == 'Zeyneps-MacBook-Pro-2.local' or hostname == "Zeyneps-MBP-2.home":
        parent_path = '/Users/zeynepaydin/geodesy.unr.edu/gps_timeseries/tenv/'
    else:
        parent_path = '/default/path/to/data'

    # Initialize the preprocessor
    pre = pr.Preprocessor(parent_path)
    eqs = pre.load_eq_txt()
    eq_stats = eqs['Station ID'].unique()
    eq_stats = [s + '.tenv' for s in eq_stats]
    # Load 5% of the available tenv files by default as a list of DataFrames
    tenvs = pre.load_tenv_file_df(eq_stats)
    
    # Outlier points are deleted, series containing huge gaps are eliminated.
    gap_tolerance = 100
    filtered_tenvs, stations_with_gaps = pre.apply_filtering(tenvs, gap_tolerance=gap_tolerance)
    fig, axs = plt.subplots(3, 1, figsize=(6, 9), sharex=True)
    fig.suptitle('GPS Timeseries Data', fontsize=16)
    index = [0]  # Mutable index to track the current station
    print(f"Currently, {100 * len(stations_with_gaps) / len(tenvs):.2f}% of the stations are being filtered out with a gap tolerance of {gap_tolerance}")

    def next_station(event):
        index[0] = (index[0] + 1) % len(filtered_tenvs)
        station_name = filtered_tenvs[index[0]]['Station ID'].iloc[0]
        plot_tenv_data(axs, filtered_tenvs[index[0]], station_name, eqs)

    def prev_station(event):
        index[0] = (index[0] - 1) % len(filtered_tenvs)
        station_name = filtered_tenvs[index[0]]['Station ID'].iloc[0]
        plot_tenv_data(axs, filtered_tenvs[index[0]], station_name, eqs)

    plot_tenv_data(axs, filtered_tenvs[index[0]], filtered_tenvs[index[0]]['Station ID'].iloc[0], eqs)

    plt.subplots_adjust(bottom=0.15)

    axprev = plt.axes([0.35, 0.02, 0.1, 0.04])
    axnext = plt.axes([0.55, 0.02, 0.1, 0.04])
    bnext = Button(axnext, 'Next', color='lightgoldenrodyellow', hovercolor='0.975')
    bprev = Button(axprev, 'Previous', color='lightgoldenrodyellow', hovercolor='0.975')

    bnext.on_clicked(next_station)
    bprev.on_clicked(prev_station)

    plt.show()

def plot_tenv_data(axs, tenv_df, station_name, eq_events):
    """Plot the Delta E, Delta N, and Delta V columns from the tenv dataframe and add navigation buttons."""

    axs[0].cla()
    axs[1].cla()
    axs[2].cla()

    # Plot Delta E
    axs[0].scatter(tenv_df['Date'], tenv_df['Delta E'], label='Delta E', c='blue', s=10)
    axs[0].set_title(f'{station_name} Delta E')
    axs[0].set_ylabel('Delta E')
    axs[0].legend()
    axs[0].grid(True)

    # Plot Delta N
    axs[1].scatter(tenv_df['Date'], tenv_df['Delta N'], label='Delta N', c='green', s=10)
    axs[1].set_title(f'{station_name} Delta N')
    axs[1].set_ylabel('Delta N')
    axs[1].legend()
    axs[1].grid(True)

    # Plot Delta V
    axs[2].scatter(tenv_df['Date'], tenv_df['Delta V'], label='Delta V', c='red', s=10)
    axs[2].set_title(f'{station_name} Delta V')
    axs[2].set_xlabel('Date')
    axs[2].set_ylabel('Delta V')
    axs[2].legend()
    axs[2].grid(True)

    # Filter earthquake events for the current station
    station_events = eq_events[eq_events['Station ID'] == station_name]
    
    # Plot earthquake events on each axis
    for ax in axs:
        for _, event in station_events.iterrows():
            ax.axvline(event['Date'], color='purple', linestyle='--', label='Earthquake Event')
    
    plt.draw()

if __name__ == '__main__':
    main()