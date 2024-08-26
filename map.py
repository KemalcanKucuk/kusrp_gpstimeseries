import sys
import folium
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, QPushButton, QLabel, QFormLayout
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl
import preprocessing as pr
import constants
import socket

class StationPlotApp(QMainWindow):
    def __init__(self, parent_path):
        super().__init__()

        self.setWindowTitle("Station Plot App")
        self.setGeometry(100, 100, 1600, 900)  # Set window size

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Use a horizontal layout for the main layout
        self.main_layout = QHBoxLayout(self.central_widget)

        self.parent_path = parent_path
        self.pre = pr.Preprocessor(parent_path)

        self.create_map()
        self.create_controls()

    def create_map(self):
        # Create map widget and add to layout
        self.map_layout = QVBoxLayout()
        self.map = folium.Map(location=[0, 0], zoom_start=2)

        # Save the map to an HTML file in the current directory
        current_dir = os.path.dirname(os.path.abspath(__file__))  # Get the current file directory
        map_path = os.path.join(current_dir, 'map.html')
        self.map.save(map_path)

        self.web_view = QWebEngineView()
        self.web_view.setUrl(QUrl.fromLocalFile(map_path))
        self.map_layout.addWidget(self.web_view)

        # Add the map layout to the main layout, taking up most of the space
        self.main_layout.addLayout(self.map_layout, stretch=4)  # Larger stretch for map

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
        self.main_layout.addWidget(controls_container, stretch=1)  # Smaller stretch for controls

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

        # Filter stations by station IDs present in main_df (tenvs)
        station_ids_in_main_df = self.tenvs['Station ID'].unique()
        filtered_stations = filtered_stations[filtered_stations['Station ID'].isin(station_ids_in_main_df)]

        # Re-create the map with filtered stations
        self.map = folium.Map(location=[0, 0], zoom_start=2)
        for index, row in filtered_stations.iterrows():
            folium.Marker(
                location=[row['Lat'], row['Long']],
                popup=row['Station ID'],
                icon=folium.Icon(color='red', icon='info-sign')
            ).add_to(self.map)

        # Save the updated map and reload it in the web view
        current_dir = os.path.dirname(os.path.abspath(__file__))
        map_path = os.path.join(current_dir, 'map.html')
        self.map.save(map_path)
        self.web_view.setUrl(QUrl.fromLocalFile(map_path))

if __name__ == '__main__':
    parent_path = constants.PATHS.get(socket.gethostname(), '/default/path/to/data')
    app = QApplication(sys.argv)
    window = StationPlotApp(parent_path)
    window.show()
    sys.exit(app.exec_())