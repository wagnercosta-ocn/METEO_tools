'''
This code extracts time series data from NetCDF files (model outputs) and a text file (buoy data), comparing them, calculating bias and RMSE, and visualizing the results.
'''
import xarray as xr
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d

# Define placeholder paths for your files
# Please replace these with your actual file paths
NETCDF_FILE_1 = 'app_exp1_all.nc' # e.g., 'model_output_wave_height_1.nc'
NETCDF_FILE_2 = 'app_exp2_all.nc' # e.g., 'model_output_wave_height_2.nc'
BUOY_DATA_FILE = 'mooring_buoys/all_buoy_data_cleaned2' # e.g., 'all_buoys_data.txt'

# Define the target buoy's coordinates
# Please replace these with the actual latitude and longitude of your buoy
TARGET_BUOY_LAT = 43.53 # Example latitude
TARGET_BUOY_LON = -1.614 # Example longitude

# ==========================================================================================
# Load the first NetCDF file
# ==========================================================================================

try:
    ds_1 = xr.open_dataset(NETCDF_FILE_1)
    print(f"Successfully opened: {NETCDF_FILE_1}")
except FileNotFoundError:
    print(f"Error: File not found at {NETCDF_FILE_1}. Please check the path.")
    ds_1 = None

if ds_1:
    # Display dimensions
    print("\nDimensions:")
    for dim_name, dim_len in ds_1.dims.items():
        print(f"  {dim_name}: {dim_len}")

    # Display variables and their attributes
    print("\nVariables:")
    for var_name, var in ds_1.variables.items():
        # Check if it's a data variable (not just a coordinate) and has shape (exclude scalar coords if any)
        if var_name not in ds_1.coords and len(var.shape) > 0:
            units = getattr(var, 'units', '')
            print(f"  {var_name}: {var.shape} {var.dtype} {units}")
    print("\nDataset structure (ds_1):")
    display(ds_1)

# --- USER INPUT REQUIRED --- 
# Replace these with the actual variable and coordinate names from your NetCDF file 1
MODEL_VAR_NAME_1 = 'example_wave_height_variable'  # e.g., 'hs' or 'significant_wave_height'
MODEL_TIME_COORD_1 = 'time' # e.g., 'time' or 't_dim'
MODEL_LAT_COORD_1 = 'lat'   # e.g., 'lat' or 'latitude'
MODEL_LON_COORD_1 = 'lon'   # e.g., 'lon' or 'longitude'

if 'ds_1' in locals() and ds_1 is not None:
    # Use .sel with 'method=nearest' for spatial selection
    model_point_1 = ds_1.sel(
        {MODEL_LAT_COORD_1: TARGET_BUOY_LAT, MODEL_LON_COORD_1: TARGET_BUOY_LON},
        method='nearest'
    )

    # Extract the time series for the specified variable and convert to Pandas Series
    model_series_1 = model_point_1[MODEL_VAR_NAME_1].to_series()

    # Get the actual coordinates of the nearest point for printing
    nearest_lat_1 = model_point_1[MODEL_LAT_COORD_1].item()
    nearest_lon_1 = model_point_1[MODEL_LON_COORD_1].item()

    print(f"\nExtracted time series for {MODEL_VAR_NAME_1} from Model 1 at nearest grid point: ({nearest_lat_1:.2f}, {nearest_lon_1:.2f})")
    display(model_series_1.head())
    display(model_series_1.tail())
    print(f"Number of data points for Model 1: {len(model_series_1)}")
    # Ensure the index is datetime for calculating resolution (xarray usually handles this)
    model_series_1.index = pd.to_datetime(model_series_1.index)
    print(f"Time resolution for Model 1: {pd.Series(model_series_1.index).diff().mode().dt.total_seconds().iloc[0] / 3600:.2f} hours")

    ds_1.close() # Close the xarray dataset
else:
    print("Skipping NetCDF Model 1 data extraction due to file error.")
# ==========================================================================================
# Load the second NetCDF file
# ==========================================================================================
try:
    ds_2 = xr.open_dataset(NETCDF_FILE_2)
    print(f"Successfully opened: {NETCDF_FILE_2}")
except FileNotFoundError:
    print(f"Error: File not found at {NETCDF_FILE_2}. Please check the path.")
    ds_2 = None

if ds_2:
    # Display dimensions
    print("\nDimensions:")
    for dim_name, dim_len in ds_2.dims.items():
        print(f"  {dim_name}: {dim_len}")

    # Display variables and their attributes
    print("\nVariables:")
    for var_name, var in ds_2.variables.items():
        # Check if it's a data variable (not just a coordinate) and has shape
        if var_name not in ds_2.coords and len(var.shape) > 0:
            units = getattr(var, 'units', '')
            print(f"  {var_name}: {var.shape} {var.dtype} {units}")
    print("\nDataset structure (ds_2):")
    display(ds_2)
    
