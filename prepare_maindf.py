import pandas as pd
import os
import math
from datetime import datetime
import socket
import constants
import numpy as np
import requests
import preprocessing as pr

# Get the hostname and initialize the parent_path based on the hostname
hostname = socket.gethostname()
parent_path = constants.PATHS.get(hostname, '/default/path/to/data')

pre = pr.Preprocessor(parent_path)

def get_earthquake_details(event_id):
    """
    Fetch earthquake details from USGS API for the given event_id.
    """
    try:
        url = f"https://earthquake.usgs.gov/fdsnws/event/1/query?eventid={event_id}&format=geojson"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            # Extract the required fields from the API response
            properties = data.get('properties', {})
            geometry = data.get('geometry', {})
            coordinates = geometry.get('coordinates', [])
            depth = coordinates[2] if len(coordinates) > 2 else None  # Depth is the 3rd value in 'coordinates'

            moment_tensor = next((product for product in properties.get('products', {}).get('moment-tensor', []) if product), {})
            nodal_plane_1 = {
                'strike': moment_tensor.get('properties', {}).get('nodal-plane-1-strike', None),
                'dip': moment_tensor.get('properties', {}).get('nodal-plane-1-dip', None),
                'rake': moment_tensor.get('properties', {}).get('nodal-plane-1-rake', None),
            }
            nodal_plane_2 = {
                'strike': moment_tensor.get('properties', {}).get('nodal-plane-2-strike', None),
                'dip': moment_tensor.get('properties', {}).get('nodal-plane-2-dip', None),
                'rake': moment_tensor.get('properties', {}).get('nodal-plane-2-rake', None),
            }
            t_axis = {
                'azimuth': moment_tensor.get('properties', {}).get('t-axis-azimuth', None),
                'plunge': moment_tensor.get('properties', {}).get('t-axis-plunge', None),
                'length': moment_tensor.get('properties', {}).get('t-axis-length', None),
            }
            p_axis = {
                'azimuth': moment_tensor.get('properties', {}).get('p-axis-azimuth', None),
                'plunge': moment_tensor.get('properties', {}).get('p-axis-plunge', None),
                'length': moment_tensor.get('properties', {}).get('p-axis-length', None),
            }
            n_axis = {
                'azimuth': moment_tensor.get('properties', {}).get('n-axis-azimuth', None),
                'plunge': moment_tensor.get('properties', {}).get('n-axis-plunge', None),
                'length': moment_tensor.get('properties', {}).get('n-axis-length', None),
            }

            tectonic_regime = properties.get('tectonic_regime', None)


            return {
                'Depth (km)': depth,
                'Nodal Plane 1 Strike': nodal_plane_1['strike'],
                'Nodal Plane 1 Dip': nodal_plane_1['dip'],
                'Nodal Plane 1 Rake': nodal_plane_1['rake'],
                'Nodal Plane 2 Strike': nodal_plane_2['strike'],
                'Nodal Plane 2 Dip': nodal_plane_2['dip'],
                'Nodal Plane 2 Rake': nodal_plane_2['rake'],
                'T-axis Azimuth': t_axis['azimuth'],
                'T-axis Plunge': t_axis['plunge'],
                'T-axis Length': t_axis['length'],
                'P-axis Azimuth': p_axis['azimuth'],
                'P-axis Plunge': p_axis['plunge'],
                'P-axis Length': p_axis['length'],
                'N-axis Azimuth': n_axis['azimuth'],
                'N-axis Plunge': n_axis['plunge'],
                'N-axis Length': n_axis['length'],
                'Tectonic Regime': tectonic_regime,
            }
        else:
            print(f"Error fetching data for event ID {event_id}: {response.status_code}")
            return {}
    except Exception as e:
        print(f"Exception while fetching details for event ID {event_id}: {e}")
        return {}

