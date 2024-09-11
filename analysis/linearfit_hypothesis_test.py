import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, TextBox
from sklearn.linear_model import Ridge, Lasso
import preprocessing as pr
import tenv_utils

def fit_models(host_path, model_type='ridge', alpha=1.0):
    """
    Fit regularized linear regression models for each unique station ID.

    :param host_path: Path to the data directory.
    :param model_type: Type of regression ('ridge' or 'lasso').
    :param alpha: Regularization strength.
    :return: A dictionary containing fitted models and data for each station.
    """
    # Initialize the preprocessor
    pre = pr.Preprocessor(host_path)

    # Load 5% of the available tenv files by default as a list of DataFrames
    tenvs = pre.load_tenv_file_df(pre.tenvs)

    # Outlier points are deleted, series containing huge gaps are eliminated.
    gap_tolerance = 100
    method = 'lof'  # Choose the method to use: 'lof'
    kwargs = {'n_neighbors': 20, 'contamination': 0.35}  # Additional parameters for the method
    filtered_tenvs, stations_with_gaps, outlier_counts = tenv_utils.apply_filtering(
        tenvs, gap_tolerance=gap_tolerance, method=method, **kwargs)

    # Split filtered dataframe into list of dataframes for each station
    filtered_tenvs_list = [
        filtered_tenvs[filtered_tenvs['Station ID'] == station].copy()
        for station in filtered_tenvs['Station ID'].unique()
    ]

    return filtered_tenvs, filtered_tenvs_list, tenvs, outlier_counts

def add_regression_line(ax, x, y, model_type='ridge', alpha=1.0):
    """Add a linear regression line to the plot."""
    if len(x) < 2:  # Skip if not enough data points
        return

    X = np.arange(len(x)).reshape(-1, 1)

    # Choose the model type
    if model_type == 'ridge':
        model = Ridge(alpha=alpha)
    elif model_type == 'lasso':
        model = Lasso(alpha=alpha)
    else:
        raise ValueError("Invalid model_type. Choose 'ridge' or 'lasso'.")

    model.fit(X, y)
    ax.plot(x, model.predict(X), color='black', linestyle='-', linewidth=2, label='Regression Line')

def plot_tenv_data(axs, tenv_df_filtered, tenv_df_original, station_name, outlier_counts, model_type='ridge', alpha=1.0):
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
    add_regression_line(axs[0, 0], tenv_df_original['Date'], tenv_df_original['Delta E'], model_type, alpha)

    # Plot Delta E (filtered)
    axs[0, 1].scatter(tenv_df_filtered['Date'], tenv_df_filtered['Delta E'], label='Delta E', c='blue', s=10)
    axs[0, 1].set_title(f'{station_name} Delta E (Outliers removed: {outlier_count_e})')
    axs[0, 1].set_ylabel('Delta E')
    axs[0, 1].legend()
    axs[0, 1].grid(True)
    add_regression_line(axs[0, 1], tenv_df_filtered['Date'], tenv_df_filtered['Delta E'], model_type, alpha)

    # Plot Delta N (original)
    axs[1, 0].scatter(tenv_df_original['Date'], tenv_df_original['Delta N'], label='Delta N', c='green', s=10)
    axs[1, 0].set_title(f'{station_name} Delta N (Original)')
    axs[1, 0].set_ylabel('Delta N')
    axs[1, 0].legend()
    axs[1, 0].grid(True)
    add_regression_line(axs[1, 0], tenv_df_original['Date'], tenv_df_original['Delta N'], model_type, alpha)

    # Plot Delta N (filtered)
    axs[1, 1].scatter(tenv_df_filtered['Date'], tenv_df_filtered['Delta N'], label='Delta N', c='green', s=10)
    axs[1, 1].set_title(f'{station_name} Delta N (Outliers removed: {outlier_count_n})')
    axs[1, 1].set_ylabel('Delta N')
    axs[1, 1].legend()
    axs[1, 1].grid(True)
    add_regression_line(axs[1, 1], tenv_df_filtered['Date'], tenv_df_filtered['Delta N'], model_type, alpha)

    # Plot Delta V (original)
    axs[2, 0].scatter(tenv_df_original['Date'], tenv_df_original['Delta V'], label='Delta V', c='red', s=10)
    axs[2, 0].set_title(f'{station_name} Delta V (Original)')
    axs[2, 0].set_xlabel('Date')
    axs[2, 0].set_ylabel('Delta V')
    axs[2, 0].legend()
    axs[2, 0].grid(True)
    add_regression_line(axs[2, 0], tenv_df_original['Date'], tenv_df_original['Delta V'], model_type, alpha)

    # Plot Delta V (filtered)
    axs[2, 1].scatter(tenv_df_filtered['Date'], tenv_df_filtered['Delta V'], label='Delta V', c='red', s=10)
    axs[2, 1].set_title(f'{station_name} Delta V (Outliers removed: {outlier_count_v})')
    axs[2, 1].set_xlabel('Date')
    axs[2, 1].set_ylabel('Delta V')
    axs[2, 1].legend()
    axs[2, 1].grid(True)
    add_regression_line(axs[2, 1], tenv_df_filtered['Date'], tenv_df_filtered['Delta V'], model_type, alpha)

