# This function is used to modify the date for a different year than the NEI emissions file
# Created by Madankui Tao on Feb. 21, 2026 [modified based on ModifiedFor2018_LoopAllSpeci_MultipleTimes_MergeNEI2017_01degCAMS_v3.py]

# Input: Hourly mean NEI filename (in the format of '')
# Output: NEI filename for the target year

#=====Dependent library & functions======
#--------------------------------------------------------------------------
import os
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from datetime import datetime
def extract_date_and_time(filename):
    # Extract the date and time part of the filename
    date_time_str = filename[13:]
    # Convert the date and time string to a datetime object (without seconds)
    date_time_obj = datetime.strptime(date_time_str, '%Y-%m-%d_%H:%M:%S')
    return date_time_obj
# # Sort the list based on date and time using the custom key function
# sorted_filenames = sorted(filenames, key=extract_date_and_time)

#=====The function======
#--------------------------------------------------------------------------
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

def NEIfileDatetime_shift_BYweekofday(inpNEIfile, outyear):
    """
    Adjusts the date in a NEI file to match the same day in a week in the specified output year.

    Parameters:
        inpNEIfile (str): The NEI file with the input datetime in the format 'wrfchemi_d01_YYYY-MM-DD_HH:MM:SS'.
        outyear (int): The target output year for the adjusted datetime.

    Returns:
        str: The adjusted NEI filename for the specified output year in the format 'wrfchemi_d01_YYYY-MM-DD_HH:MM:SS'.
    """
    # Takes NEI file for the input datetime
    inp_date_time_obj = datetime.strptime(inpNEIfile[13:], '%Y-%m-%d_%H:%M:%S')

    # get the years between input and output
    nyears = outyear - inp_date_time_obj.year

    # find the date in the target year
    outp_date_time_obj = inp_date_time_obj + relativedelta(years=nyears)

    # adjusted for week in a day
    delta_days = outp_date_time_obj - inp_date_time_obj

    # Calculate the number of weeks to shift the weekday
    num_weeks_shift = delta_days.days // 7

    # Calculate the number of remaining days after removing whole weeks
    remaining_days = delta_days.days % 7

    # then will shift the date by 'remaining_days' to match the same day in a week
    adjt_outp_date_time_obj = outp_date_time_obj + timedelta(days=-remaining_days)

    # Format the datetime object to get the full weekday names of the original and adjusted dates
    original_weekday = inp_date_time_obj.strftime('%A')
    adjusted_weekday = adjt_outp_date_time_obj.strftime('%A')

    # Print the day of the week of the original and adjusted dates for verification
    print(f"{original_weekday} matched with {adjusted_weekday}")

    # return the NEI filename after adjustment
    outpNEIfile = 'wrfchemi_d01_' + adjt_outp_date_time_obj.strftime('%Y-%m-%d_%H:%M:%S')

    return outpNEIfile

# #=====Example to use this function======
# #--------------------------------------------------------------------------
# inpNEIfile = 'wrfchemi_d01_2017-08-01_01:00:00'
# outyear = 2020

# outpNEIfile = NEIfileDatetime_shift_BYweekofday(inpNEIfile, outyear)

# #=====Function to locate the 2017 NEI filename given the desired output date======
# #--------------------------------------------------------------------------

from datetime import datetime, timedelta

def NEIfileDatetime_shift_BACKWARD(outpNEIfile_datetime, NEIactualyear):
    """
    Map an output datetime (in any year) back to the corresponding NEI file datetime
    in NEIactualyear, adjusting within +/- 6 days to match the same weekday.

    Parameters
    ----------
    outpNEIfile_datetime : str
        Target datetime string in format 'YYYY-MM-DD_HH:MM:SS' (the year here is outyear).
    NEIactualyear : int
        The year of the actual NEI files (e.g., 2017 or 2022).

    Returns
    -------
    str
        Datetime string in NEIactualyear in format 'YYYY-MM-DD_HH:MM:SS', weekday-matched.
    """

    out_dt = datetime.strptime(outpNEIfile_datetime, "%Y-%m-%d_%H:%M:%S")

    # Step 1: replace the year to get the "same month/day/time" in NEIactualyear
    # (handles leap-day safely by falling back to Feb 28 if needed)
    try:
        inp_dt = out_dt.replace(year=NEIactualyear)
    except ValueError:
        # only likely issue is Feb 29 -> non-leap year
        inp_dt = out_dt.replace(year=NEIactualyear, day=28)

    # Step 2: weekday-match by shifting 0–6 days forward
    # weekday(): Mon=0 ... Sun=6
    delta = (out_dt.weekday() - inp_dt.weekday()) % 7
    inp_dt_adj = inp_dt + timedelta(days=delta)

    # optional print for verification
    print(f"{out_dt.strftime('%A')} matched with {inp_dt_adj.strftime('%A')} (shift +{delta} days)")

    return inp_dt_adj.strftime("%Y-%m-%d_%H:%M:%S")

### sample use: 
#NEIfileDatetime_shift_BACKWARD("2023-07-15_13:00:00", NEIactualyear=2022)

### Verification code
# test_out = [
#     "2023-01-01_00:00:00",
#     "2023-03-15_12:00:00",
#     "2023-07-04_18:00:00",
#     "2023-12-31_23:00:00",
# ]

# NEIactualyear = 2022

# for s in test_out:
#     back = NEIfileDatetime_shift_BACKWARD(s, NEIactualyear)
#     print(f"{s}  ->  {back}")