def process_and_save_merged_data_with_api(earthquakes_txt_path, all_earthquakes_csv_path, merged_output_csv_path, num_earthquakes=1):
    try:

        # Step 1: Extract unique event IDs from earthquakes.txt
        #with open(earthquakes_txt_path, 'r') as file:
         #   lines = file.readlines()

        # Extract the last column (event ID) from each line
        #event_ids = [line.split()[-1] for line in lines]
        event_ids = ['usp000by66', 'usp000fn3d', 'us10006jbi', 'us7000dflf'] 
        # Get unique event IDs
        unique_event_ids = list(set(event_ids))

        # Limit to the first `num_earthquakes` event IDs
        #unique_event_ids = unique_event_ids[:num_earthquakes]

        # Step 2: Load the earthquake data from the CSV file
        combined_df = pd.read_csv(all_earthquakes_csv_path)

        displacement_dic = {}

        # Step 3: Process displacement data for each unique event ID
        for event_id in unique_event_ids:
            # Filter the combined data for the selected event
            event_data = combined_df[combined_df['Event ID'] == event_id]
            if event_data.empty:
                print(f"No event data found for Event ID: {event_id}")
                continue
            event_data = event_data.drop_duplicates(subset=['Station ID'])
            stations = event_data['Station ID']
            event_date = pd.to_datetime(event_data['Date'].iloc[0])

            for station_id in stations:
                # Find the day before and after the event date, then calculate displacement
                print(f"Processing Station ID: {station_id}, Event Date: {event_date}, earthquake id: {event_id}")
                before_event_data = combined_df[
                    (combined_df['Station ID'] == station_id) &
                    (pd.to_datetime(combined_df['Date']) < event_date)
                ].sort_values('Date').iloc[-1]

                after_event_data = combined_df[
                    (combined_df['Station ID'] == station_id) &
                    (pd.to_datetime(combined_df['Date']) > event_date)
                ].sort_values('Date').iloc[0]

                if before_event_data is not None and after_event_data is not None:
                    # Calculate the displacement in different directions (E, N, V)
                    delta_e_displacement = abs(after_event_data['Delta E'] - before_event_data['Delta E'])
                    delta_n_displacement = abs(after_event_data['Delta N'] - before_event_data['Delta N'])
                    delta_v_displacement = abs(after_event_data['Delta V'] - before_event_data['Delta V'])

                    # Calculate total horizontal displacement
                    total_displacement = math.sqrt(delta_e_displacement**2 + delta_n_displacement**2)

                    displacement_data = {
                        'Station ID': station_id,
                        'Event ID': event_id,
                        'Displacement': total_displacement,
                        'Delta E': delta_e_displacement, 
                        'Delta N': delta_n_displacement,
                        'Delta V': delta_v_displacement,
                        'Magnitude': event_data['Event Magnitude'].iloc[0]  # Include magnitude
                    }

                    # Save the displacement data to the dictionary
                    displacement_dic[(station_id, event_id)] = displacement_data

        # Step 4: Convert the displacement_dic to a dataframe
        displacement_df = pd.DataFrame.from_dict(displacement_dic, orient='index')

        # Step 5: Load the earthquake information from the earthquakes.txt file (via the pre-existing function)
        earthquake_info = pre.load_eq_txt()

        # Step 6: Merge displacement_df and earthquake_info based on 'Station ID' and 'Event ID'
        merged_df = pd.merge(displacement_df, earthquake_info[['Station ID', 'Event ID', 'Distance from Epicenter']],
                             on=['Station ID', 'Event ID'])

        # Handle NaN and infinity values
        merged_df = merged_df.replace([np.inf, -np.inf], np.nan)  # Replace inf with NaN
        merged_df = merged_df.dropna(subset=['Distance from Epicenter', 'Displacement'])  # Drop rows with NaN

        # Step 7: For each unique event ID, fetch earthquake details via API and add to DataFrame
        for event_id in unique_event_ids:
            event_details = get_earthquake_details(event_id)
            if event_details:
                # Assign the details to the corresponding rows in the DataFrame
                for key, value in event_details.items():
                    merged_df.loc[merged_df['Event ID'] == event_id, key] = value

        # Step 8: Save the merged DataFrame to a CSV file
        merged_df.to_csv(merged_output_csv_path, index=False)
        print(f"Merged data with API details successfully saved to {merged_output_csv_path}")

    except Exception as e:
        print(f"Error processing and saving merged data: {e}")

# Example usage
earthquakes_txt_path = os.path.join(parent_path, 'earthquakes.txt')
all_earthquakes_csv_path = os.path.join(parent_path, 'all_earthquakes.csv')
merged_output_csv_path = os.path.join(parent_path, 'merged_displacement_data_with_api.csv')

# Call the function to process and save the merged data for the first 2 earthquakes, including additional API data
process_and_save_merged_data_with_api(earthquakes_txt_path, all_earthquakes_csv_path, merged_output_csv_path, num_earthquakes=10)
