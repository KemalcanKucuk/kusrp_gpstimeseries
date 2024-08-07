import numpy as np
import socket
import pandas as pd
import os
from matplotlib import pyplot as plt
from matplotlib.widgets import Button, TextBox
import preprocessing as pr
import tenv_utils

def main():
    hostname = socket.gethostname()

    # kendi hostnaminizi print ettirin ona göre path ekleyin.
    if hostname == 'Sarps-MacBook-Pro.local':
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

    # Load 5% of the available tenv files by default as a list of DataFrames
    tenvs = pre.load_tenv_file_df(pre.tenvs)

    # Define the parameter ranges for Grid Search
    n_neighbors_range = [5, 10, 15, 20, 25]
    contamination_range = [0.01, 0.02, 0.05]

    #best_params = tenv_utils.manual_lof_optimization(tenvs, cols=['Delta E', 'Delta N', 'Delta V'], n_neighbors_range=n_neighbors_range, contamination_range=contamination_range, search_type='grid')

    #print(f"Best LOF parameters found: {best_params}")

    # Outlier points are deleted, series containing huge gaps are eliminated.
    gap_tolerance = 100
    method = 'lof'  # Choose the method to use: 'lof'
    #kwargs = best_params   # Additional parameters for the method
    kwargs = {'n_neighbors': 20, 'contamination': 0.35}
    filtered_tenvs, stations_with_gaps, outlier_counts = tenv_utils.apply_filtering(tenvs, gap_tolerance=gap_tolerance,
                                                                                    method=method, **kwargs)
    filtered_tenvs_list = tenv_utils.split_combined_df_to_list(filtered_tenvs)

    fig, axs = plt.subplots(3, 2, figsize=(12, 9), sharex='col')
    fig.suptitle('GPS Timeseries Data', fontsize=16)
    index = [0]  # Mutable index to track the current station
    print(
        f"Currently, {100 * len(stations_with_gaps) / len(tenvs):.2f}% of the stations are being filtered out with a gap tolerance of {gap_tolerance}")

    def next_station(event):
        index[0] = (index[0] + 1) % len(filtered_tenvs_list)
        station_name = filtered_tenvs_list[index[0]]['Station ID'].iloc[0]
        plot_tenv_data(axs, filtered_tenvs_list[index[0]], tenvs[tenvs['Station ID'] == station_name], station_name,
                       outlier_counts)

    def prev_station(event):
        index[0] = (index[0] - 1) % len(filtered_tenvs_list)
        station_name = filtered_tenvs_list[index[0]]['Station ID'].iloc[0]
        plot_tenv_data(axs, filtered_tenvs_list[index[0]], tenvs[tenvs['Station ID'] == station_name], station_name,
                       outlier_counts)

    def search_station(event):
        station_name = text_box.text.upper()  # Convert input to uppercase
        station_index = next((i for i, df in enumerate(filtered_tenvs_list) if df['Station ID'].iloc[0] == station_name), None)
        if station_index is not None:
            index[0] = station_index
            plot_tenv_data(axs, filtered_tenvs_list[index[0]], tenvs[tenvs['Station ID'] == station_name], station_name,
                           outlier_counts)
        else:
            print(f"Station {station_name} not found.")

    plot_tenv_data(axs, filtered_tenvs_list[index[0]],
                   tenvs[tenvs['Station ID'] == filtered_tenvs_list[index[0]]['Station ID'].iloc[0]],
                   filtered_tenvs_list[index[0]]['Station ID'].iloc[0], outlier_counts)

    plt.subplots_adjust(bottom=0.35)

    axprev = plt.axes([0.35, 0.02, 0.1, 0.04])
    axnext = plt.axes([0.55, 0.02, 0.1, 0.04])
    axbox = plt.axes([0.35, 0.1, 0.3, 0.04])
    axsearch = plt.axes([0.68, 0.1, 0.1, 0.04])
    bnext = Button(axnext, 'Next', color='lightgoldenrodyellow', hovercolor='0.975')
    bprev = Button(axprev, 'Previous', color='lightgoldenrodyellow', hovercolor='0.975')
    text_box = TextBox(axbox, 'Search Station: ')
    bsearch = Button(axsearch, 'SEARCH', color='lightgoldenrodyellow', hovercolor='0.975')

    bnext.on_clicked(next_station)
    bprev.on_clicked(prev_station)
    bsearch.on_clicked(search_station)
    text_box.on_submit(search_station)

    plt.show()

def plot_tenv_data(axs, tenv_df_filtered, tenv_df_original, station_name, outlier_counts):
    """Plot the Delta E, Delta N, and Delta V columns from the tenv dataframe with and without outliers removed."""

    # Clear previous plots
    for ax in axs[:, 0]:
        ax.cla()
    for ax in axs[:, 1]:
        ax.cla()

    outlier_count_e = outlier_counts.get(station_name, {}).get('Delta E', 0)
    outlier_count_n = outlier_counts.get(station_name, {}).get('Delta N', 0)
    outlier_count_v = outlier_counts.get(station_name, {}).get('Delta V', 0)

    # Plot Delta E (original)
    axs[0, 0].scatter(tenv_df_original['Date'], tenv_df_original['Delta E'], label='Delta E', c='blue', s=10)
    axs[0, 0].set_title(f'{station_name} Delta E (Original)')
    axs[0, 0].set_ylabel('Delta E')
    axs[0, 0].legend()
    axs[0, 0].grid(True)

    # Plot Delta E (filtered)
    axs[0, 1].scatter(tenv_df_filtered['Date'], tenv_df_filtered['Delta E'], label='Delta E', c='blue', s=10)
    axs[0, 1].set_title(f'{station_name} Delta E (Outliers removed: {outlier_count_e})')
    axs[0, 1].set_ylabel('Delta E')
    axs[0, 1].legend()
    axs[0, 1].grid(True)

    # Plot Delta N (original)
    axs[1, 0].scatter(tenv_df_original['Date'], tenv_df_original['Delta N'], label='Delta N', c='green', s=10)
    axs[1, 0].set_title(f'{station_name} Delta N (Original)')
    axs[1, 0].set_ylabel('Delta N')
    axs[1, 0].legend()
    axs[1, 0].grid(True)

    # Plot Delta N (filtered)
    axs[1, 1].scatter(tenv_df_filtered['Date'], tenv_df_filtered['Delta N'], label='Delta N', c='green', s=10)
    axs[1, 1].set_title(f'{station_name} Delta N (Outliers removed: {outlier_count_n})')
    axs[1, 1].set_ylabel('Delta N')
    axs[1, 1].legend()
    axs[1, 1].grid(True)

    # Plot Delta V (original)
    axs[2, 0].scatter(tenv_df_original['Date'], tenv_df_original['Delta V'], label='Delta V', c='red', s=10)
    axs[2, 0].set_title(f'{station_name} Delta V (Original)')
    axs[2, 0].set_xlabel('Date')
    axs[2, 0].set_ylabel('Delta V')
    axs[2, 0].legend()
    axs[2, 0].grid(True)

    # Plot Delta V (filtered)
    axs[2, 1].scatter(tenv_df_filtered['Date'], tenv_df_filtered['Delta V'], label='Delta V', c='red', s=10)
    axs[2, 1].set_title(f'{station_name} Delta V (Outliers removed: {outlier_count_v})')
    axs[2, 1].set_xlabel('Date')
    axs[2, 1].set_ylabel('Delta V')
    axs[2, 1].legend()
    axs[2, 1].grid(True)

    plt.draw()

if __name__ == '__main__':
    main()