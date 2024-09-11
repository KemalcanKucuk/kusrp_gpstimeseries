import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import os
import constants
import socket

# Get hostname to dynamically select paths (adjust based on your environment)
hostname = socket.gethostname()
parent_path = constants.PATHS.get(hostname, '/default/path/to/data')

# Function to convert strike, dip, and rake into 3D plane vertices and slip vector
def fault_plane_vertices_with_rake_3d(strike, dip, rake, width=1, height=1):
    """
    Convert strike, dip, and rake into 3D plane vertices and slip direction vector.
    :param strike: Strike angle in degrees
    :param dip: Dip angle in degrees
    :param rake: Rake angle in degrees
    :param width: Width of the plane
    :param height: Height (dip) of the plane
    :return: Coordinates for the vertices of the fault plane and slip direction vector
    """
    # Convert angles from degrees to radians
    strike_rad = np.radians(strike)
    dip_rad = np.radians(dip)
    rake_rad = np.radians(rake)

    # Calculate the direction of the strike
    x_dir = np.cos(strike_rad)
    y_dir = np.sin(strike_rad)

    # Vertices of the plane (quadrilateral) in 3D
    bl_x, bl_y, bl_z = 0, 0, 0  # Bottom-left corner
    br_x, br_y, br_z = width * x_dir, width * y_dir, 0  # Bottom-right corner

    # Top-right (accounting for dip)
    tr_x = br_x
    tr_y = br_y
    tr_z = -height * np.sin(dip_rad)

    # Top-left (accounting for dip)
    tl_x = bl_x
    tl_y = bl_y
    tl_z = -height * np.sin(dip_rad)

    # Calculate the slip direction using the rake
    slip_x = np.cos(rake_rad) * x_dir - np.sin(rake_rad) * y_dir * np.cos(dip_rad)
    slip_y = np.cos(rake_rad) * y_dir + np.sin(rake_rad) * x_dir * np.cos(dip_rad)
    slip_z = np.sin(rake_rad) * np.sin(dip_rad)

    # Return vertices as a list of coordinates and the slip vector
    vertices = [(bl_x, bl_y, bl_z), (br_x, br_y, br_z), (tr_x, tr_y, tr_z), (tl_x, tl_y, tl_z)]
    return vertices, (slip_x, slip_y, slip_z)

# Function to plot Plane 1 and Plane 2 in 3D as surfaces, with rake showing slip direction
def plot_fault_planes_3d_with_rake(strike1, dip1, rake1, strike2, dip2, rake2, event_id):
    """
    Plot Plane 1 and Plane 2 in 3D based on their strike, dip, and rake, as 3D planes with slip direction.
    """
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    # Get vertices and slip direction for Plane 1
    vertices1, slip_vector1 = fault_plane_vertices_with_rake_3d(strike1, dip1, rake1)
    # Get vertices and slip direction for Plane 2
    vertices2, slip_vector2 = fault_plane_vertices_with_rake_3d(strike2, dip2, rake2)

    # Create a Poly3DCollection for Plane 1
    plane1 = Poly3DCollection([vertices1], color='r', alpha=0.5, label="Plane 1")
    # Create a Poly3DCollection for Plane 2
    plane2 = Poly3DCollection([vertices2], color='g', alpha=0.5, label="Plane 2")

    # Add the planes to the plot
    ax.add_collection3d(plane1)
    ax.add_collection3d(plane2)

    # Plot the slip vector for Plane 1 (using rake)
    ax.quiver(0, 0, 0, slip_vector1[0], slip_vector1[1], slip_vector1[2], color='b', label="Slip 1")
    # Plot the slip vector for Plane 2 (using rake)
    ax.quiver(0, 0, 0, slip_vector2[0], slip_vector2[1], slip_vector2[2], color='y', label="Slip 2")

    # Set the plot limits and labels
    ax.set_xlim([-1.5, 1.5])
    ax.set_ylim([-1.5, 1.5])
    ax.set_zlim([-1.5, 1.5])
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')

    # Set the title with the event ID
    ax.set_title(f"3D Fault Planes with Slip Direction for Event {event_id}")

    # Add a legend
    ax.legend()

    # Enable rotation
    plt.show()

# Function to plot the fault planes for multiple events from the CSV file
def plot_fault_planes_from_csv_with_rake_3d(csv_file_path, event_ids):
    # Load the CSV data
    combined_df = pd.read_csv(csv_file_path, delimiter=';', decimal=',')

    # Loop through each event ID
    for event_id in event_ids:
        # Filter for the specific event
        event_data = combined_df[combined_df['Event ID'] == event_id]

        if event_data.empty:
            print(f"No data found for Event ID: {event_id}")
            continue

        # Extract strike, dip, and rake for Plane 1 and Plane 2 from the event data
        strike1 = event_data['Nodal Plane 1 Strike'].iloc[0]
        dip1 = event_data['Nodal Plane 1 Dip'].iloc[0]
        rake1 = event_data['Nodal Plane 1 Rake'].iloc[0]

        strike2 = event_data['Nodal Plane 2 Strike'].iloc[0]
        dip2 = event_data['Nodal Plane 2 Dip'].iloc[0]
        rake2 = event_data['Nodal Plane 2 Rake'].iloc[0]

        # Plot the fault planes with slip direction in 3D for the current event
        plot_fault_planes_3d_with_rake(strike1, dip1, rake1, strike2, dip2, rake2, event_id)

# Example usage
if __name__ == "__main__":
    # Update the CSV file path to the actual file
    csv_file_path = os.path.join(parent_path, 'merged_displacement_data_with_api.csv')

    # List of event IDs to plot (use actual Event IDs from your dataset)
    event_ids = ['usp000by66', 'usp000fn3d']  # Example event IDs

    # Plot the fault planes with slip direction for the selected events from the CSV in 3D
    plot_fault_planes_from_csv_with_rake_3d(csv_file_path, event_ids)
