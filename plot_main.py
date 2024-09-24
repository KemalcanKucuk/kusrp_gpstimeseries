import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
import os
import constants
import socket
from obspy.imaging.beachball import beachball
import argparse

# Get hostname to dynamically select paths (adjust based on your environment)
hostname = socket.gethostname()
parent_path = constants.PATHS.get(hostname, '/default/path/to/data')

# Function to plot distance vs displacement for multiple events with controlled fitting methods
def plot_distance_vs_displacement(csv_file_path, event_ids, fit_type='attenuation'):
    try:
        # Load the preprocessed CSV with necessary columns
        combined_df = pd.read_csv(csv_file_path, delimiter=';', decimal=',')

        # Set up a single plot for polynomial fits if selected
        plt.figure(figsize=(10, 6))

        # Loop over each event ID provided
        for event_id in event_ids:
            # Filter for the specific event ID
            event_data = combined_df[combined_df['Event ID'] == event_id]

            if event_data.empty:
                print(f"No data found for Event ID: {event_id}")
                continue

            # Ensure valid values for the plot (drop rows with NaN in required columns)
            valid_data = event_data.dropna(subset=['Distance from Epicenter', 'Displacement'])

            if valid_data.empty:
                print(f"No valid data for plotting distance vs displacement for Event ID: {event_id}")
                continue

            # Extract event magnitude for the legend
            magnitude = valid_data['Magnitude'].iloc[0]

            # Handle different fit types
            if fit_type == 'attenuation':
                # Log-transform Distance and Displacement for linear regression
                log_distance = np.log(valid_data['Distance from Epicenter'].values)
                log_displacement = np.log(valid_data['Displacement'].values)

                # Fit a linear regression model to log-transformed data
                model = LinearRegression()
                model.fit(log_distance.reshape(-1, 1), log_displacement)

                # Get the attenuation exponent n and log(A)
                n = -model.coef_[0]  # The slope of the line is -n
                log_A = model.intercept_  # The intercept gives log(A)
                A = np.exp(log_A)  # Convert log(A) back to A

                # Generate predicted displacements using the fitted n and A
                X_range = np.linspace(valid_data['Distance from Epicenter'].min(), valid_data['Distance from Epicenter'].max(), 500)
                y_pred = A * (X_range ** -n)

                # Plot the fitted attenuation curve
                plt.plot(X_range, y_pred, label=f"Attenuation Fit (M={magnitude}): Displacement = {A:.8f} * Distance^{{-{n:.8f}}}", linewidth=2)

            elif fit_type == 'polynomial':
                # Polynomial Regression (2nd degree)
                X = valid_data['Distance from Epicenter'].values.reshape(-1, 1)
                y = valid_data['Displacement'].values.reshape(-1, 1)

                # Apply 2nd-degree polynomial features to X
                poly = PolynomialFeatures(degree=2)
                X_poly = poly.fit_transform(X)

                # Fit the polynomial regression model
                poly_model = LinearRegression()
                poly_model.fit(X_poly, y)

                # Predict the displacement using the polynomial regression model
                X_range = np.linspace(X.min(), X.max(), 500).reshape(-1, 1)  # Smooth line for better visualization
                X_poly_range = poly.transform(X_range)
                y_poly_pred = poly_model.predict(X_poly_range)

                # Get the polynomial coefficients for displaying the equation
                coef = poly_model.coef_[0]
                intercept = poly_model.intercept_[0]
                poly_formula = f"{coef[2]:.8f}x^2 + {coef[1]:.8f}x + {intercept:.8f}"

                # Plot the polynomial regression curve for this event
                plt.plot(X_range, y_poly_pred, label=f"Polynomial Fit (M={magnitude}): {poly_formula}", linewidth=2)

            # Also plot the original scatter data for this event
            plt.scatter(valid_data['Distance from Epicenter'], valid_data['Displacement'], label=f"Event {event_id} Data (M={magnitude})")

        # Add labels and title
        plt.xlabel('Distance from Epicenter (km)')
        plt.ylabel('Displacement (m)')
        plt.title(f'Distance vs Displacement with {fit_type.capitalize()} Fit')
        plt.legend()

        # Show the plot with all the fits on top of each other
        plt.show()

    except Exception as e:
        print(f"Error generating plot: {e}")

if __name__ == "__main__":
    # Use argparse to handle command-line arguments
    parser = argparse.ArgumentParser(description="Plot Distance vs Displacement with specified fit type (attenuation or polynomial) for multiple events.")
    parser.add_argument("event_ids", nargs='+', type=str, help="A list of Event IDs to plot")
    parser.add_argument("fit_type", choices=['attenuation', 'polynomial'], help="The type of fit to apply: 'attenuation' or 'polynomial'")
    
    # Parse the arguments
    args = parser.parse_args()

    # Update the CSV file path to the actual file
    csv_file_path = os.path.join(parent_path, 'merged_displacement_data_with_api.csv')
c
    # Call the plot function with the parsed arguments
    plot_distance_vs_displacement(csv_file_path, args.event_ids, args.fit_type)