# --- USER INPUT REQUIRED --- 
# Replace these with the actual variable and coordinate names from your NetCDF file 2
try:
    ds_2 = xr.open_dataset(NETCDF_FILE_2)
    print(f"Successfully opened: {NETCDF_FILE_2}")
except FileNotFoundError:
    print(f"Error: File not found at {NETCDF_FILE_2}. Please check the path.")
    ds_2 = None

if ds_2:
    # Display dimensions
    print("\nDimensions:")
    for dim_name, dim_len in ds_2.dims.items():
        print(f"  {dim_name}: {dim_len}")

    # Display variables and their attributes
    print("\nVariables:")
    for var_name, var in ds_2.variables.items():
        # Check if it's a data variable (not just a coordinate) and has shape
        if var_name not in ds_2.coords and len(var.shape) > 0:
            units = getattr(var, 'units', '')
            print(f"  {var_name}: {var.shape} {var.dtype} {units}")
    print("\nDataset structure (ds_2):")
    display(ds_2)
# ==========================================================================================
# Load the buoy data file
# ==========================================================================================

try:
    # --- USER INPUT REQUIRED ---
    # Adjust 'sep' (separator) and 'header' based on your text file format
    # For example: sep='\s+' for space-separated, sep=',' for comma-separated
    buoy_df = pd.read_csv(BUOY_DATA_FILE, sep='\s+', header=0)
    print(f"Successfully loaded: {BUOY_DATA_FILE}")
except FileNotFoundError:
    print(f"Error: Buoy data file not found at {BUOY_DATA_FILE}. Please check the path.")
    buoy_df = None

if buoy_df is not None:
    print("\nBuoy Data Head:")
    display(buoy_df.head())
    print("\nBuoy Data Info:")
    buoy_df.info()
else:
    print("Skipping buoy data loading due to file error.")

if buoy_df is not None:
    buoy_df.columns=['Date','lat','lon','swh','tp','flg']
    # --- USER INPUT REQUIRED --- 
    # Replace these with the actual column names from your buoy data file
    BUOY_TIME_COL = 'Date'     # e.g., 'Date_Time'
    BUOY_LAT_COL = 'lat'       # e.g., 'Latitude'
    BUOY_LON_COL = 'lon'       # e.g., 'Longitude'
    BUOY_VAR_COL = 'swh'  # e.g., 'Hs' or 'Wave_Height'

    # Convert time column to datetime objects
    # Adjust the format if necessary (e.g., format='%Y-%m-%d %H:%M:%S')
    buoy_df[BUOY_TIME_COL] = pd.to_datetime(buoy_df[BUOY_TIME_COL],format='%Y%m%d%H%M%S')

    # Find the row(s) corresponding to the target buoy's coordinates
    # We'll use a small tolerance for floating point comparisons
    tolerance_lat = 0.01 # Adjust as needed
    tolerance_lon = 0.01 # Adjust as needed

    target_buoy_data = buoy_df[
        (np.abs(buoy_df[BUOY_LAT_COL] - TARGET_BUOY_LAT) < tolerance_lat) &
        (np.abs(buoy_df[BUOY_LON_COL] - TARGET_BUOY_LON) < tolerance_lon)
    ]

    if not target_buoy_data.empty:
        # Create a Pandas Series for easier handling
        buoy_series = pd.Series(target_buoy_data[BUOY_VAR_COL].values, index=target_buoy_data[BUOY_TIME_COL])

        print(f"\nExtracted time series for target buoy at ({TARGET_BUOY_LAT}, {TARGET_BUOY_LON})")
        display(buoy_series.head())
        display(buoy_series.tail())
        print(f"Number of data points for Buoy: {len(buoy_series)}")
        print(f"Time resolution for Buoy: {pd.Series(buoy_series.index).diff().mode().dt.total_seconds().iloc[0] / 3600:.2f} hours")

    else:
        print(f"No data found for buoy at ({TARGET_BUOY_LAT}, {TARGET_BUOY_LON}) within specified tolerance.")
        buoy_series = None
else:
    print("Skipping buoy data extraction due to previous file error.")

  # ==========================================================================================
  ### 5. Resample and Align Time Series
  # ==========================================================================================
