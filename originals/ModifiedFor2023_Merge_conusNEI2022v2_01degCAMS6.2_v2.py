# This script is used to integrate NEI 2022v2 emissions into CAMS-GLOB-ANT6.2
# Created by Madankui Tao on Feb. 22, 2026 based on previous workflow for NEI2017

# Input: Hourly mean NEI 2022v2 and Monthly mean CAMS-GLOB-ANT6.2 in approximately 0.1 by 0.1 degree
# Output: Merged hourly mean global data centered on even 0.1 by 0.1 degree FOR ADJUSTED YEAR!

# Tried a much faster way to replace the CONUS with NEI emissions
# 1. Precompute the CAMS→NEI index mapping once (no more “closest search” inside nested loops).
# 2. Replace values with vectorized assignment using either a 80km buffered shapefile mask.
# 3. Note that the time is incorrect as it only has the 00 as the CAMS file! 

#=====Input features that can be changed======
#--------------------------------------------------------------------------
# specify the start and end datetime
# if other than 2022, means adjusted by week of a day
# need to be in the same year for processing

# The year I merge to
startDatetime = '2023-01-21_00:00:00'
endDatetime = '2023-02-02_23:00:00'

# startDatetime = '2023-01-30_00:00:00'
# endDatetime = '2023-01-31_23:00:00'

# the actual year for NEI data
NEIactualyear = 2022

outyear = int(startDatetime[:4])

### find the corresponding NEI species name mapped to CAMS orig ###
# 'sum_' means summing the following species | based on MergeNEI2022v2_to_CAMS.ipynb
CMASOrig_toNEI_dic = {'acetylene':'E_C2H2', 
                      'alcohols':'sum_E_CH3OH_E_C2H5OH', # sum of E_CH3OH and E_C2H5OH in NEI
                      'bc':'E_BC', 
                      'benzene':'E_BENZENE', 
                      # 'chlorinated-HC', # ignore; we do not use in MOZART species
                      'co':'E_CO', 
                      'ethane':'E_C2H6', 
                      'ethene':'E_C2H4', 
                      'formaldehyde':'E_CH2O', 
                      'isoprene':'E_ISOP', 
                      'total-ketones':'sum_E_CH3COCH3_E_MEK',  # sum of E_CH3COCH3 and E_MEK in NEI
                      'monoterpenes':'E_APIN',  # use APIN
                      'nh3':'E_NH3', 
                      # 'nmvocs', # ignore
                      'nox':'sum_E_NO_NO2', # sum of NO and NO2
                      'oc':'E_OC', #organic carbon
                      # 'other-aldehydes':'E_CH3CHO', v6.2 does not have aldehydes
                      'other-alkenes-and-alkynes':'E_BIGENE', 
                      # 'other-vocs', # ignore
                      'propane':'E_C3H8', 
                      'propene':'E_C3H6', 
                      'so2':'E_SO2', 
                      'toluene':'E_TOLUENE',
                      'xylene':'E_XYLENE',
                       }

#=====Dependent library & functions======
#--------------------------------------------------------------------------
import os
import glob

import numpy as np # for array manipulation and basic scientific calculation
import xarray as xr # To read NetCDF files
import pandas as pd

from datetime import datetime

#--------------------------------------------------------------------------
# Unit Conversion (to CAMS standard)
def convert_molkm_2hr_1_TO_kgm_2s_1(vals_molkm_2hr_1, MV):
    """
    Convert emissions unit from mol km^-2 hr^-1 to kg m^-2 s^-1
    Parameters:
        vals_molkm_2hr_1 (array-like): Emissions data in mol km^-2 hr^-1
        MV (float): Molecular weight of the species in g/mol
    Returns:
        vals_kgm_2s_1 (array-like): Emissions data in kg m^-2 s^-1
    """
    # Ensure vals_molkm_2hr_1 is an array before applying element-wise calculation
    vals_molkm_2hr_1 = np.array(vals_molkm_2hr_1)
    
    MV_kg_ml = MV * 1e-3
    vals_kgm_2s_1 = vals_molkm_2hr_1 * (1 / (60 * 60)) * (1 / 1e6) * MV_kg_ml
    
    return vals_kgm_2s_1

