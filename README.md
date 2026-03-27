# merge_anthroemis_hourlyNEI_globalCAMS

Generalized workflow to process hourly NEI anthropogenic emissions and merge them into global CAMS anthropogenic inventories, then prepare model-ready files on `ne0CONUSne30x8`.

## Process_NEI2022v2_mergewithCAMS

Goal: process all dates/hours for NEI 2022v2 and merge with CAMS-GLOB-ANT v6.2 over CONUS, following the ACP-paper methodology.

### Step 1: Preprocess NEI emissions

Process NEI2022v2 to regular `0.1° x 0.1°` CONUS grid using `epa_anthro_emis` preprocessor.

Reference from NEI2017 (T1 mechanism):

`/net/fs09/d0/taoma528/CESM22/CAMS_withCONUS2017NEI/2017NEI_01latlon`

One-day trial reference:

`ProcessThenCompare_NEI2017_vs_NEI2022v2_additionalspecies`

Mechanism decision: use `T1` to stay consistent with NEI2017 workflow.

### Step 2: Unit conversion and merge with CAMS

Convert NEI units to CAMS-compatible units and replace CAMS emissions over CONUS with NEI (hourly within ~80 km coastal buffer); keep CAMS monthly elsewhere.

Unit context:

- CAMS: `kg m-2 s-1`
- NEI: `mol km^-2 hr^-1`
- NEI particulate (BC, OC, PM10, PM25): `ug m^-2 s^-1`

### Step 3: Combine hourly files by species

Aggregate hourly Step-2 outputs to one file per species in CAM-chem-friendly format.

### Step 4: Regridding

Regrid Step-3 files to `ne0CONUSne30x8`.

### Step 5: Species mapping

Apply species mapping for CAM-chem mechanism consistency.

### Step 6: Zero Outside CONUS Mask

Create files where values outside CONUS 80 km buffer are set to zero while preserving coordinates and overall structure.

Script:

- `scripts/ops_singularity/zero_outside_conus_mask_c20260325.py`

Input path:

`/net/fs09/d0/taoma528/CESM22/CAMS6.2_withCONUS2022v2NEI/MappedSpecies_globCAMS_conusNEI_ne0CONUSne30x8/2023/`

Run:

```bash
python3 scripts/ops_singularity/zero_outside_conus_mask_c20260325.py --config config/paths.json
```

Output path (from config):

`paths.conus_zerooutside_temp_dir`

### Step 7: Fix Header/Format for Run Compatibility

Convert files to CAMS-compatible conventions used by existing model workflows (e.g., reorder dims, rename variable to `emiss`, convert time units/calendar, write CDF5).

Script:

- `scripts/ops_singularity/fix_header_to_cams_style.sh`

Run:

```bash
bash scripts/ops_singularity/fix_header_to_cams_style.sh config/paths.json
```

Expected output directory (from config):

`paths.conus_zerooutside_fixed_dir`

### Step 8: QA/Visualization Notebook

Notebook-based checks for structure, time handling, and map/point diagnostics.

Notebook:

- `notebooks/Check_CAMSvsNEI_Emissions.ipynb`

## Operational Notes (Derecho <-> Svante)

### Copy CAMS v6.2 from Derecho to Svante

On Derecho:

```bash
rsync -avz --progress -e ssh /glade/campaign/acom/acom-da/Global_Emissions/CAMS-GLOB-ANT_v6.2/* taoma528@svante9.mit.edu:/net/fs09/d0/taoma528/ncar_copies/acom/MUSICA/emissions/cams/CAMS-GLOB-ANT_v6.2/CAMS-GLOB-ANT_v6.2_orig/
```

### Copy 0.1-degree domain file to Derecho

```bash
rsync -avzL --exclude=".*" -e ssh "taoma528@svante9.mit.edu:/net/fs09/d0/taoma528/CESM22/CAMS_withCONUS2017NEI/2017NEI_01latlon/wrfinput_d01*" /glade/derecho/scratch/madankuit/NEI/EPA2022v2_CONUS/wrfchem_T1_MOZCART_hourly/
```

### Process one month at a time on Derecho

```bash
cd /glade/derecho/scratch/madankuit/NEI/EPA2022v2_CONUS/wrfchem_T1_MOZCART_hourly/
./anthro_emis < anthro_emis_T1_MOZCART_EPA2022_final.inp > anthro_emis.log 2>&1
```

Check mapping:

```bash
grep -i area anthro_emis.log
```