if 'model_series_1' in locals() and 'model_series_2' in locals() and 'buoy_series' in locals() and buoy_series is not None:
    # Ensure all series have datetime indices and are sorted
    model_series_1 = model_series_1.sort_index()
    model_series_2 = model_series_2.sort_index()
    buoy_series = buoy_series.sort_index()

    # Determine the common time range
    start_time = max(model_series_1.index.min(), model_series_2.index.min(), buoy_series.index.min())
    end_time = min(model_series_1.index.max(), model_series_2.index.max(), buoy_series.index.max())

    # Filter buoy series to the common time range
    buoy_series_aligned = buoy_series.loc[start_time:end_time]

    if not buoy_series_aligned.empty:
        # Interpolate Model 1 to buoy's timestamps
        # Convert datetime to numerical (seconds since epoch) for interpolation
        model_time_numeric_1 = model_series_1.index.astype(np.int64) // 10**9
        buoy_time_numeric_aligned = buoy_series_aligned.index.astype(np.int64) // 10**9

        f_interp_1 = interp1d(model_time_numeric_1, model_series_1.values, kind='linear', fill_value="extrapolate")
        model_series_1_interp = pd.Series(f_interp_1(buoy_time_numeric_aligned), index=buoy_series_aligned.index)

        # Interpolate Model 2 to buoy's timestamps
        model_time_numeric_2 = model_series_2.index.astype(np.int64) // 10**9
        f_interp_2 = interp1d(model_time_numeric_2, model_series_2.values, kind='linear', fill_value="extrapolate")
        model_series_2_interp = pd.Series(f_interp_2(buoy_time_numeric_aligned), index=buoy_series_aligned.index)

        print(f"\nCommon time range for comparison: {start_time} to {end_time}")
        print("\nAligned Buoy Series (head):")
        display(buoy_series_aligned.head())
        print("\nInterpolated Model 1 Series (head):")
        display(model_series_1_interp.head())
        print("\nInterpolated Model 2 Series (head):")
        display(model_series_2_interp.head())
    else:
        print("No overlapping time range found between buoy and models after filtering.")
        model_series_1_interp = None
        model_series_2_interp = None
        buoy_series_aligned = None
else:
    print("Skipping time series alignment due to missing data.")
# ==========================================================================================
### 6. Calculate Bias and RMSE  
# ==========================================================================================

if 'model_series_1_interp' in locals() and model_series_1_interp is not None and\
   'model_series_2_interp' in locals() and model_series_2_interp is not None and\
   'buoy_series_aligned' in locals() and buoy_series_aligned is not None:

    def calculate_metrics(model_data, buoy_data):
        bias = np.mean(model_data - buoy_data)
        rmse = np.sqrt(np.mean((model_data - buoy_data)**2))
        return bias, rmse

    # Calculate metrics for Model 1
    bias_1, rmse_1 = calculate_metrics(model_series_1_interp, buoy_series_aligned)
    print(f"\nModel 1 vs Buoy: Bias = {bias_1:.3f}, RMSE = {rmse_1:.3f}")

    # Calculate metrics for Model 2
    bias_2, rmse_2 = calculate_metrics(model_series_2_interp, buoy_series_aligned)
    print(f"Model 2 vs Buoy: Bias = {bias_2:.3f}, RMSE = {rmse_2:.3f}")
else:
    print("Skipping bias and RMSE calculation due to missing aligned data.")

# ==========================================================================================
### 7. Plot Time Series with Bias and RMSE
# ==========================================================================================
if 'model_series_1_interp' in locals() and model_series_1_interp is not None and\
   'model_series_2_interp' in locals() and model_series_2_interp is not None and\
   'buoy_series_aligned' in locals() and buoy_series_aligned is not None:

    # Set figure size for a scientific poster
    plt.figure(figsize=(18, 10)) # Adjust as needed

    # Plot Buoy Data
    plt.plot(buoy_series_aligned.index, buoy_series_aligned.values, label='Buoy Observations', color='black', linewidth=2, marker='o', markersize=4, linestyle='-')

    # Plot Model 1 Data
    plt.plot(model_series_1_interp.index, model_series_1_interp.values, label=f'Model 1 (Bias: {bias_1:.2f}, RMSE: {rmse_1:.2f})', color='red', linewidth=1.5, linestyle='--')

    # Plot Model 2 Data
    plt.plot(model_series_2_interp.index, model_series_2_interp.values, label=f'Model 2 (Bias: {bias_2:.2f}, RMSE: {rmse_2:.2f})', color='blue', linewidth=1.5, linestyle=':')

    # Set title and labels
    plt.title('Comparison of Model Outputs and Buoy Observations', fontsize=20, fontweight='bold')
    plt.xlabel('Time', fontsize=16)
    plt.ylabel(f'{MODEL_VAR_NAME_1} (Units)', fontsize=16) # Replace 'Units' with actual units

    # Set tick parameters and font sizes
    plt.xticks(fontsize=14, rotation=45, ha='right')
    plt.yticks(fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(fontsize=14, loc='upper left')
    plt.tight_layout() # Adjust layout to prevent labels from being cut off
    plt.show()

    print("\nPlot generated successfully. Remember to replace 'Units' in the y-label with the actual units of your variable.")
else:
    print("Skipping plotting due to missing aligned or calculated data.")
