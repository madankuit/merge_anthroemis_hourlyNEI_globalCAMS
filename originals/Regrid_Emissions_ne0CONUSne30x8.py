"""
Created by Madankui Tao on Feb. 24, 2026 

Purpose
-------
Re-grid the combined hourly merged CAMS + CONUS NEI 2022v2 emission files
(globCAMS_conusNEI2022) from one 0.1° × 0.1° global NetCDF file to ne0CONUSne30x8
per original CAMS species.

Conda Environment: rootxesmf

Input
-----
- Hourly merged files by species:
    globCAMS_conusNEI2022_01deg_YYYY-MM-DD_HH:MM:SS.nc
- Grid files

Output
------
- One NetCDF file per species
- Dimensions: (ncol, lat, lon)

The issue is that the regridding function cannot get the time correct and I added the 'Fix time coordinate' step

"""
#=====Input features that can be changed======
#--------------------------------------------------------------------------
# specify the start and end datetime
# if other than 2022 (actual NEI year), means already adjusted by week of a day
DateOfModify = 'c20260224'

startDatetime = '2023-01-01T00:00:00'
endDatetime = '2023-12-30T23:00:00'

# after merging, get to files group by each CAMS original species
CAMS_merged01_bySpecies_diri = '/net/fs09/d0/taoma528/CESM22/CAMS6.2_withCONUS2022v2NEI/globCAMS_conusNEI_01deg/2023_GroupBySpecies/'
mergedne0CONUSne30x8_diri = '/net/fs09/d0/taoma528/CESM22/CAMS6.2_withCONUS2022v2NEI/globCAMS_conusNEI_ne0CONUSne30x8/2023_CAMSSpecies/'

### Providing all files needed to regrid
# Grid information file
CAMS_grid_file = '/net/fs09/d0/taoma528/CESM22/grids/FV_gridinfo_CAMS_c20210219.nc'
# SE-RR grid file
SERR_scrip_file = '/net/fs09/d0/taoma528/CESM22/grids/ne0CONUS_ne30x8_np4_SCRIP.nc'
# Weights file
Regridding_weights_file = '/net/fs09/d0/taoma528/CESM22/grids/ESMFmap_0.1x0.1_ne0CONUSne30x8_cubit_conserve_cams.nc'

#=====Dependent library & functions======
#--------------------------------------------------------------------------

import os
import glob
import fnmatch

import numpy as np # for array manipulation and basic scientific calculation
import xarray as xr # To read NetCDF files
# import cartopy.crs as ccrs # For map projection
# import seaborn as sns # boxplot
import pandas as pd

import warnings
# Ignore a specific warning
warnings.filterwarnings('ignore', message='Some warning message')

### Module import ###
import esmpy as ESMF
from mpi4py import MPI
print("ESMF:", ESMF.__version__)
print("MPI:", MPI.Get_version())

# from the module
# get the packages downloaded from NCAR cheyenne: /glade/u/home/cdswk/python/lib/my_packages/
import sys
sys.path.insert(0,'/home/taoma528/Scripts/CESM_analysis/ACP_MUSICANEI_scripts/anthroemis_MergeNEI2017_to_CAMS/NCAR_packages/')
from dsj.array.chk import chk
from dsj.time.expand_date import Expand_date
from dsj.analysis.Regridding_ESMF import Add_bounds, Regridding
from dsj.io.get_sp import get_sp

###------additional defined functions
import os
import re
from typing import Iterable, Dict, List, Tuple
def get_spc_and_spcfiles(file_list: Iterable[str]) -> Tuple[List[str], Dict[str, str]]:
    """
    Parse species names from merged CAMS+NEI per-species filenames and return
    (1) a sorted list of unique species and (2) a dict mapping species -> file path.

    Expected (new) filename pattern (basename):
        Y<YYYY>CAMS-GLOB-ANTv6.2_conusNEI2022v2_01deg_<SPC>_c<YYYYMMDD>.nc

    Notes:
      - If multiple files map to the same species, the most recently modified
        file is kept (helps if reruns produced duplicates).
      - Works with any iterable of paths (list, np.array, generator).
    """
    # capture the species as the token before "_cYYYYMMDD.nc"
    # e.g., ..._01deg_acetylene_c20260224.nc -> "acetylene"
    pat = re.compile(r"_01deg_(?P<spc>.+?)_c\d{8}\.nc$")

    spc_to_file: Dict[str, str] = {}
    for fp in file_list:
        bn = os.path.basename(fp)
        m = pat.search(bn)
        if not m:
            # skip anything that doesn't match the new convention
            continue

        spc = m.group("spc")

        # if duplicates exist, keep the newest by mtime
        if spc in spc_to_file:
            try:
                if os.path.getmtime(fp) > os.path.getmtime(spc_to_file[spc]):
                    spc_to_file[spc] = fp
            except OSError:
                # if stat fails, just keep the existing one
                pass
        else:
            spc_to_file[spc] = fp

    spc_list = sorted(spc_to_file.keys())
    return spc_list, spc_to_file

