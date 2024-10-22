import sys
import folium
import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, QPushButton, QLabel, QFormLayout
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtCore import QUrl
import preprocessing as pr
import constants
import socket

# Step 1: Custom QWebEnginePage to handle the JavaScript interaction
class MyWebEnginePage(QWebEnginePage):
    def acceptNavigationRequest(self, url, _type, is_main_frame):
        # Handle any other navigation if needed
        return super().acceptNavigationRequest(url, _type, is_main_frame)

class StationPlotApp(QMainWindow):
    def __init__(self, parent_path):
        super().__init__()

        self.setWindowTitle("Station Plot App")
        self.setGeometry(100, 100, 1600, 900)  # Set window size

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QHBoxLayout(self.central_widget)

        self.parent_path = parent_path
        self.pre = pr.Preprocessor(parent_path)

        self.create_controls()
        self.create_map()

    def create_map(self):
        # Create map widget and add to layout
        self.map_layout = QVBoxLayout()
        self.map = folium.Map(location=[0, 0], zoom_start=2)

        # Save the map to an HTML file in the current directory
        current_dir = os.path.dirname(os.path.abspath(__file__))  # Get the current file directory
        map_path = os.path.join(current_dir, 'map.html')
        self.map.save(map_path)

        # Set up QWebEngineView
        self.web_view = QWebEngineView()
        self.web_view.setPage(MyWebEnginePage(self))  # Use the custom page
        self.web_view.setUrl(QUrl.fromLocalFile(map_path))
        self.web_view.loadFinished.connect(self.on_page_load_finished)  # Connect loadFinished signal
        self.map_layout.addWidget(self.web_view)

        # Add the map layout to the main layout
        self.main_layout.addLayout(self.map_layout, stretch=4)

    def on_page_load_finished(self):
        # Define the JavaScript function after the page has loaded
        js_code = """
        function plotStation(stationId) {
            console.log('Station ID: ' + stationId);
            qt.python.call('plotStation', stationId);  // Call the Python function
        }
        """
        self.web_view.page().runJavaScript(js_code)

    def create_controls(self):
        # Create a layout for the control inputs and condense them into the top-right corner
        control_layout = QFormLayout()

        self.load_percentage_input = QLineEdit()
        self.load_percentage_input.setPlaceholderText("5")
        control_layout.addRow(QLabel("Load Percentage:"), self.load_percentage_input)

        self.magnitude_threshold_input = QLineEdit()
        self.magnitude_threshold_input.setPlaceholderText("Enter magnitude threshold")
        control_layout.addRow(QLabel("Magnitude Threshold:"), self.magnitude_threshold_input)

        self.earthquake_count_input = QLineEdit()
        self.earthquake_count_input.setPlaceholderText("Enter earthquake count")
        control_layout.addRow(QLabel("Earthquake Count:"), self.earthquake_count_input)

        self.load_plot_button = QPushButton("Load and Plot")
        self.load_plot_button.clicked.connect(self.load_data)
        control_layout.addRow(self.load_plot_button)

        self.info_label = QLabel("Load and filter data to see the details here.")
        control_layout.addRow(self.info_label)

        # Create a container widget for controls and add it to the top-right corner
        controls_container = QWidget()
        controls_container.setLayout(control_layout)
        self.main_layout.addWidget(controls_container, stretch=1)

    def load_data(self):
        load_percentage = int(self.load_percentage_input.text() or 5)
        magnitude_threshold = float(self.magnitude_threshold_input.text()) if self.magnitude_threshold_input.text() else None
        earthquake_count = int(self.earthquake_count_input.text()) if self.earthquake_count_input.text() else None

        # Load and filter the data
        self.tenvs = self.pre.load_combined_df(load_percentage=load_percentage,
                                               target_magnitude=magnitude_threshold,
                                               eq_count=earthquake_count, save=True)

        self.update_map()

    def update_map(self):
        # Filter stat_position_df based on the stations in main_df
        filtered_stations = self.pre.load_station_info()  # Load station information

        station_ids_in_main_df = self.tenvs['Station ID'].unique()
        filtered_stations = filtered_stations[filtered_stations['Station ID'].isin(station_ids_in_main_df)]

        # Re-create the map with filtered stations
        self.map = folium.Map(location=[0, 0], zoom_start=2)
        for index, row in filtered_stations.iterrows():
            station_id = row['Station ID']

            # Get the magnitudes and count of earthquakes for this station
            station_eqs = self.tenvs[self.tenvs['Station ID'] == station_id]
            magnitudes = station_eqs['Event Magnitude'].dropna().tolist()  # Filter out NaNs
            earthquake_count = len(magnitudes)

            # If no magnitudes are available after filtering, skip this marker
            if earthquake_count == 0:
                continue

            # Create a popup with magnitudes and earthquake count information
            popup_content = f"""
            <b>Station ID:</b> {station_id}<br>
            <b>Earthquake Count:</b> {earthquake_count}<br>
            <b>Magnitudes:</b> {', '.join(map(str, magnitudes))}<br>
            <button onclick="plotStation('{station_id}')">Show Plot</button>
            """
            popup = folium.Popup(popup_content, max_width=300)

            marker = folium.Marker(
                location=[row['Lat'], row['Long']],
                popup=popup,
                icon=folium.Icon(color='red', icon='info-sign')
            )
            marker.add_to(self.map)

        # Save the updated map and reload it in the web view
        current_dir = os.path.dirname(os.path.abspath(__file__))
        map_path = os.path.join(current_dir, 'map.html')
        self.map.save(map_path)

        # Reload the web view with the updated map
        self.web_view.setUrl(QUrl.fromLocalFile(map_path))

    def showPlot(self, station_id):
        station_eqs = self.tenvs[self.tenvs['Station ID'] == station_id]
        displacement_data = []

        # Calculate displacements for each unique event ID
        for event_id in station_eqs['Event ID'].dropna().unique():
            event_data = station_eqs[station_eqs['Event ID'] == event_id]

            if len(event_data) >= 2:
                event_data_sorted = event_data.sort_values('Date')
                day_before = event_data_sorted.iloc[0]
                day_after = event_data_sorted.iloc[-1]

                delta_e_displacement = abs(day_after['Delta E'] - day_before['Delta E'])
                delta_n_displacement = abs(day_after['Delta N'] - day_before['Delta N'])
                delta_v_displacement = abs(day_after['Delta V'] - day_before['Delta V'])

                displacement_data.append(
                    [day_after['Event Magnitude'], delta_e_displacement, delta_n_displacement, delta_v_displacement])

        if displacement_data:
            self.plot_displacement(displacement_data, station_id)

    def plot_displacement(self, displacement_data, station_id):
        displacement_df = pd.DataFrame(displacement_data, columns=['Magnitude', 'Delta E', 'Delta N', 'Delta V'])
        displacement_grouped = displacement_df.groupby('Magnitude').mean().reset_index()
        displacement_grouped[['Delta E', 'Delta N', 'Delta V']] = displacement_grouped[
            ['Delta E', 'Delta N', 'Delta V']].apply(lambda x: x / x.max())

        fig, ax = plt.subplots(figsize=(12, 6))
        bar_width = 0.2
        index = np.arange(len(displacement_grouped))

        ax.bar(index, displacement_grouped['Delta E'], bar_width, label='Delta E')
        ax.bar(index + bar_width, displacement_grouped['Delta N'], bar_width, label='Delta N')
        ax.bar(index + 2 * bar_width, displacement_grouped['Delta V'], bar_width, label='Delta V')

        ax.set_xlabel('Magnitude')
        ax.set_ylabel('Normalized Displacement')
        ax.set_title(f'Normalized Displacement by Magnitude for Station {station_id}')
        ax.set_xticks(index + bar_width)
        ax.set_xticklabels(displacement_grouped['Magnitude'].round(2))
        ax.legend()

        plt.show()

if __name__ == '__main__':
    parent_path = constants.PATHS.get(socket.gethostname(), '/default/path/to/data')
    app = QApplication(sys.argv)
    window = StationPlotApp(parent_path)
    window.show()
    sys.exit(app.exec_())