def setup_plot_navigation(filtered_tenvs_list, tenvs, outlier_counts, model_type='ridge', alpha=1.0):
    """Setup interactive navigation for plotting different stations."""
    fig, axs = plt.subplots(3, 2, figsize=(12, 9))
    plt.subplots_adjust(bottom=0.35)

    index = [0]  # Use a list to allow access in closures

    def next_station(event):
        index[0] = (index[0] + 1) % len(filtered_tenvs_list)
        station_name = filtered_tenvs_list[index[0]]['Station ID'].iloc[0]
        plot_tenv_data(axs, filtered_tenvs_list[index[0]], tenvs[tenvs['Station ID'] == station_name], station_name,
                       outlier_counts, model_type, alpha)

    def prev_station(event):
        index[0] = (index[0] - 1) % len(filtered_tenvs_list)
        station_name = filtered_tenvs_list[index[0]]['Station ID'].iloc[0]
        plot_tenv_data(axs, filtered_tenvs_list[index[0]], tenvs[tenvs['Station ID'] == station_name], station_name,
                       outlier_counts, model_type, alpha)

    def search_station(event):
        station_name = text_box.text.upper()  # Convert input to uppercase
        station_index = next((i for i, df in enumerate(filtered_tenvs_list) if df['Station ID'].iloc[0] == station_name), None)
        if station_index is not None:
            index[0] = station_index
            plot_tenv_data(axs, filtered_tenvs_list[index[0]], tenvs[tenvs['Station ID'] == station_name], station_name,
                           outlier_counts, model_type, alpha)
        else:
            print(f"Station {station_name} not found.")

    # Initial plot
    plot_tenv_data(axs, filtered_tenvs_list[index[0]],
                   tenvs[tenvs['Station ID'] == filtered_tenvs_list[index[0]]['Station ID'].iloc[0]],
                   filtered_tenvs_list[index[0]]['Station ID'].iloc[0], outlier_counts, model_type, alpha)

    # Define button axes
    axprev = plt.axes([0.35, 0.02, 0.1, 0.04])
    axnext = plt.axes([0.55, 0.02, 0.1, 0.04])
    axbox = plt.axes([0.35, 0.1, 0.3, 0.04])
    axsearch = plt.axes([0.68, 0.1, 0.1, 0.04])

    # Create buttons and text box
    bnext = Button(axnext, 'Next', color='lightgoldenrodyellow', hovercolor='0.975')
    bprev = Button(axprev, 'Previous', color='lightgoldenrodyellow', hovercolor='0.975')
    text_box = TextBox(axbox, 'Search Station: ')
    bsearch = Button(axsearch, 'SEARCH', color='lightgoldenrodyellow', hovercolor='0.975')

    # Connect buttons to event handlers
    bnext.on_clicked(next_station)
    bprev.on_clicked(prev_station)
    bsearch.on_clicked(search_station)
    text_box.on_submit(search_station)

    plt.subplots_adjust(hspace=0.8)
    plt.show()
