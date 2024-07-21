"""
gps_timeseries.tenv_utils
~~~~~~~~~~~~~~

This module provides utility functions that are used to process .tenv files
"""


from datetime import datetime, timedelta
import numpy as np
from scipy.signal import find_peaks

def decimal_year_to_date(decimal_year):
        """Convert decimal year to datetime."""
        year = int(decimal_year)
        rem = decimal_year - year
        base = datetime(year, 1, 1)
        result_date = base + timedelta(seconds=(base.replace(year=year + 1) - base).total_seconds() * rem)
        return result_date

def create_index_file_mapping(tenvs, output_file='index_file_mapping.txt'):
    """
    Create a 1-1 map between the index and the IGS14 tenv file name and save it in a txt format.
    """
    with open(output_file, 'w') as f:
        for index, file_name in enumerate(tenvs):
            f.write(f"{index}: {file_name}\n")

def get_station_name_by_index(index, mapping_file='index_file_mapping.txt'):
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

def get_station_name_by_index(tenvs, index):
    """
    Get the station name (file name) using the index number.
    """
    if index < 0 or index >= len(tenvs):
        raise IndexError("Index out of range.")
    return tenvs[index]

'''
def displacement_detection(ts, peak_const = 0.02):
        """
        Detect the displacement caused by an earthquake on the given time series.
        """
        diff = np.diff(ts)
        peak_height = (diff.max() - diff.min()) * peak_const
        peaks, _ = find_peaks(diff, height=peak_height)
        return diff, peaks

'''