import io
import math
import os
import socket
from flask import Flask, jsonify, Response, request, render_template
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import preprocessing as pr
import constants
import pandas as pd
import numpy as np

import tenv_utils

# Get the hostname and initialize the parent_path based on the hostname
hostname = socket.gethostname()
parent_path = constants.PATHS.get(hostname, '/default/path/to/data')

# Initialize the Preprocessor with the dynamic path
pre = pr.Preprocessor(parent_path)

app = Flask(__name__)
pd.set_option('display.max_columns', None)

# Index Route
@app.route('/')
def index():
    try:
        # Load the combined data
        combined_df = pd.read_csv(os.path.join(parent_path, 'all_earthquakes.csv'))

        # Drop rows where Event ID or Event Magnitude is NaN
        combined_df = combined_df.dropna(subset=['Event ID', 'Event Magnitude'])

        # Extract unique earthquake events
        earthquake_df = combined_df[['Event ID', 'Event Magnitude']].drop_duplicates()

        earthquakes = earthquake_df.to_dict(orient='records')

        # Render the index page and pass the earthquake data
        return render_template('index.html', earthquakes=earthquakes)
    except Exception as e:
        print(f"Error loading earthquake data: {e}")
        return jsonify({"status": "error", "message": "Error loading earthquake data"}), 500