#=====Dependent library & functions======
#--------------------------------------------------------------------------
# Marged CAMS+NEI emissions dir with specified date of modification
# Merged emissions dir
file_dir = CAMS_merged01_bySpecies_diri
# Search for files that match the pattern
pattern = 'Y2023_CAMS-GLOB-ANTv6.2_conusNEI2022v2_01deg_*'+DateOfModify+'*'
file_list = [file for file in glob.glob(os.path.join(file_dir, pattern)) if fnmatch.fnmatch(os.path.basename(file), pattern)]

# Destination filename format that regridded field will be saved
# "SPC" will be replaced to the real species name from CAMS species
# !!! Use the 'raw_' dir in case need to modify
dst_file_format = f'{mergedne0CONUSne30x8_diri}Y2023_CAMS-GLOB-ANTv6.2_conusNEI2022v2_ne0CONUSne30x8_SPC_'+DateOfModify+'.nc'

# SE-RR grid file
SERR_scrip_file = '/net/fs09/d0/taoma528/CESM22/grids/ne0CONUS_ne30x8_np4_SCRIP.nc'

# This will create a list of species names and a dictionary matching species name with 
species, species_files = get_spc_and_spcfiles(file_list)
print(species)

# uncomment below if you just want to process some species, not all the species in the emission directory
# CAMS species: 'acetylene', 'acids', 'alcohols', 'bc', 'benzene', 'butanes', 'chlorinated-HC',
# 'co', 'esters', 'ethane', 'ethene', 'ethers', 'formaldehyde', 'hexanes', 
# 'isoprene', 'ketones', 'monoterpenes', 'nh3', 'nmvocs', 'nox', 'oc', 
# 'other-aldehydes', 'other-alkenes-and-alkynes', 'other-aromatics', 'other-vocs',
# 'pentanes', 'propane', 'propene', 'so2', 'toluene','trimethylbenzene', 'xylene', 
# species = species[22:]
species = ["nox",]

# Remaining: "monoterpenes","nox",


# uncomment below if you want to process only some fields/sectors of the file
#sectors = ['sum']
# uncomment below if you want to process all the fields/sectors in the file
sectors = []

#--------------------------------------------------------------------------
for sp1 in species:
    dst_file = dst_file_format.replace( 'SPC', sp1 )
    # check if this species has already been processed
    if os.path.exists(dst_file):
        # pass
        print(f"{sp1} already processed.")
    else:
        # continue
        print( 'Regridding: ', sp1)
        print( '************************************************************************' )
        ds_emis = xr.open_dataset( species_files[sp1] )  

        rr = Regridding( ds_emis, src_grid_file=CAMS_grid_file, dst_grid_file=SERR_scrip_file, 
                         wgt_file=Regridding_weights_file, method='Conserve', fields=sectors,
                         dst_file=dst_file, save_wgt_file=False, save_results=True, check_results=False, 
                         check_timings=True, creation_date=False, nc_file_format='NETCDF4' )

        # ------------------------------------------------------------
        # Fix time coordinate in the regridded output to match ds_emis
        # ------------------------------------------------------------
        src_time = np.array(ds_emis["time"].values, dtype="datetime64[ns]")

        ds_out = xr.open_dataset(dst_file)

        if "time" not in ds_out.dims:
            raise ValueError(f"[{sp1}] dst_file has no 'time' dimension. Found dims: {ds_out.dims}")

        if ds_out.sizes["time"] != len(src_time):
            raise ValueError(
                f"[{sp1}] time length mismatch: dst={ds_out.sizes['time']} vs src={len(src_time)}"
            )

        # overwrite time coord
        ds_out = ds_out.assign_coords(time=("time", src_time))

        # (optional) minimal provenance
        ds_out.attrs["time_fix_note"] = "Replaced output time coordinate to match ds_emis.time (hourly)."

        # overwrite safely
        tmp = dst_file + ".tmp"
        ds_out.to_netcdf(tmp)
        ds_out.close()
        ds_emis.close()

        os.replace(tmp, dst_file)
        print(f"[{sp1}] time fixed and overwrote: {dst_file}")