### Transfer processed hourly NEI files back to Svante

```bash
time rsync -avz --progress -e ssh /glade/derecho/scratch/madankuit/NEI/EPA2022v2_CONUS/wrfchem_T1_MOZCART_hourly/wrfchemi_d01_2022-12-* taoma528@svante9.mit.edu:/net/fs09/d0/taoma528/CESM22/CAMS_withCONUS2022v2NEI/NEI2022v2_T1_CONUS_output_01deg/
```

Archive month on Derecho:

```bash
mv /glade/derecho/scratch/madankuit/NEI/EPA2022v2_CONUS/wrfchem_T1_MOZCART_hourly/wrfchemi_d01_2022-12-* /glade/derecho/scratch/madankuit/NEI/EPA2022v2_CONUS/wrfchem_T1_MOZCART_hourly/hourly_files/
```

Estimated timing:

- Processing: ~2.5 hr/month
- Copying: ~3 hr/month

## Species/Inventory Comparison Notes

CAMS v5.1 vs v6.2 and NEI2017 vs NEI2022v2 comparison notes:

- Common species count: 29 (CAMS comparison)
- Only in v6.2: `chlorinated-hydrocarbons`, `co2_excl_short-cycle_org_C`, `co2_short-cycle_org_C`, `n2o`, `total-acids`, `total-ketones`
- Only in v5.1: `acids`, `chlorinated-HC`, `ketones`
- Common species count: 28 (NEI comparison)
- Only in NEI2022: `E_CH3COOH`, `E_HCHOOH`, `E_MGLY`, `E_MVK`
- Only in NEI2017: `E_ECI`, `E_ECJ`, `E_ORGI`, `E_SO4I`, `E_SO4J`

## Scripts and Exact Output Paths

### Step 2 merge (0.1 degree)

Script:

- `ModifiedFor2023_Merge_conusNEI2022v2_01degCAMS6.2_v2.py` (source workflow)
- repo equivalent: `scripts/01_merge_nei_into_cams.py`

Output path (intermediate hourly; may be removed after Step 3):

`/net/fs09/d0/taoma528/CESM22/CAMS6.2_withCONUS2022v2NEI/globCAMS_conusNEI_01deg/2023_hourly/`

Processing time estimate: ~6 hr/month for all species.

### Step 3 combine by species

Script:

- `combine_hourly_globCAMS_conusNEI2022_to_species_01deg_v20260303.py` (source workflow)
- repo equivalent: `scripts/03_combine_hourly_species_yearly.py`

Output path:

`/net/fs09/d0/taoma528/CESM22/CAMS6.2_withCONUS2022v2NEI/globCAMS_conusNEI_01deg/2023_GroupBySpecies/`

### Step 4 regrid to ne0CONUSne30x8

Script:

- `Regrid_Emissions_ne0CONUSne30x8.py` (source workflow)
- repo equivalent: `scripts/04_regrid_to_ne0conusne30x8.py`

Output path:

`/net/fs09/d0/taoma528/CESM22/CAMS6.2_withCONUS2022v2NEI/globCAMS_conusNEI_ne0CONUSne30x8/2023_CAMSSpecies/`

### Step 5 species mapping

Script:

- `Species_Mapping_NEI2022v2_CAMSv6.2_ne0CONUSne30x8.ipynb`
- mapping file in this repo: `config/species_mapping_template.dat`

Output path:

`/net/fs09/d0/taoma528/CESM22/CAMS6.2_withCONUS2022v2NEI/MappedSpecies_globCAMS_conusNEI_ne0CONUSne30x8/2023/`

## Config and Code Design

All runtime paths are centralized in one config file loaded by one shared module:

- Config: `config/paths.json` (local/private; gitignored)
- Loader: `src/nei_merge/settings.py`

Scripts (`scripts/01-04`) import settings from that single module.

Operational post-processing scripts captured from Svante are kept under:

- `scripts/ops_singularity/`
- `notebooks/`

Operational scripts are also config-driven and do not require hardcoded paths in script bodies.

## Quick Start (repo scripts)

```bash
cp config/paths.example.json config/paths.json
python3 scripts/01_merge_nei_into_cams.py --config config/paths.json
python3 scripts/02_fix_time_coords.py --config config/paths.json
python3 scripts/03_combine_hourly_species_yearly.py --config config/paths.json
python3 scripts/04_regrid_to_ne0conusne30x8.py --config config/paths.json
# then run scripts/ops_singularity/* and notebooks/* in the Singularity workflow
```
