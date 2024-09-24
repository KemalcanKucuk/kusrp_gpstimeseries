"""
gps_timeseries.preprocessing
~~~~~~~~~~~~~~

Preprocessor singleton class to read/load relevant data while applying relevant transformations.
"""

import os
import pandas as pd
import numpy as np
import tenv_utils


class Preprocessor:
    '''Class that handles the loading and filtering of earthquake data.
    Attributes:
        parent_path (str): String path containing the tenv directory.
        tenv_path (os.path): Path that contains the .tenv files.
        tenvs (list): Path that contains the .tenv files. 
    '''

    def __init__(self, parent_path):
        '''Initialize Preprocessor singleton on the parent path.
        Args:
            parent_path (string): String path containing the tenv directory.
        '''
        self.parent_path = parent_path
        self.tenv_path = os.path.join(parent_path, 'tenv')
        self.tenvs = sorted([os.path.splitext(f)[0] for f in os.listdir(
            self.tenv_path) if not f.startswith('.')])  # skip hidden files

    def read_tenv_file(self, stat_name, target_cols=['Station ID', 'Date', 'Delta E', 'Delta N', 'Delta V']):
        '''Read a .tenv file given by filename and return a dataframe with the appropriate columns.

        Args:
            file_name (string): Name of the .tenv to be loaded.
            target_cols (list, optional): The columns to be loaded from the .tenv file. Defaults to ['Station ID', 'Date', 'Delta E', 'Delta N', 'Delta V'].
        Returns:
            df (pd.DataFrame): Loaded data frame with transformations applied.
        '''
        tenv_cols = ['Station ID', 'Date', 'Decimal Year', 'MJD', 'GPS Week',
                     'Day of the GPS Week', 'Delta E', 'Delta N', 'Delta V',
                     'Antenna Height', 'Sigma E', 'Sigma N', 'Sigma V',
                     'Correlation EN', 'Correlation EV', 'Correlation NV']
        add_cols = tenv_cols[:]
        add_cols[6:6] = ['Longitude']
        file_name = stat_name + '.tenv'
        # to get rid of the additional conditions
        cols_by_count = {16: tenv_cols, 17: add_cols}

        full_path = os.path.join(self.tenv_path, file_name)
        try:
            # read the first row to get column count
            temp_df = pd.read_csv(full_path, sep='\s+',
                                  header=None, index_col=False, nrows=1)
            col_n = len(temp_df.columns)
            df = pd.read_csv(full_path, sep='\s+', index_col=False,
                             names=cols_by_count[col_n], usecols=target_cols)
            if col_n not in cols_by_count:
                print(
                    f"Unexpected number of columns while reading {file_name}: {len(df.columns)}")
            return df
        except FileNotFoundError:
            print(f"The file {file_name} does not exist in {self.tenv_path}.")
        except Exception as e:
            print(f"An error occurred while reading {file_name}: {e}")

    def load_tenv_file_df(self, tenvs, load_percentage=20, point_thr=1000):
        '''Load the given percentage of the .tenv files according to the sorted file list.

        Args:
            tenvs (list): _description_
            load_percentage (int, optional): Percentage of .tenv files to be loaded. Defaults to 5.

        Returns:
            combined_df (list): The DataFrame contaning the loaded dataframes for each .tenv file.
        '''
        if len(tenvs) == 0:
            raise ValueError("No valid stations are given.")
        file_count = int((load_percentage / 100) * len(tenvs))
        loaded_dfs = [self.read_tenv_file(tenvs[i]) for i in range(file_count)]
        if len(loaded_dfs) == 0:
            raise ValueError(
                "No time series data available for the given stations.")
        filtered_tenvs = [df for df in loaded_dfs if len(df.index) >= point_thr]

        combined_df = pd.concat(filtered_tenvs, ignore_index=True)
        combined_df['Date'] = tenv_utils.strdate_to_datetime(combined_df['Date'])
        return combined_df

    def load_station_info(self):
        '''Load the station.txt file with the appropriate columns.

        Args: 
            None

        Returns:
            stations (pd.DataFrame): Loaded dataframe from the station file.
        '''
        station_file = 'llh.out.txt'  # Adjust this to the correct filename
        file_path = os.path.join(self.parent_path, station_file)

        cols = ['Station ID', 'Lat', 'Long', 'Hgt']
        stations = pd.read_csv(file_path, delim_whitespace=True, header=None,
                            index_col=False, names=cols)
        
        return stations

    def load_eq_txt(self, target_cols=['Station ID', 'Date', 'Distance from Epicenter', 'Event Magnitude', 'Event ID']):
        '''Load the earthquakes.txt file with appropriate columns.

        Args: 
            target_cols (list, optional): The columns to be loaded from the EQ file. Defaults to ['Station ID', 'Date', 'Distance from Epicenter', 'Event Magnitude'].

        Returns:
            eqs (pd.DataFrame): Loaded dataframe from the EQ file.
        '''
        eq_file = 'earthquakes.txt'
        file_path = os.path.join(self.parent_path, eq_file)
        cols = ['Station ID', 'Date', 'Code', 'Threshold Distance',
                'Distance from Epicenter', 'Event Magnitude', 'Event ID']

        eqs = pd.read_csv(file_path, sep='\s+', header=None,
                          index_col=False, names=cols, usecols=target_cols)
        eqs['Date'] = tenv_utils.strdate_to_datetime(eqs['Date'])
        return eqs

    def load_combined_df(self, gap_tolerance=1000, load_percentage=5, target_magnitude=None, eq_count=None, save=False, method='lof', n_neighbors=20, contamination=0.35):
        '''Load and filter combined dataframe of .tenv files based on specified conditions.

        This function extracts .tenv files that have earthquakes, applies various filtering conditions,
        and combines the resulting data into a single dataframe. The filtering conditions include gap tolerance,
        earthquake count, and target magnitude.

        Args:
            gap_tolerance (int, optional): Gap tolerance threshold in days to filter out stations with large data gaps. Defaults to 1000.
            load_percentage (int, optional): Percentage of .tenv files to be loaded. Defaults to 5.
            target_magnitude (float, optional): Minimum earthquake magnitude to filter the earthquakes. Defaults to None.
            eq_count (int, optional): Exact number of unique earthquake events required per station. Defaults to None.

        Returns:
            pd.DataFrame: Combined dataframe with filtered .tenv data and merged earthquake events.

        Raises:
            ValueError: If no stations meet the earthquake count filter condition.
            ValueError: If no earthquakes meet the magnitude filter condition.
            ValueError: If no stations meet the combined filtering conditions.
        '''
        # extract .tenv files that have earthquakes
        eqs = self.load_eq_txt()

        # filter by earthquake count
        if eq_count is not None:
            # group by station and count unique event ids
            station_event_counts = eqs.groupby(
                'Station ID')['Event ID'].nunique()
            filtered_stations = station_event_counts[station_event_counts == eq_count].index
            eqs = eqs[eqs['Station ID'].isin(filtered_stations)]
            if eqs.empty:
                raise ValueError(
                    "No stations meet the earthquake count filter condition.")

        # filter by magnitude
        if target_magnitude is not None:
            eqs = eqs[eqs['Event Magnitude'] >= target_magnitude]
            if eqs.empty:
                raise ValueError(
                    "No earthquakes meet the magnitude filter condition.")

        if eqs.empty:
            raise ValueError("No stations meet the filtering conditions.")

       # load the stations with filtered earthquakes
        eq_stats = eqs['Station ID'].unique()
        tenvs_df = self.load_tenv_file_df(
            tenvs=eq_stats, load_percentage=load_percentage)
        #tenvs_df, _, _ = tenv_utils.apply_filtering(tenvs_df, gap_tolerance=100, method=method, n_neighbors=n_neighbors, contamination=contamination)

        
        # append missing earthquake dates to the timeseries data with NaN values for the timeseries columns
        all_stations_dfs = []
        for station_id, station_df in tenvs_df.groupby('Station ID'):
            station_eqs = eqs[eqs['Station ID'] == station_id]
            missing_dates = station_eqs[~station_eqs['Date'].isin(station_df['Date'])]

            if not missing_dates.empty:
                missing_rows = pd.DataFrame({
                    'Station ID': station_id,
                    'Date': missing_dates['Date'],
                    'Delta E': np.nan,
                    'Delta N': np.nan,
                    'Delta V': np.nan
                })
                station_df = pd.concat([station_df, missing_rows], ignore_index=True)

            all_stations_dfs.append(station_df)

        combined_tenvs_df = pd.concat(all_stations_dfs)
        # combined_df, _, _ = tenv_utils.apply_filtering(tenvs_df, gap_tolerance=gap_tolerance)
        combined_df = pd.merge(combined_tenvs_df, eqs[['Station ID', 'Date', 'Event ID', 'Event Magnitude', 'Distance from Epicenter']], on=['Station ID', 'Date'], how='left')
        # sanity check
        total_eqs = eqs['Event ID'].nunique()
        loaded_eqs = combined_df['Event ID'].nunique()
        print(f"\033[93mINFO: Loaded {loaded_eqs} of {total_eqs} earthquake events. \033[0m")
        if save:
            filename = f'loadp{load_percentage}' # @TODO: edit this so that it matches the called method arguments
            # @TODO: gropby event id
            filename = 'combined_tenv.csv'
            filepath = os.path.join(self.parent_path, filename)
            combined_df.to_csv(filepath, index=False)
            print(f"\033[93mINFO: Successfully saved the combined dataframe to {filepath}. \033[0m")
        return combined_df
