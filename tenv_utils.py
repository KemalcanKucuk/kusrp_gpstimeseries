"""
gps_timeseries.tenv_utils
~~~~~~~~~~~~~~

This module provides utility functions that are used to process .tenv files
"""
from datetime import datetime
import pandas as pd


def strdate_to_datetime(date_col):
    '''Convert the given date column of a dataframe to datetime format.

    Args:
        date_col (pandas.Series): The date column of a dataframe.
    Returns:
        date_col (pandas.Series): The date column of a dataframe converted to datetime.
    '''
    def datestr_to_date(date_str):
        '''Convert a string date to datetime.

        Args:
            date_str (string): Date string in format of YEARMONTHDAY.

        Returns:
            target_date_str (string): Date string in format of datetime.
        '''
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

    date_col = date_col.apply(datestr_to_date)
    date_col = pd.to_datetime(date_col)

    return date_col


def gap_filter(combined_df, gap_tolerance):
    '''Filter out the stations that have gaps between the data that is above the tolerance threshold.

    Args:
        combined_df (pd.DataFrame): Combined dataframe of all stations.
        gap_tolerance (int): Gap tolerance threshold in days.

    Returns:
        filtered_df (pd.DataFrame): DataFrame of rows that aren't filtered out by the threshold.
        stations_with_gaps_df (pd.DataFrame): DataFrame of rows that are filtered out by the threshold.
    '''
    combined_df['Date'] = strdate_to_datetime(combined_df['Date'])
    filtered_list = []
    stations_with_gaps = []
    
    # Group by 'Station ID' to check gaps per station
    grouped = combined_df.groupby('Station ID')
    
    for station_id, group in grouped:
        # Sort dates
        group = group.sort_values(by='Date')
        # Calculate the difference between consecutive dates
        group['Date_Diff'] = group['Date'].diff().dt.days
        # Check if any gaps are larger than gap_tolerance
        if group['Date_Diff'].max() <= gap_tolerance:
            filtered_list.append(group.drop(columns=['Date_Diff']))
        else:
            stations_with_gaps.append(group.drop(columns=['Date_Diff']))
    
    # Concatenate the results back into DataFrames
    if filtered_list:
        filtered_df = pd.concat(filtered_list, ignore_index=True)
    else:
        # return the combined df
        filtered_df = combined_df
        print('\033[93mINFO: No stations with the gap threshold filter. \033[0m')
    if stations_with_gaps:
        stations_with_gaps_df = pd.concat(stations_with_gaps, ignore_index=True)
    else:
        stations_with_gaps_df = combined_df
        print('\033[93mINFO: All of the stations are above the gap threshold filter. \033[0m')
    
    return filtered_df, stations_with_gaps_df

def apply_filtering(combined_df, gap_tolerance=120):
    '''Outlier points are deleted, series containing huge gaps are eliminated.

    Args:
        combined_df (pd.DataFrame): Combined dataframe of all stations.
        gap_tolerance (int, optional): Amount of days to filter out a given station. Defaults to 120.

    Returns:
        tuple: (filtered_df, stations_with_gaps_df)
    '''
    filtered_df, stations_with_gaps_df = gap_filter(combined_df, gap_tolerance)
    if not combined_df.empty:
        pass
        # print(f'station: {self.get_station_name_by_index(0)} \n {combined_df.head()} \n')
    # @TODO: outlier filtering

    return filtered_df, stations_with_gaps_df

def split_combined_df_to_list(combined_df):
    """Split a combined dataframe into a list of dataframes, each corresponding to a unique station. 
    This functions exists because I got too lazy to change the previous code and notebooks used for plotting.

    Args:
        combined_df (pd.DataFrame): The combined dataframe with data for multiple stations.

    Returns:
        list: A list of dataframes, where each dataframe contains the data for a single station.
    """
    # Group the combined dataframe by 'Station ID' and convert each group to a separate dataframe
    station_dfs = [group for _, group in combined_df.groupby('Station ID')]
    
    return station_dfs