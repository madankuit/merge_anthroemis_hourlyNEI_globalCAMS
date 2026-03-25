"""
Functions to identify missing hourly emissions or chemistry files within a specified datetime range.

This script generates the expected hourly filenames between two timestamps
and checks whether each file exists in the target directory. It returns
both the list of expected files and any missing files.

Designed for use in atmospheric chemistry and emissions workflows
(e.g., WRF-Chem, CAMS, MUSICA processing).

Author
------
Madankui Tao
Created: 2026-02
"""

from datetime import datetime, timedelta

def find_missing_files_v1(startDatetime, endDatetime, filedir, file_prefix):
    """
    Find missing files between two given datetime strings. time in '%Y-%m-%d_%H:%M:%S'

    Parameters:
        startDatetime (str): Start datetime in the format 'YYYY-MM-DD_HH:MM:SS'.
        endDatetime (str): End datetime in the format 'YYYY-MM-DD_HH:MM:SS'.
        filedir (str): the directory where the files are located.
        file_prefix (str): Prefix used in the file names.

    Returns:
        list: List of missing file names.

    Example:
        startDatetime = '2018-07-01_03:00:00'
        endDatetime = '2018-07-03_00:00:00'
        file_prefix = 'wrfchemi_d01'
        missing_files = find_missing_files_v1(startDatetime, endDatetime, file_prefix)
        print(missing_files)  # Print the missing files.
    """

    # Convert startDatetime and endDatetime strings to datetime objects
    start_date = datetime.strptime(startDatetime, '%Y-%m-%d_%H:%M:%S')
    end_date = datetime.strptime(endDatetime, '%Y-%m-%d_%H:%M:%S')

    # Create a list of expected file names between start and end dates
    current_date = start_date
    expected_files = []
    while current_date <= end_date:
        file_name = file_prefix + current_date.strftime('_%Y-%m-%d_%H:00:00')
        expected_files.append(filedir+file_name)
        current_date += timedelta(hours=1)

    # Check if each file exists, and store the missing files in a list
    missing_files = []
    for file_path in expected_files:
        try:
            # Check if the file exists
            with open(file_path, 'r'):
                pass
        except FileNotFoundError:
            missing_files.append(file_path)

    #-----------
    # Print the missing files
    if len(missing_files)!=0:
        print("Missing files:")
        for file_name in missing_files:
            print(file_name)
    else:
        print("No missing files found.")
            
    return {'missing_files':missing_files,'expected_files':expected_files}

# # Example usage
# startDatetime = '2017-07-01_03:00:00'
# endDatetime = '2017-07-03_00:00:00'
# filedir = '/net/fs09/d0/taoma528/CESM22/CAMS_withCONUS2017NEI/NEI2017_CONUS_output_01deg/'
# file_prefix = 'wrfchemi_d01'
# missing_files = find_missing_files_v1(startDatetime, endDatetime, filedir,file_prefix)

# # Print the missing files
# if missing_files:
#     print("Missing files:")
#     for file_name in missing_files:
#         print(file_name)
# else:
#     print("No missing files found.")

### version two for different datetime 
def find_missing_files_v2(startDatetime, endDatetime, filedir, file_prefix, file_sufix):
    """
    Find missing files between two given datetime strings.

    Parameters:
        startDatetime (str): Start datetime in the format 'YYYY-MM-DDTHH:MM:SS'.
        endDatetime (str): End datetime in the format 'YYYY-MM-DD_HH:MM:SS'.
        filedir (str): the directory where the files are located.
        file_prefix (str): Prefix used in the file names.

    Returns:
        list: List of missing file names.

    Example:
        startDatetime = '2018-07-01T00:00:00'
        endDatetime = '2018-07-02T00:00:00'
        file_prefix = 'CAMS-GLOB-ANT_v5.1_'+CAMSorigName+'_MergedNEI2017WDKadjusted'
        missing_files = find_missing_files_v2(startDatetime, endDatetime, file_prefix)
        print(missing_files)  # Print the missing files.
    """

    # Convert startDatetime and endDatetime strings to datetime objects
    start_date = datetime.strptime(startDatetime, '%Y-%m-%dT%H:%M:%S')
    end_date = datetime.strptime(endDatetime, '%Y-%m-%dT%H:%M:%S')

    # Create a list of expected file names between start and end dates
    current_date = start_date
    expected_files = []
    while current_date <= end_date:
        file_name = file_prefix + current_date.strftime('_%Y-%m-%dT%H:00:00') + file_sufix
        expected_files.append(filedir+file_name)
        current_date += timedelta(hours=1)

    # Check if each file exists, and store the missing files in a list
    missing_files = []
    for file_path in expected_files:
        try:
            # Check if the file exists
            with open(file_path, 'r'):
                pass
        except FileNotFoundError:
            missing_files.append(file_path)

    #-----------
    # Print the missing files
    if len(missing_files)!=0:
        print("Missing files:")
        for file_name in missing_files:
            print(file_name)
    else:
        print("No missing files found.")
            
    return {'missing_files':missing_files,'expected_files':expected_files}