# Unit Conversion (to CAMS standard)
def convert_ugm_2s_1_TO_kgm_2s_1(vals_ugm_2s_1):
    """
    Convert concentrations from micrograms per square meter per second (μg/m^2/s) to kilograms per square meter per second (kg/m^2/s).
    
    Parameters:
        vals_ugm_2s_1 (numpy.ndarray): Concentration values in micrograms per square meter per second.
        
    Returns:
        numpy.ndarray: Concentration values converted to kilograms per square meter per second.
    """
    vals_kgm_2s_1 = vals_ugm_2s_1 * 1e-9
    return vals_kgm_2s_1

def find_closest_value_2Darray(array, value):
    """
    Find the value and index of the closest value to 'value' in a 2-D array.
    Parameters:
        array (numpy array): The 2-D array to search
        value: The value to find the closest match for
    Returns:
        closest_value: The value in the array closest to 'value'
        closest_index: The index of the closest value in the array
    """
    array = np.asarray(array)
    flattened_array = array.flatten()
    idx = (np.abs(flattened_array - value)).argmin()
    closest_value = flattened_array[idx]
    closest_index = np.unravel_index(idx, array.shape)
    return closest_value, closest_index

# used to sort files
def extract_date_and_time(filename):
    """
    Extract the date and time part of the filename and convert to a datetime object.
    Parameters:
        filename (str): The file name in the format 'wrfchemi_d01_YYYY-MM-DD_HH:MM:SS'
    Returns:
        date_time_obj (datetime): The datetime object extracted from the filename
    """
    date_time_str = filename[13:]
    date_time_obj = datetime.strptime(date_time_str, '%Y-%m-%d_%H:%M:%S')
    return date_time_obj

# function written to adjust the date
from NEIfileDatetime_shift_BYweekofday import *

#--------------------------------------------------------------------------
# --- Load mapping ---
map_path = "/net/fs09/d0/taoma528/CESM22/GeographicMasks/CAMSgrid_to_NEIgrid_CONUSlower48_80kmBuffer_map.npz"
m = np.load(map_path, allow_pickle=True)

cams_ii = m["cams_ii"]
cams_jj = m["cams_jj"]
nei_sn  = m["nei_sn"]
nei_we  = m["nei_we"]
dist    = m["dist_deg"]

# Optional distance cutoff (prevents odd snapping near edges/offshore)
dist_cutoff_deg = 0.125
dist_ok = (dist <= dist_cutoff_deg)

#--------------------------------------------------------------------------
# Function to read in NEI files within the given datetimes
def read_nei_files(start_datetime, end_datetime, NEIactualyear, outyear):
    # Find the corresponding NEI files to read in
    NEIfile_startDatetime = NEIfileDatetime_shift_BACKWARD(start_datetime, NEIactualyear)
    NEIfile_endDatetime = NEIfileDatetime_shift_BACKWARD(end_datetime, NEIactualyear)

    start_dt = datetime.strptime(NEIfile_startDatetime, '%Y-%m-%d_%H:%M:%S')
    end_dt = datetime.strptime(NEIfile_endDatetime, '%Y-%m-%d_%H:%M:%S')

    # Get all file names in the directory
    NEIonCONUS_diri = '/net/fs09/d0/taoma528/CESM22/CAMS6.2_withCONUS2022v2NEI/NEI2022v2_T1_CONUS_output_01deg/'
    file_names = os.listdir(NEIonCONUS_diri)

    # Filter the file names based on the date range
    selected_file_names = []

    for file_name in file_names:
        file_date = datetime.strptime(file_name[13:], '%Y-%m-%d_%H:%M:%S')
        if start_dt <= file_date <= end_dt:
            selected_file_names.append(file_name)

    # Re-organize in ascending date then time
    sorted_file_list = sorted(selected_file_names, key=extract_date_and_time)

    print('%i files within the given timeframe' % len(selected_file_names))
    return sorted_file_list

