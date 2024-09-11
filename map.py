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
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures

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


from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
from matplotlib import cm
import numpy as np

@app.route('/plot_distance_vs_displacement')
def plot_distance_vs_displacement():
    try:
        
        # Retrieve the event IDs from the request
        event_ids = request.args.get('event_ids')
        if not event_ids:
            raise ValueError("Event IDs are missing")

        # Convert the event_ids string to a list
        event_ids = event_ids.split(',')

        # Load the entire combined earthquake data
        combined_df = pd.read_csv(os.path.join(parent_path, 'all_earthquakes.csv'))

        displacement_dic = {}

        for event_id in event_ids:
            # Filter the combined data for the selected event
            event_data = combined_df[combined_df['Event ID'] == event_id]
            if event_data.empty:
                print(f"No event data found for Event ID: {event_id}")
                continue

            stations = event_data['Station ID']
            event_date = pd.to_datetime(event_data['Date'].iloc[0])

            for station_id in stations:
                # Find the day before and after the event date, then calculate displacement
                print(f"Processing Station ID: {station_id}, Event Date: {event_date}")
                before_event_data = combined_df[
                    (combined_df['Station ID'] == station_id) &
                    (pd.to_datetime(combined_df['Date']) < event_date)
                ].sort_values('Date').iloc[-1]

                after_event_data = combined_df[
                    (combined_df['Station ID'] == station_id) &
                    (pd.to_datetime(combined_df['Date']) > event_date)
                ].sort_values('Date').iloc[0]

                if before_event_data is not None and after_event_data is not None:
                    delta_e_displacement = abs(after_event_data['Delta E'] - before_event_data['Delta E'])
                    delta_n_displacement = abs(after_event_data['Delta N'] - before_event_data['Delta N'])
                    delta_v_displacement = abs(after_event_data['Delta V'] - before_event_data['Delta V'])

                    displacement_data = {
                        'Station ID': station_id,
                        'Event ID': event_id,
                        'Displacement': math.sqrt(delta_e_displacement**2 + delta_n_displacement**2),
                        'Magnitude': event_data['Event Magnitude'].iloc[0]  # Include magnitude
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

        # Handle NaN and infinity values
        merged_df = merged_df.replace([np.inf, -np.inf], np.nan)  # Replace inf with NaN
        merged_df = merged_df.dropna(subset=['Distance from Epicenter', 'Displacement'])  # Drop rows with NaN

        # Get unique magnitudes and create a colormap
        magnitudes = merged_df['Magnitude'].unique()
        num_magnitudes = len(magnitudes)
        cmap = cm.get_cmap('tab20', num_magnitudes)  # Use tab20 colormap for up to 20 magnitudes
        colors = {magnitude: cmap(i) for i, magnitude in enumerate(magnitudes)}

        # Plotting the data: Distance vs Displacement
        fig = Figure(figsize=(10, 6))
        axis = fig.add_subplot(1, 1, 1)

        # Plot distance from epicenter vs displacement with colors based on magnitude
        for magnitude in magnitudes:
            plot_data = merged_df[merged_df['Magnitude'] == magnitude]
            axis.scatter(plot_data['Distance from Epicenter'], plot_data['Displacement'], color=colors[magnitude], label=f"Magnitude {magnitude}")

            # Polynomial Regression (2nd order) for each earthquake
            X = plot_data['Distance from Epicenter'].values.reshape(-1, 1)
            y = plot_data['Displacement'].values.reshape(-1, 1)

            # Apply 2nd-degree polynomial features to X
            poly = PolynomialFeatures(degree=2)
            X_poly = poly.fit_transform(X)

            # Fit the polynomial regression model
            model = LinearRegression()
            model.fit(X_poly, y)

            # Predict the displacement using the polynomial regression model
            y_poly_pred = model.predict(X_poly)

            # Plot the polynomial regression curve for the earthquake
            axis.plot(plot_data['Distance from Epicenter'], y_poly_pred, label=f"Poly Fit Magnitude {magnitude}", color=colors[magnitude], linewidth=3)

        # Set labels and title
        axis.set_xlabel('Distance from Epicenter (km)')
        axis.set_ylabel('Displacement (m)')
        axis.set_title('Distance vs Displacement for Selected Earthquakes with Polynomial Regression')

        # Add a legend to differentiate magnitudes and polynomial regression lines
        axis.legend()

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
