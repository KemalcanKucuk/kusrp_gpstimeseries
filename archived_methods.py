"""
gps_timeseries.archive.archived_methods
~~~~~~~~~~~~~~

Contains currently unused methods for future reference.
"""

from datetime import datetime, timedelta
import numpy as np
from scipy.signal import find_peaks

def decimal_year_to_date(decimal_year):
    """Convert decimal year to datetime."""
    year = int(decimal_year)
    rem = decimal_year - year
    base = datetime(year, 1, 1)
    result_date = base + \
        timedelta(seconds=(base.replace(year=year + 1) -
                  base).total_seconds() * rem)
    return result_date

def create_index_file_mapping(tenvs, output_file='index_file_mapping.txt'):
    """
    Create a 1-1 map between the index and the IGS14 tenv file name and save it in a txt format.
    """
    with open(output_file, 'w') as f:
        for index, file_name in enumerate(tenvs):
            f.write(f"{index}: {file_name}\n")

def displacement_detection(ts, peak_const = 0.02):
        """
        Detect the displacement caused by an earthquake on the given time series.
        """
        diff = np.diff(ts)
        peak_height = (diff.max() - diff.min()) * peak_const
        peaks, _ = find_peaks(diff, height=peak_height)
        return diff, peaks