#--------------------------------------------------------------------------
# Read the NEI files corresponding within the given datetimes
# Approx 0.1 by 0.1 centered processed NEI emissions on CONUS grid
# Function to process NEI and merge with CAMS-GLOB
def process_nei_and_merge(CAMSorigName, NEIfilei, outyear):
    # Find the CAMS monthly mean file for SpeciesX
    search_str = f'_{CAMSorigName}_' # add dash to make sure selecting the correct species
    CAMS_orig_diri = '/net/fs09/d0/taoma528/ncar_copies/acom/MUSICA/emissions/cams/CAMS-GLOB-ANT_v6.2/CAMS-GLOB-ANT_v6.2_orig/'
    CAMS_orig_list = glob.glob(os.path.join(CAMS_orig_diri, f'*{search_str}*'))
    CAMSGLOB_SpeciesX_orig_file = CAMS_orig_list[0]

    # Shift the NEI file to match the given year needed
    outpNEIfile = NEIfileDatetime_shift_BYweekofday(NEIfilei, outyear)

    # Convert to datetime64 object with correct format
    datetime_str = outpNEIfile[-19:]
    formatted_datetime_stri = np.datetime64(datetime_str[:10] + 'T' + datetime_str[11:] + '.000000000')

    # Get the given month from the NEI file
    GivenMonth = outpNEIfile[13:20]
    
    # Output to .nc file: filename
    Outpt_diri = '/net/fs09/d0/taoma528/CESM22/CAMS6.2_withCONUS2022v2NEI/globCAMS_conusNEI_01deg/' + str(outyear) + '_hourly_timeFixed/'
    if os.path.exists(Outpt_diri):
        pass
        # print(f"Directory already exists: {Outpt_diri}")
    else:
        os.makedirs(Outpt_diri, exist_ok=True)
        print(f"Directory created: {Outpt_diri}")
    # Add MergedNEI2022 and datetime at the end of the original filename
    filename_orig = os.path.basename(CAMSGLOB_SpeciesX_orig_file)
    filename_without_extension, extension = os.path.splitext(filename_orig)
    FILEOUT_name = filename_without_extension + '_conusNEI2022v2WDKadjusted_' + str(formatted_datetime_stri)[:19] + extension
    FILEOUT_path = Outpt_diri + FILEOUT_name
    
    # if the file already existed
    if os.path.exists(FILEOUT_path):
        print(f"Skipping processing for {CAMSorigName} and {NEIfilei} as the output file already exists.")
    else:
        # Process each CAMS and NEI combination
        print(f"Start processing for {CAMSorigName} and {NEIfilei}.")

        # Read in the data for the given month from CAMS-GLOB
        CAMSGLOB_SpeciesXds = xr.open_dataset(CAMSGLOB_SpeciesX_orig_file)
        # Convert the time dimension to pandas DateTimeIndex
        time_index = pd.DatetimeIndex(CAMSGLOB_SpeciesXds['time'].values)
        # Use boolean indexing to select data for the desired time range
        monthi_CAMSGLOBds = CAMSGLOB_SpeciesXds.sel(time=time_index.strftime('%Y-%m') == GivenMonth)

        # Read in NEI (this is still 2022v2 data)
        NEIonCONUS_diri = '/net/fs09/d0/taoma528/CESM22/CAMS6.2_withCONUS2022v2NEI/NEI2022v2_T1_CONUS_output_01deg/'
        datei_houri_NEIds = xr.open_dataset(NEIonCONUS_diri + NEIfilei)
        XLAT = datei_houri_NEIds.XLAT
        XLONG = datei_houri_NEIds.XLONG

        # Extract the NEI emissions name based on the CAMS original name
        NEI_Name = CMASOrig_toNEI_dic[CAMSorigName]
        input_list = NEI_Name.split('_')

        # Handle single species and multiple species separately
        if input_list[0] != 'sum':
            # Single Species
            speci_datei_houri_NEIda = datei_houri_NEIds[CMASOrig_toNEI_dic[CAMSorigName]]
        elif input_list[0] == 'sum':
            # Multiple Species
            species_list = [item for item in input_list if item not in ['sum', 'E']]
            var1 = 'E_' + species_list[0]
            var2 = 'E_' + species_list[1]

            # Sum the two variables and assign the result to a new variable named 'summed'
            summed_data = datei_houri_NEIds[var1] + datei_houri_NEIds[var2]
            # Create a new DataArray for the summed variable with the same attributes and dimensions as 'var1'
            summed_da = xr.DataArray(summed_data, coords=datei_houri_NEIds[var1].coords, attrs=datei_houri_NEIds[var1].attrs)
            # Add the new variable to the dataset
            datei_houri_NEIds['sum'] = summed_da
            # Change the description
            datei_houri_NEIds['sum'].attrs['description'] = f'NEI Emissions summed for {var1} and {var2}'

            # Use the sum for species i
            speci_datei_houri_NEIda = datei_houri_NEIds['sum']

        # Unit conversion
        origUnit = speci_datei_houri_NEIda.units # check the original unit
        
        MV = int(monthi_CAMSGLOBds['sum'].molecular_weight)
        
        # Convert the unit and copy the attributes
        # all to kgm_2s_1
        if origUnit=='ug m^-2 s^-1':
            UnitChecked_speci_datei_houri_NEI_vals = convert_ugm_2s_1_TO_kgm_2s_1(speci_datei_houri_NEIda.values)
        elif origUnit=='mol km^-2 hr^-1':
            UnitChecked_speci_datei_houri_NEI_vals = convert_molkm_2hr_1_TO_kgm_2s_1(speci_datei_houri_NEIda.values, MV)
        else:
            print(f'Stop! Check the unit [{origUnit}] of NEI species')
        
        UnitChecked_speci_datei_houri_NEIda = xr.DataArray(data=UnitChecked_speci_datei_houri_NEI_vals,
                                                           dims=speci_datei_houri_NEIda.dims,
                                                           coords=speci_datei_houri_NEIda.coords,
                                                           attrs=speci_datei_houri_NEIda.attrs.copy())

        # Add the variable name from speci_datei_houri_NEIda
        UnitChecked_speci_datei_houri_NEIda.name = speci_datei_houri_NEIda.name
        # add across stack heights
        timei_NEIda = UnitChecked_speci_datei_houri_NEIda.sum(dim='emissions_zdim_stag')
        # Update the 'units' attribute
        timei_NEIda.attrs['units'] = 'kg m-2 s-1'

        # Merge the data within CONUS
        #--------------------------------------
        # --- Prepare NEI 2D (first timestep), already unit-converted ---
        time_dim = "Time" if "Time" in timei_NEIda.dims else "time"

        nei_da = timei_NEIda.isel({time_dim: 0})
        if "emissions_zdim_stag" in nei_da.dims:
            nei2d = nei_da.sum("emissions_zdim_stag").values
        else:
            nei2d = nei_da.values

        nei_on_cams = nei2d[nei_sn, nei_we]
        replace_ok = (nei_on_cams > 1e-21) & dist_ok

        # --- 3) Start from FULL CAMS dataset copy (preserves everything) ---
        copied_ds = monthi_CAMSGLOBds.copy(deep=True)

        # Replace in-place (keeps variable structure/attrs/encoding intact)
        copied_ds["sum"].values[0, cams_ii[replace_ok], cams_jj[replace_ok]] = nei_on_cams[replace_ok]

        # --- 4) Add ONE-LINE provenance (minimal difference) ---
        copied_ds.attrs["NEI_merge_note"] = (
            "Merged: replaced CAMS-GLOB-ANT 'sum' inside buffered CONUS (80 km) with NEI emissions "
            f"(nearest-neighbor map: {map_path}; criteria: dist<={dist_cutoff_deg} deg)."
        )

        # --- 5) Parse time from filename string 
        # Make sure it’s a scalar datetime64[ns]
        t = np.datetime64(str(formatted_datetime_stri).replace(".000000000",""))
        copied_ds = copied_ds.assign_coords(time=("time", np.array([t], dtype="datetime64[ns]")))
        # (or copied_ds["time"] = xr.DataArray([t], dims="time") also works)

        # Save out the merged product
        # Modify the 'long_name' attribute
        long_name = copied_ds['sum'].attrs['long_name']
        new_long_name = long_name + ' (merged Y2023 global CAMSv6.2 with conus NEI 2022v2 and shifted to match weekday/weekend)'
        copied_ds['sum'].attrs['long_name'] = new_long_name

        copied_ds.to_netcdf(FILEOUT_path)
        print('Save successfuly and output to: ', FILEOUT_path)
            

# Loop through all species names and files
sorted_file_list = read_nei_files(startDatetime, endDatetime, NEIactualyear, outyear)
# print(sorted_file_list)

## Process each species in order 
# for CAMSorigName in CMASOrig_toNEI_dic.keys():
#     # Loop through the NEI emissions file
#     for NEIfilei in sorted_file_list:
#         # Process each CAMS and NEI combination
#         process_nei_and_merge(CAMSorigName, NEIfilei, outyear)
        
## loop through files first, prioritize processing for species that miss the dates listed 
for NEIfilei in sorted_file_list:
    for CAMSorigName in CMASOrig_toNEI_dic.keys():
        # Process each CAMS and NEI combination
        process_nei_and_merge(CAMSorigName, NEIfilei, outyear)

# print(CMASOrig_toNEI_dic.keys())
