#!/bin/bash
#SBATCH --job-name=nei_cams_merge
#SBATCH --output=nei_cams_merge.%j.out
#SBATCH --error=nei_cams_merge.%j.err
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --time=4-00:00:00

set -euo pipefail

echo "Host: $(hostname)"
echo "Start: $(date -Is)"

PYTHON_BIN=${PYTHON_BIN:-python}
CONFIG_JSON=${CONFIG_JSON:-config/paths.json}

$PYTHON_BIN -c "import sys,platform; print('python:', sys.executable); print('glibc:', platform.libc_ver())"

cd "$(dirname "$0")/.."
$PYTHON_BIN scripts/01_merge_nei_into_cams.py --config "$CONFIG_JSON"
