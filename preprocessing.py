import pandas as pd
import numpy as np
import os

class Preprocessor:
    def __init__(self, parent_path, return_all = False):
        self.return_all = return_all
        self.parent_path = parent_path
        self.tenv_path = os.path.join(parent_path, 'IGS14')
        self.sta_path = os.path.join(parent_path, 'stations')
        self.tenvs = sorted([f for f in os.listdir(self.tenv_path) if not f.startswith('.')]) # skip hidden files
        self.stats = sorted([f for f in os.listdir(self.sta_path) if not f.startswith('.')])
        self.tenv_cols = ['Station ID', 'Date', 'Decimal Year', 'MJD', 'GPS Week', 
                          'Day of the GPS Week', 'Delta E', 'Delta N', 'Delta V', 
                          'Antenna Height', 'Sigma E', 'Sigma N', 'Sigma V', 
                          'Correlation EN', 'Correlation EV', 'Correlation NV']
        self.add_cols = self.tenv_cols[:]
        self.add_cols[6:6] = ['Longitude']
        self.cols_by_count = {16: self.tenv_cols, 17: self.add_cols} # to get rid of the additional conditions
        self.target_cols = ['Decimal Year', 'Delta E', 'Delta N', 'Delta V']

    def read_tenv_file(self, file_name):
            """
            Read a .tenv file given by filename and return a dataframe with the appropriate columns.
            """
            full_path = os.path.join(self.tenv_path, file_name)
            try:
                # read the first row to get column count
                temp_df = pd.read_csv(full_path, delim_whitespace=True, header=None, index_col=False, nrows=1)
                col_count = len(temp_df.columns)
                # only the target columns are loaded due to memory efficiency
                df = pd.read_csv(full_path, delim_whitespace=True, index_col=False, names=self.cols_by_count[col_count], usecols=self.target_cols)
                if self.return_all:
                    # return all of the available columns
                    df = pd.read_csv(full_path, delim_whitespace=True, index_col=False, names=self.cols_by_count[col_count])
                if col_count not in self.cols_by_count:
                    # check if there're any outliers remaining
                    print(f"Unexpected number of columns while reading {file_name}: {len(df.columns)}")              
                # we can apply normalization and other transformations here but i'll check the performance differences 
                return df
            except FileNotFoundError:
                print(f"The file {file_name} does not exist in {self.tenv_path}.")
            except Exception as e:
                print(f"An error occurred while reading {file_name}: {e}")  
    
    def load_tenv_file_df(self, load_percentage = 5):
        """
        Load the given percentage of the .tenv files according to the sorted file list.
        """
        file_count = int((load_percentage / 100) * len(self.tenvs))
        loaded_dfs= []
        for i in range(file_count):
            loaded_dfs.append(self.read_tenv_file(self.tenvs[i]))
        return loaded_dfs
    


    