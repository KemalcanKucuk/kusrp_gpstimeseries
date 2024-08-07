import sys
import socket
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QListWidget, QScrollArea, QLabel, QFormLayout
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import preprocessing as pr
import tenv_utils
import constants


class StationPlotApp(QMainWindow):
    def __init__(self, parent_path):
        super().__init__()

        self.setWindowTitle("Station Plot App")
        self.setGeometry(100, 100, 1200, 900)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Use a horizontal layout for the main layout
        self.main_layout = QHBoxLayout(self.central_widget)

        self.parent_path = parent_path
        self.pre = pr.Preprocessor(parent_path)

        self.filtered_tenvs_list = []

        self.create_plot()
        self.create_controls()

    def create_plot(self):
        self.fig = Figure(figsize=(10, 9), dpi=100)
        self.axs = [self.fig.add_subplot(311), self.fig.add_subplot(
            312), self.fig.add_subplot(313)]
        self.canvas = FigureCanvas(self.fig)
        self.main_layout.addWidget(self.canvas)

    def create_controls(self):
        control_layout = QVBoxLayout()

        self.load_percentage_input = QLineEdit()
        self.load_percentage_input.setPlaceholderText("5")
        control_layout.addWidget(QLabel("Load Percentage"))
        control_layout.addWidget(self.load_percentage_input)

        self.magnitude_threshold_input = QLineEdit()
        self.magnitude_threshold_input.setPlaceholderText(
            "Enter magnitude threshold")
        control_layout.addWidget(QLabel("Magnitude Threshold"))
        control_layout.addWidget(self.magnitude_threshold_input)

        self.earthquake_count_input = QLineEdit()
        self.earthquake_count_input.setPlaceholderText(
            "Enter earthquake count")
        control_layout.addWidget(QLabel("Earthquake Count"))
        control_layout.addWidget(self.earthquake_count_input)

        # Station list
        self.station_list_widget = QListWidget()
        self.station_list_widget.currentItemChanged.connect(
            self.on_station_select)

        scroll_area = QScrollArea()
        scroll_area.setWidget(self.station_list_widget)
        scroll_area.setWidgetResizable(True)
        control_layout.addWidget(scroll_area)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search Station")
        control_layout.addWidget(self.search_bar)

        search_button = QPushButton("Search")
        search_button.clicked.connect(self.submit_search)
        control_layout.addWidget(search_button)

        self.load_plot_button = QPushButton("Load and Plot")
        self.load_plot_button.clicked.connect(self.load_data)
        control_layout.addWidget(self.load_plot_button)

        self.info_label = QLabel(
            "Load and filter data to see the details here.")
        control_layout.addWidget(self.info_label)

        self.main_layout.addLayout(control_layout)

    def load_data(self):
        load_percentage = int(self.load_percentage_input.text() or 5)
        magnitude_threshold = float(self.magnitude_threshold_input.text(
        )) if self.magnitude_threshold_input.text() else None
        earthquake_count = int(self.earthquake_count_input.text(
        )) if self.earthquake_count_input.text() else None

        # Load and filter the data
        self.tenvs = self.pre.load_combined_df(load_percentage=load_percentage,
                                               target_magnitude=magnitude_threshold,
                                               eq_count=earthquake_count)

        self.filtered_tenvs_list = tenv_utils.split_combined_df_to_list(
            self.tenvs)
        self.index = 0

        # Update the station list
        self.station_list_widget.clear()
        for df in self.filtered_tenvs_list:
            station_id = df['Station ID'].iloc[0]
            num_eqs = df['Event ID'].nunique(
            ) if 'Event ID' in df.columns else 0
            self.station_list_widget.addItem(f"{station_id} - {num_eqs} EQs")

        self.info_label.setText(
            f"Loaded {len(self.filtered_tenvs_list)} stations.")

        # Initially clear the plot
        for ax in self.axs:
            ax.clear()
        self.canvas.draw()

        # Plot the first station's data if available
        if self.filtered_tenvs_list:
            self.plot_tenv_data(self.filtered_tenvs_list[0], self.filtered_tenvs_list[0]['Station ID'].iloc[0])

    def plot_tenv_data(self, tenv_df, station_name):
        for ax in self.axs:
            ax.clear()

        # Plot Delta E
        self.axs[0].scatter(tenv_df['Date'], tenv_df['Delta E'],
                            label='Delta E', c='blue', s=10)
        self.axs[0].set_title(f'{station_name} Delta E', fontsize=10, pad=15)
        self.axs[0].set_ylabel('Delta E')
        self.axs[0].legend()
        self.axs[0].grid(True)

        # Plot Delta N
        self.axs[1].scatter(tenv_df['Date'], tenv_df['Delta N'],
                            label='Delta N', c='green', s=10)
        self.axs[1].set_title(f'{station_name} Delta N', fontsize=10, pad=15)
        self.axs[1].set_ylabel('Delta N')
        self.axs[1].legend()
        self.axs[1].grid(True)

        # Plot Delta V
        self.axs[2].scatter(tenv_df['Date'], tenv_df['Delta V'],
                            label='Delta V', c='red', s=10)
        self.axs[2].set_title(f'{station_name} Delta V', fontsize=10, pad=15)
        self.axs[2].set_xlabel('Date')
        self.axs[2].set_ylabel('Delta V')
        self.axs[2].legend()
        self.axs[2].grid(True)

        # Filter earthquake events for the current station
        station_events = tenv_df[tenv_df['Event Magnitude'].notna()]

        # Plot earthquake events on each axis if they exist
        if not station_events.empty:
            for ax in self.axs:
                for _, event in station_events.iterrows():
                    ax.axvline(event['Date'], color='purple',
                               linestyle='--', label='Earthquake Event')

        self.fig.tight_layout()
        self.canvas.draw()

    def submit_search(self):
        station_name = self.search_bar.text().strip().upper()
        for i, df in enumerate(self.filtered_tenvs_list):
            if df['Station ID'].iloc[0] == station_name:
                self.index = i
                self.plot_tenv_data(
                    self.filtered_tenvs_list[self.index], station_name)
                self.station_list_widget.setCurrentRow(self.index)
                return
        print(f"Station {station_name} not found")

    def on_station_select(self, current, previous):
        if current:
            station_name = current.text().split(" - ")[0]
            self.index = self.station_list_widget.currentRow()
            self.plot_tenv_data(
                self.filtered_tenvs_list[self.index], station_name)


if __name__ == '__main__':
    hostname = socket.gethostname()
    parent_path = constants.PATHS.get(hostname, '/default/path/to/data')
    app = QApplication(sys.argv)
    window = StationPlotApp(parent_path)
    window.show()
    sys.exit(app.exec_())