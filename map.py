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


# Old Plotting Logic (Unchanged)
@app.route('/plot.png')
def plot_png():
    try:
        station_id = request.args.get('station_id')
        if not station_id:
            raise ValueError("Station ID is missing")

        # Load the combined data
        combined_df = pd.read_csv(os.path.join(parent_path, 'combined.csv'))
        station_data = combined_df[combined_df['Station ID'] == station_id]

        displacement_data = []

        for event_id in station_data['Event ID'].dropna().unique():
            event_data = station_data[station_data['Event ID'] == event_id]
            event_magnitude = event_data['Event Magnitude'].iloc[0]
            event_date = event_data['Date'].values[0]

            before_event_data = station_data[
                (station_data['Date'] < event_date) & station_data[['Delta E', 'Delta N', 'Delta V']].notna().all(
                    axis=1)]
            after_event_data = station_data[
                (station_data['Date'] > event_date) & station_data[['Delta E', 'Delta N', 'Delta V']].notna().all(
                    axis=1)]

            if before_event_data.empty or after_event_data.empty:
                continue

            day_before = before_event_data.iloc[-1]
            day_after = after_event_data.iloc[0]

            delta_e_displacement = abs(day_after['Delta E'] - day_before['Delta E'])
            delta_n_displacement = abs(day_after['Delta N'] - day_before['Delta N'])
            delta_v_displacement = abs(day_after['Delta V'] - day_before['Delta V'])

            displacement_data.append(
                [event_magnitude, delta_e_displacement, delta_n_displacement, delta_v_displacement])

        displacement_df = pd.DataFrame(displacement_data, columns=['Magnitude', 'Delta E', 'Delta N', 'Delta V'])

        if displacement_df.empty:
            print("No valid displacement data available after filtering.")
            return jsonify({"status": "error", "message": "No valid displacement data available for this station"}), 400

        displacement_grouped = displacement_df.groupby('Magnitude').mean().reset_index()

        fig = Figure(figsize=(12, 6))
        axis = fig.add_subplot(1, 1, 1)

        bar_width = 0.2
        index = np.arange(len(displacement_grouped))

        axis.bar(index, displacement_grouped['Delta E'], bar_width, label='Delta E')
        axis.bar(index + bar_width, displacement_grouped['Delta N'], bar_width, label='Delta N')
        axis.bar(index + 2 * bar_width, displacement_grouped['Delta V'], bar_width, label='Delta V')

        axis.set_xlabel('Magnitude')
        axis.set_ylabel('Displacement (m)')
        axis.set_title(f'Displacement by Magnitude for Station {station_id}')
        axis.set_xticks(index + bar_width)
        axis.set_xticklabels(displacement_grouped['Magnitude'].round(2))
        axis.legend()

        output = io.BytesIO()
        FigureCanvas(fig).print_png(output)

        return Response(output.getvalue(), mimetype='image/png')

    except Exception as e:
        print(f"Error generating plot: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400


# New Plotting Logic: Distance vs Displacement for Earthquake
@app.route('/plot_distance_vs_displacement')
def plot_distance_vs_displacement():
    try:
        # Retrieve the event ID from the request
        event_id = request.args.get('event_id')
        if not event_id:
            raise ValueError("Event ID is missing")

        # Load the combined earthquake data
        combined_df = pd.read_csv(os.path.join(parent_path, 'all_earthquakes.csv'))

        # Load earthquake information from the earthquakes.txt file
        earthquake_info = pre.load_eq_txt()

        # Filter the combined data for the selected event
        event_data = combined_df[combined_df['Event ID'] == event_id]
        if event_data.empty:
            print(f"No event data found for Event ID: {event_id}")
            return jsonify({"status": "error", "message": "No data found for the given earthquake event"}), 400

        # Get distances for all stations from earthquakes.txt
        event_distances = earthquake_info[earthquake_info['Event ID'] == event_id]

        if event_distances.empty:
            print(f"No distances found for Event ID: {event_id}")
            return jsonify({"status": "error", "message": "No distances found for the given earthquake event"}), 400

        # Merge combined_df with event_distances to get the Distance from Epicenter
        merged_df = pd.merge(event_data, event_distances[['Station ID', 'Distance from Epicenter']], on='Station ID')

        # Initialize lists to store displacements and distances
        displacement_data = []
        for station_id, station_df in merged_df.groupby('Station ID'):
            # Log for debugging each station
            print(f"Processing Station ID: {station_id}")

            # Get displacement for each event
            for event_id in station_df['Event ID'].dropna().unique():
                event_data = station_df[station_df['Event ID'] == event_id]

                event_magnitude = event_data['Event Magnitude'].iloc[0]
                event_date = event_data['Date'].values[0]

                # Find closest non-NaN data before and after the event
                before_event_data = station_df[(station_df['Date'] < event_date) & station_df[['Delta E', 'Delta N', 'Delta V']].notna().all(axis=1)]
                after_event_data = station_df[(station_df['Date'] > event_date) & station_df[['Delta E', 'Delta N', 'Delta V']].notna().all(axis=1)]

                # Log for missing data before or after
                if before_event_data.empty:
                    print(f"No valid data found before the event for Station ID: {station_id}, Event ID: {event_id}")
                if after_event_data.empty:
                    print(f"No valid data found after the event for Station ID: {station_id}, Event ID: {event_id}")

                if before_event_data.empty or after_event_data.empty:
                    continue

                day_before = before_event_data.iloc[-1]
                day_after = after_event_data.iloc[0]

                delta_e_displacement = abs(day_after['Delta E'] - day_before['Delta E'])
                delta_n_displacement = abs(day_after['Delta N'] - day_before['Delta N'])
                delta_v_displacement = abs(day_after['Delta V'] - day_before['Delta V'])

                displacement_data.append([station_id, event_data['Distance from Epicenter'].iloc[0],
                                          delta_e_displacement, delta_n_displacement, delta_v_displacement])

        # Convert the displacement data into a DataFrame
        displacement_df = pd.DataFrame(displacement_data, columns=['Station ID', 'Distance from Epicenter', 'Delta E', 'Delta N', 'Delta V'])

        # Check if any data remains after filtering
        if displacement_df.empty:
            print(f"No valid displacement data available for Event ID: {event_id}")
            return jsonify({"status": "error", "message": "No valid displacement data available for this earthquake"}), 400

        # Calculate mean displacements for plotting
        displacement_grouped = displacement_df.groupby('Distance from Epicenter').mean().reset_index()

        # Plotting the displacement vs distance from epicenter
        fig = Figure(figsize=(12, 6))
        axis = fig.add_subplot(1, 1, 1)

        axis.plot(displacement_grouped['Distance from Epicenter'], displacement_grouped['Delta E'], label='Delta E')
        axis.plot(displacement_grouped['Distance from Epicenter'], displacement_grouped['Delta N'], label='Delta N')
        axis.plot(displacement_grouped['Distance from Epicenter'], displacement_grouped['Delta V'], label='Delta V')

        axis.set_xlabel('Distance from Epicenter (km)')
        axis.set_ylabel('Displacement (m)')
        axis.set_title(f'Displacement vs Distance from Epicenter for Earthquake {event_id}')
        axis.legend()

        # Create an output stream and save the plot to it
        output = io.BytesIO()
        FigureCanvas(fig).print_png(output)

        return Response(output.getvalue(), mimetype='image/png')

    except Exception as e:
        print(f"Error generating distance vs displacement plot: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400




# Stations for Earthquake Route
@app.route('/stations_for_earthquake')
def stations_for_earthquake():
    try:
        event_id = request.args.get('event_id')
        if not event_id:
            raise ValueError("Event ID is missing")

        combined_df = pd.read_csv(os.path.join(parent_path, 'all_earthquakes.csv'))
        event_data = combined_df[combined_df['Event ID'] == event_id]

        if event_data.empty:
            return jsonify({"status": "error", "message": "No stations found for the given earthquake event"}), 400

        station_df = pre.load_station_info()
        affected_stations = station_df[station_df['Station ID'].isin(event_data['Station ID'].unique())]

        if affected_stations.empty:
            return jsonify({"status": "error", "message": "No stations found with earthquake data"}), 400

        stations = []
        for _, row in affected_stations.iterrows():
            stations.append({
                'station_id': row['Station ID'],
                'lat': row['Lat'],
                'lon': row['Long']
            })

        return jsonify({"status": "success", "stations": stations})

    except Exception as e:
        print(f"Error loading stations for earthquake: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400


# Earthquake List Route
@app.route('/earthquake_list')
def earthquake_list():
    try:
        combined_df = pd.read_csv(os.path.join(parent_path, 'all_earthquakes.csv'))
        combined_df = combined_df.dropna(subset=['Event ID', 'Event Magnitude'])
        earthquake_df = combined_df[['Event ID', 'Event Magnitude']].drop_duplicates()
        earthquakes = earthquake_df.to_dict(orient='records')
        return jsonify({"status": "success", "earthquakes": earthquakes})

    except Exception as e:
        print(f"Error loading earthquake list: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400


if __name__ == '__main__':
    app.run(debug=True)
