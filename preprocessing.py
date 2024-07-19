import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

class Preprocessor:
    def __init__(self, parent_path, return_all=False):
        self.return_all = return_all
        self.parent_path = parent_path
        self.tenv_path = os.path.join(parent_path, 'IGS14')
        self.tenvs = sorted([f for f in os.listdir(self.tenv_path) if not f.startswith('.')])  # skip hidden files
        self.tenv_cols = ['Station ID', 'Date', 'Decimal Year', 'MJD', 'GPS Week',
                          'Day of the GPS Week', 'Delta E', 'Delta N', 'Delta V',
                          'Antenna Height', 'Sigma E', 'Sigma N', 'Sigma V',
                          'Correlation EN', 'Correlation EV', 'Correlation NV']
        self.add_cols = self.tenv_cols[:]
        self.add_cols[6:6] = ['Longitude']
        self.cols_by_count = {16: self.tenv_cols, 17: self.add_cols}  # to get rid of the additional conditions
        self.target_cols = ['Decimal Year', 'Delta E', 'Delta N', 'Delta V']

    def read_tenv_file(self, file_name):
        """
        Read a .tenv file given by filename and return a dataframe with the appropriate columns.
        """
        full_path = os.path.join(self.tenv_path, file_name)
        try:
            temp_df = pd.read_csv(full_path, sep='\s+', header=None, index_col=False, nrows=1)  # read the first row to get column count
            col_n = len(temp_df.columns)
            df = pd.read_csv(full_path, sep='\s+', index_col=False, names=self.cols_by_count[col_n], usecols=self.target_cols)
            if self.return_all:
                df = pd.read_csv(full_path, sep='\s+', index_col=False, names=self.cols_by_count[col_n])
            if col_n not in self.cols_by_count:
                print(f"Unexpected number of columns while reading {file_name}: {len(df.columns)}")
            return df
        except FileNotFoundError:
            print(f"The file {file_name} does not exist in {self.tenv_path}.")
        except Exception as e:
            print(f"An error occurred while reading {file_name}: {e}")

    def load_tenv_file_df(self, load_percentage=5):
        """
        Load the given percentage of the .tenv files according to the sorted file list.
        """
        file_count = int((load_percentage / 100) * len(self.tenvs))
        loaded_dfs = [self.read_tenv_file(self.tenvs[i]) for i in range(file_count)]
        return loaded_dfs

    def decimal_year_to_date(self, decimal_year):
        """Convert decimal year to datetime."""
        year = int(decimal_year)
        rem = decimal_year - year
        base = datetime(year, 1, 1)
        result_date = base + timedelta(seconds=(base.replace(year=year + 1) - base).total_seconds() * rem)
        return result_date

    def ayikla_pirincin_tasini(self, unprocessed_list, gap_tolerance=120):
        """
        Outlier points are deleted, series containing huge gaps are eliminated.

        :param unprocessed_list: loaded unprocessed list
        :type unprocessed_list: list
        :param gap_tolerance: Series containing gaps larger than the tolerance level are deleted
        :type gap_tolerance: int
        :rtype: list
        :return: Clean list
        """
        filtered_list, stations_with_gaps = self.gap_filter(unprocessed_list, gap_tolerance)
        if unprocessed_list:
            print(f'station: {self.get_station_name_by_index(0)} \n {unprocessed_list[0]} \n')
        return filtered_list, stations_with_gaps

    def gap_filter(self, unprocessed_list, gap_tolerance):
        filtered_files = []
        stations_with_gaps = []
        for i, df in enumerate(unprocessed_list):
            # Convert decimal year to datetime
            df['Date'] = df['Decimal Year'].apply(self.decimal_year_to_date)
            # Sort dates
            df = df.sort_values(by='Date')
            # Calculate the difference between consecutive dates
            df['Date_Diff'] = df['Date'].diff().dt.days
            # Check if any gaps are larger than gap_tolerance
            if df['Date_Diff'].max() <= gap_tolerance:
                filtered_files.append(df)
            else:
                stations_with_gaps.append(df)
        return filtered_files, stations_with_gaps

    def get_station_name_by_index(self, index):
        """
        Get the station name (file name) using the index number.
        """
        if index < 0 or index >= len(self.tenvs):
            raise IndexError("Index out of range.")
        return self.tenvs[index]

    def create_index_file_mapping(self, output_file='index_file_mapping.txt'):
        """
        Create a 1-1 map between the index and the IGS14 tenv file name and save it in a txt format.
        """
        with open(output_file, 'w') as f:
            for index, file_name in enumerate(self.tenvs):
                f.write(f"{index}: {file_name}\n")

    def get_station_name_by_index(self, index, mapping_file='index_file_mapping.txt'):
        """
        Get the station name from the index_file_mapping.txt using the index number.
        """
        if not os.path.exists(mapping_file):
            raise FileNotFoundError(f"Mapping file {mapping_file} not found.")
        with open(mapping_file, 'r') as f:
            lines = f.readlines()
            for line in lines:
                idx, file_name = line.strip().split(': ')
                if int(idx) == index:
                    return file_name
            raise IndexError(f"Index {index} not found in mapping file.")

    def decimal_year_to_date(self, decimal_year):
        """Convert decimal year to datetime."""
        year = int(decimal_year)
        rem = decimal_year - year
        base = datetime(year, 1, 1)
        result_date = base + timedelta(seconds=(base.replace(year=year + 1) - base).total_seconds() * rem)
        return result_date