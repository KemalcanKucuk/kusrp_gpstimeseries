# KUSRP GPS Timeseries

## Overview
This repository contains scripts and analysis for handling GPS timeseries data related to earthquake events. It focuses on preprocessing, analyzing, and visualizing geodetic data from multiple stations to detect potential seismic activity.

## Installation

### Prerequisites
- Python 3.x
- ~~Required packages (install via `requirements.txt` [not available at the moment]):~~

### Setup
1. Clone the repository:
  ```bash
  git clone https://github.com/KemalcanKucuk/kusrp_gpstimeseries.git
  ```
2. Navigate to the project directory:
  ```bash
  cd kusrp_gpstimeseries
  ```
3. ~~Install dependencies:~~
  ```bash
  pip install -r requirements.txt
  ```
4. Fetch the .tenv files from the Nevada Geodetic Laboratory (this may take a while)
   ```bash
   wget -r -np -nH --cut-dirs=3 -R "index.html*" -A "*.tenv" -P ./geodesy_data/tenv/ http://geodesy.unr.edu/gps_timeseries/tenv/IGS14/
   ```
5. Run the script to prepare the GPS time series data from the .tenv files
    ```bash
   python create_tenv_data.py --save
   ```

The necessary data for earthquake events is supplied at geodesy_data/cleaned_combined_api_data.csv

6. ~~(Optional) Run the script to prepare the earthquake event folders (add the api script).~~
    ```bash
   python create_tenv_data.py --save
   ```
## Usage
@TODO: notebooks and scripts run really poorly we can patch them up, i've archived them for now.


## Folder Structure

kusrp_gpstimeseries/
├── analysis/       # Data analysis scripts and results
├── archive/        # Archived code
├── notebooks/      # Jupyter notebooks for interactive analysis
├── outs/           # Output files, visualizations, and results
├── src/            # Source code for data processing and analysis
├── static/         # Static resources (for the map site)
├── requirements.txt
└── README.md       # Project description

## Contributing
1. Fork the repository.
2. Create a branch for your feature (`git checkout -b feature-branch`).
3. Make changes and commit (`git commit -m 'Add feature'`).
4. Push to your branch (`git push origin feature-branch`).
5. Create a pull request.