# Load Stations Route
@app.route('/load_stations')
def load_stations():
    try:
        load_percentage = int(request.args.get('load_percentage', 5))  # Default 5%
        magnitude_threshold = request.args.get('magnitude_threshold', None)
        earthquake_count = request.args.get('earthquake_count', None)

        magnitude_threshold = float(magnitude_threshold) if magnitude_threshold else None
        earthquake_count = int(earthquake_count) if earthquake_count else None

        print(
            f"Loading stations with load_percentage={load_percentage}, magnitude_threshold={magnitude_threshold}, earthquake_count={earthquake_count}")

        # Load the filtered combined earthquake data
        combined_df = pre.load_combined_df(load_percentage=load_percentage,
                                           target_magnitude=magnitude_threshold,
                                           eq_count=earthquake_count,
                                           save=True)

        # Debugging: Print first few rows of combined_df
        print(f"Combined DataFrame (first 5 rows):\n{combined_df.head()}")
        print(f"Combined DataFrame contains {len(combined_df)} rows")

        # Check if combined_df has valid data
        if combined_df.empty:
            print("No data in combined_df")
            return jsonify({"status": "error", "message": "No earthquake data found"}), 400

        # Load station info
        station_df = pre.load_station_info()
        print(f"Station DataFrame (first 5 rows):\n{station_df.head()}")
        print(f"Station DataFrame contains {len(station_df)} rows")

        # Filter out stations that do not have any corresponding earthquake data
        filtered_stations = station_df[station_df['Station ID'].isin(combined_df['Station ID'].unique())]
        print(f"Filtered Station DataFrame (first 5 rows):\n{filtered_stations.head()}")
        print(f"Filtered stations with earthquake data: {len(filtered_stations)} stations")

        # If no stations are found after filtering, return an error
        if filtered_stations.empty:
            print("No stations found with earthquake data")
            return jsonify({"status": "error", "message": "No stations found with earthquake data"}), 400

        # Prepare station info with earthquake count and magnitudes
        stations = []
        for station_id, df in filtered_stations.groupby('Station ID'):
            lat = df['Lat'].iloc[0]
            lon = df['Long'].iloc[0]

            # Get events related to this station from combined_df
            station_events = combined_df[combined_df['Station ID'] == station_id]
            eq_count = station_events['Event ID'].nunique()
            magnitudes = station_events['Event Magnitude'].dropna().unique().tolist()

            print(f"Station {station_id}: {eq_count} earthquakes, magnitudes: {magnitudes}")

            # Prepare station info
            stations.append({
                'station_id': station_id,
                'lat': lat,
                'lon': lon,
                'eq_count': eq_count,
                'magnitudes': magnitudes
            })

        print("Filtered station data prepared and sent to the frontend.")
        return jsonify({"status": "Data Loaded", "stations": stations})

    except Exception as e:
        print(f"Error loading stations: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

# Updated Plotting Logic: Distance vs Displacement for Earthquake
# Updated Plotting Logic: Distance vs Displacement for Earthquake
@app.route('/plot_distance_vs_displacement')
def plot_distance_vs_displacement():
    try:
        # Retrieve the event ID from the request
        event_id = request.args.get('event_id')
        if not event_id:
            raise ValueError("Event ID is missing")

        # Load the entire combined earthquake data
        combined_df = pd.read_csv(os.path.join(parent_path, 'all_earthquakes.csv'))

        # Filter the combined data for the selected event
        event_data = combined_df[combined_df['Event ID'] == event_id]
        if event_data.empty:
            print(f"No event data found for Event ID: {event_id}")
            return jsonify({"status": "error", "message": "No data found for the given earthquake event"}), 400

        # Get the station ID and date for this earthquake event
        stations = event_data['Station ID']
        event_date = pd.to_datetime(event_data['Date'].iloc[0])
        displacement_dic = {}

        for station_id in stations:
            print(f"Processing Station ID: {station_id}, Event Date: {event_date}")

            # Find the day before the event date
            before_event_data = combined_df[
                (combined_df['Station ID'] == station_id) &
                (pd.to_datetime(combined_df['Date']) < event_date)
            ].sort_values('Date').iloc[-1]  # Get the last record before the event date

            # Find the day after the event date
            after_event_data = combined_df[
                (combined_df['Station ID'] == station_id) &
                (pd.to_datetime(combined_df['Date']) > event_date)
            ].sort_values('Date').iloc[0]  # Get the first record after the event date

            # If both before and after event data are found, calculate the displacement
            if before_event_data is not None and after_event_data is not None:
                delta_e_displacement = abs(after_event_data['Delta E'] - before_event_data['Delta E'])
                delta_n_displacement = abs(after_event_data['Delta N'] - before_event_data['Delta N'])
                delta_v_displacement = abs(after_event_data['Delta V'] - before_event_data['Delta V'])

                displacement_data = {
                    'Station ID': station_id,
                    'Event ID': event_id,
                    'Displacement': math.sqrt(delta_e_displacement**2 + delta_n_displacement**2)
                }

                # Save the displacement data to the dictionary
                displacement_dic[(station_id, event_id)] = displacement_data

        # Convert the displacement_dic to a dataframe
        displacement_df = pd.DataFrame.from_dict(displacement_dic, orient='index')

        # Load the earthquake information from the earthquakes.txt file
        earthquake_info = pre.load_eq_txt()

        # Merge displacement_df and earthquake_info based on 'Station ID' and 'Event ID'
        merged_df = pd.merge(displacement_df, earthquake_info[['Station ID', 'Event ID', 'Distance from Epicenter']],
                             on=['Station ID', 'Event ID'])

        # Debugging: Print merged data
        print(merged_df.head())

        # Plotting the data: Distance vs Displacement
        fig = Figure(figsize=(10, 6))
        axis = fig.add_subplot(1, 1, 1)

        # Plot distance from epicenter vs displacement
        axis.scatter(merged_df['Distance from Epicenter'], merged_df['Displacement'], color='blue')

        # Set labels and title
        axis.set_xlabel('Distance from Epicenter (km)')
        axis.set_ylabel('Displacement (m)')
        axis.set_title(f'Distance vs Displacement for Earthquake {event_id}')

        # Create an output stream and save the plot to it
        output = io.BytesIO()
        FigureCanvas(fig).print_png(output)

        # Return the plot as a response
        return Response(output.getvalue(), mimetype='image/png')

    except Exception as e:
        print(f"Error generating distance vs displacement plot: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400



def load_data():
    load_percentage = int(5)

    # Load and filter the data
    tenvs = pre.load_combined_df(load_percentage=load_percentage,
                                           target_magnitude=2,
                                           eq_count=2, save=False)

    filtered_tenvs_list = tenv_utils.split_combined_df_to_list(tenvs)
    return filtered_tenvs_list


if __name__ == '__main__':
    app.run(debug=True)
