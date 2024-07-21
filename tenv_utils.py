"""
gps_timeseries.tenv_utils
~~~~~~~~~~~~~~

This module provides utility functions that are used to process .tenv files
"""
import os
from datetime import datetime, timedelta
import numpy as np
from scipy.signal import find_peaks

def datestr_to_date(date_str):
    # Dictionary to map month abbreviations to numbers
    months = {
        'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4,
        'MAY': 5, 'JUN': 6, 'JUL': 7, 'AUG': 8,
        'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
    }
    
    # Extract parts from the string
    year_str = date_str[:2]
    month_str = date_str[2:5]
    day_str = date_str[5:]
    
    # Convert year to four digits based on a threshold
    year = int(year_str)
    if year < 50:
        year += 2000  # Years 00-49 -> 2000-2049
    else:
        year += 1900  # Years 50-99 -> 1950-1999
    
    # Convert month and day to integers
    month = months[month_str.upper()]
    day = int(day_str)
    
    # Create datetime object
    date = datetime(year, month, day)
    
    # Convert to target format
    target_date_str = date.strftime('%Y-%m-%d %H:%M:%S.%f')
    return target_date_str

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