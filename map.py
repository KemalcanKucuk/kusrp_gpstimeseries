import io
import os
import socket
from flask import Flask, jsonify, Response, request, render_template
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt 
import preprocessing as pr
import constants
import pandas as pd
import numpy as np

# Get the hostname and initialize the parent_path based on the hostname
hostname = socket.gethostname()
parent_path = constants.PATHS.get(hostname, '/default/path/to/data')

# Initialize the Preprocessor with the dynamic path
pre = pr.Preprocessor(parent_path)

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/load_stations')
def load_stations():
    try:
        load_percentage = int(request.args.get('load_percentage', 5))  # Default 5%
        magnitude_threshold = request.args.get('magnitude_threshold', None)
        earthquake_count = request.args.get('earthquake_count', None)

        magnitude_threshold = float(magnitude_threshold) if magnitude_threshold else None
        earthquake_count = int(earthquake_count) if earthquake_count else None

        print(f"Loading stations with load_percentage={load_percentage}, magnitude_threshold={magnitude_threshold}, earthquake_count={earthquake_count}")

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

@app.route('/plot.png')
def plot_png():
    try:
        # Retrieve the station ID from the request
        station_id = request.args.get('station_id')
        if not station_id:
            raise ValueError("Station ID is missing")

        # Load the combined data
        combined_df = pd.read_csv(os.path.join(parent_path, 'combined.csv'))
        
        # Filter the data for the given station
        station_data = combined_df[combined_df['Station ID'] == station_id]

        # Initialize a list to store displacement data
        displacement_data = []

        # Loop through each unique event ID to calculate displacements
        for event_id in station_data['Event ID'].dropna().unique():
            event_data = station_data[station_data['Event ID'] == event_id]

            # Get the magnitude from the day of the event
            event_magnitude = event_data['Event Magnitude'].iloc[0]

            # Ensure that the event date exists
            event_date = event_data['Date'].values[0]

            # Find the closest non-NaN value before the earthquake
            before_event_data = station_data[(station_data['Date'] < event_date) & station_data[['Delta E', 'Delta N', 'Delta V']].notna().all(axis=1)]
            if before_event_data.empty:
                print(f"No non-NaN data found before the event for {event_id}")
                continue
            day_before = before_event_data.iloc[-1]  # Take the closest before

            # Find the closest non-NaN value after the earthquake
            after_event_data = station_data[(station_data['Date'] > event_date) & station_data[['Delta E', 'Delta N', 'Delta V']].notna().all(axis=1)]
            if after_event_data.empty:
                print(f"No non-NaN data found after the event for {event_id}")
                continue
            day_after = after_event_data.iloc[0]  # Take the closest after

            # Calculate the displacement for each delta component
            delta_e_displacement = abs(day_after['Delta E'] - day_before['Delta E'])
            delta_n_displacement = abs(day_after['Delta N'] - day_before['Delta N'])
            delta_v_displacement = abs(day_after['Delta V'] - day_before['Delta V'])

            # Debugging: Print out the displacement for this event
            print(f"Event {event_id}: Magnitude = {event_magnitude}, Delta E = {delta_e_displacement}, Delta N = {delta_n_displacement}, Delta V = {delta_v_displacement}")

            # Append displacement data along with the event magnitude
            displacement_data.append([event_magnitude, delta_e_displacement, delta_n_displacement, delta_v_displacement])

        # Convert the displacement data into a DataFrame
        displacement_df = pd.DataFrame(displacement_data, columns=['Magnitude', 'Delta E', 'Delta N', 'Delta V'])

        # Debugging: Print the displacement data
        print(f"Displacement DataFrame:\n{displacement_df}")

        # Check if any data remains after filtering
        if displacement_df.empty:
            print("No valid displacement data available after filtering.")
            return jsonify({"status": "error", "message": "No valid displacement data available for this station"}), 400

        # Group by Magnitude and calculate mean displacement for each component
        displacement_grouped = displacement_df.groupby('Magnitude').mean().reset_index()

        # Plotting the displacement bar graph for each magnitude
        fig = Figure(figsize=(12, 6))
        axis = fig.add_subplot(1, 1, 1)

        bar_width = 0.2
        index = np.arange(len(displacement_grouped))

        # Plot bars for Delta E, Delta N, and Delta V
        axis.bar(index, displacement_grouped['Delta E'], bar_width, label='Delta E')
        axis.bar(index + bar_width, displacement_grouped['Delta N'], bar_width, label='Delta N')
        axis.bar(index + 2 * bar_width, displacement_grouped['Delta V'], bar_width, label='Delta V')

        axis.set_xlabel('Magnitude')
        axis.set_ylabel('Displacement (m)')
        axis.set_title(f'Displacement by Magnitude for Station {station_id}')
        axis.set_xticks(index + bar_width)
        axis.set_xticklabels(displacement_grouped['Magnitude'].round(2))
        axis.legend()

        # Create an output stream and save the plot to it
        output = io.BytesIO()
        FigureCanvas(fig).print_png(output)

        return Response(output.getvalue(), mimetype='image/png')

    except Exception as e:
        print(f"Error generating plot: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/plot_averaged_displacement')
def plot_averaged_displacement():
    try:
        # Retrieve the station IDs from the request
        station_ids = request.args.get('station_ids')
        if not station_ids:
            raise ValueError("No station IDs provided")

        # Split the station IDs into a list
        station_ids = station_ids.split(',')

        # Load the combined data
        combined_df = pd.read_csv(os.path.join(parent_path, 'combined.csv'))
        
        # Initialize a list to store displacement data across all stations
        all_displacement_data = []

        # Loop through each station and calculate the displacement for each event
        for station_id in station_ids:
            station_data = combined_df[combined_df['Station ID'] == station_id]
            
            # Collect displacements for this station
            displacement_data = []

            for event_id in station_data['Event ID'].dropna().unique():
                event_data = station_data[station_data['Event ID'] == event_id]

                event_magnitude = event_data['Event Magnitude'].iloc[0]
                event_date = event_data['Date'].values[0]

                # Find closest non-NaN data before and after the event
                before_event_data = station_data[(station_data['Date'] < event_date) & station_data[['Delta E', 'Delta N', 'Delta V']].notna().all(axis=1)]
                after_event_data = station_data[(station_data['Date'] > event_date) & station_data[['Delta E', 'Delta N', 'Delta V']].notna().all(axis=1)]

                if before_event_data.empty or after_event_data.empty:
                    continue

                day_before = before_event_data.iloc[-1]
                day_after = after_event_data.iloc[0]

                delta_e_displacement = abs(day_after['Delta E'] - day_before['Delta E'])
                delta_n_displacement = abs(day_after['Delta N'] - day_before['Delta N'])
                delta_v_displacement = abs(day_after['Delta V'] - day_before['Delta V'])

                displacement_data.append([event_magnitude, delta_e_displacement, delta_n_displacement, delta_v_displacement])

            # Append to the list of all stations' displacement data
            all_displacement_data.extend(displacement_data)

        # Convert the combined displacement data into a DataFrame
        displacement_df = pd.DataFrame(all_displacement_data, columns=['Magnitude', 'Delta E', 'Delta N', 'Delta V'])

        # Check if any data remains after filtering
        if displacement_df.empty:
            print("No valid displacement data available after filtering.")
            return jsonify({"status": "error", "message": "No valid displacement data available for the selected stations"}), 400

        # Group by Magnitude and calculate the mean displacement across all stations
        displacement_grouped = displacement_df.groupby('Magnitude').mean().reset_index()

        # Plotting the averaged displacement bar graph for each magnitude
        fig = Figure(figsize=(12, 6))
        axis = fig.add_subplot(1, 1, 1)

        bar_width = 0.2
        index = np.arange(len(displacement_grouped))

        # Plot bars for averaged Delta E, Delta N, and Delta V
        axis.bar(index, displacement_grouped['Delta E'], bar_width, label='Averaged Delta E')
        axis.bar(index + bar_width, displacement_grouped['Delta N'], bar_width, label='Averaged Delta N')
        axis.bar(index + 2 * bar_width, displacement_grouped['Delta V'], bar_width, label='Averaged Delta V')

        axis.set_xlabel('Magnitude')
        axis.set_ylabel('Averaged Displacement')
        axis.set_title(f'Averaged Displacement by Magnitude for Selected Stations')
        axis.set_xticks(index + bar_width)
        axis.set_xticklabels(displacement_grouped['Magnitude'].round(2))
        axis.legend()

        # Create an output stream and save the plot to it
        output = io.BytesIO()
        FigureCanvas(fig).print_png(output)

        return Response(output.getvalue(), mimetype='image/png')

    except Exception as e:
        print(f"Error generating averaged displacement plot: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)