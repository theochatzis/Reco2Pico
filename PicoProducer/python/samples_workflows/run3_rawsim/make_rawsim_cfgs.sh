#!/bin/bash
# ---------------------------------------------------------------------------
# Build the cfgs of the Run-3 GEN-SIM-RAW -> Pico chain
#   step1  RAW2DIGI,L1Reco,RECO,RECOSIM  (the central Reco recipe of the campaign,
#          plus the sim-truth products kept by recoCustomise.keepSimTruth)
#   ntuple common/ntuples/reco-pico.sh    (RECO_to_pico_cfg.py with the full table set)
# and append rawsim_varparsing_tail.py to step1 (the ntuple cfg parses the
# same arguments itself).
#
# Usage:  make_rawsim_cfgs.sh [OUTDIR]          (default OUTDIR = <this dir>/cfgs)
#
# Environment overrides (defaults = Run3Winter26, CMSSW_15_0_X, 2026 realistic):
#   ERA      [Run3_2025]                      -> --era
#   GT       [150X_mcRun3_2026_realistic_v4]  -> --conditions (also passed to the ntuple step)
#   GEOM     [DB:Extended]                    -> --geometry
#   RECOSTEP [RAW2DIGI,L1Reco,RECO,RECOSIM]   -> --step
#   NTUPLE   [reco-pico]                      -> ntuple definition, see ../common/ntuples/
#   PICO_TABLES []                            -> table groups of the reco-pico ntuple (see its definition)
#   NEVT     [10]                             -> -n of the cmsDriver command (dummy)
#
# The defaults reproduce the McM request JME-Run3Winter26Reco-00027 (CMSSW_15_0_18):
#   cmsDriver.py --era Run3_2025 --step RAW2DIGI,L1Reco,RECO,RECOSIM --geometry DB:Extended
#     --conditions 150X_mcRun3_2026_realistic_v4 --datatier GEN-SIM-RECO --eventcontent RECOSIM --mc
# Check the Reco request of another sample on McM (public API:
#   https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get_setup/<PREPID>)
# and set ERA/GT accordingly.
# ---------------------------------------------------------------------------
set -euo pipefail
SW_LOG=make_rawsim_cfgs
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../common/chain_lib.sh"
sw_require_cmssw

OUTDIR="${1:-${SCRIPT_DIR}/cfgs}"
mkdir -p "${OUTDIR}"
OUTDIR="$(cd "${OUTDIR}" && pwd -P)"

export ERA="${ERA:-Run3_2025}"
export GT="${GT:-150X_mcRun3_2026_realistic_v4}"
GEOM="${GEOM:-DB:Extended}"
RECOSTEP="${RECOSTEP:-RAW2DIGI,L1Reco,RECO,RECOSIM}"
NTUPLE="${NTUPLE:-reco-pico}"
NEVT="${NEVT:-10}"

TAIL="${SCRIPT_DIR}/rawsim_varparsing_tail.py"
CUSTOMISE="Reco2Pico/PicoProducer/samples_workflows/run3_rawsim/recoCustomise.keepSimTruth"
[ -f "${TAIL}" ] || sw_die "VarParsing tail not found: ${TAIL}"
for f in "${SCRIPT_DIR}/../__init__.py" "${SCRIPT_DIR}/../common/__init__.py" "${SCRIPT_DIR}/__init__.py"; do
  [ -f "$f" ] || sw_die "missing package marker $f (needed so cmsDriver/cmsRun can import the tail and the customise)"
done

sw_load_ntuple "${NTUPLE}"

sw_log "CMSSW_BASE = ${CMSSW_BASE}"
sw_log "OUTDIR     = ${OUTDIR}"
sw_log "ERA=${ERA} GT=${GT} GEOM=${GEOM} STEP=${RECOSTEP} NTUPLE=${NTUPLE}"

cd "${OUTDIR}"

sw_run_driver step1 \
  --era "${ERA}" --conditions "${GT}" --geometry "${GEOM}" \
  --step "${RECOSTEP}" --eventcontent RECOSIM --datatier GEN-SIM-RECO \
  --customise "${CUSTOMISE}" \
  --mc --no_exec -n "${NEVT}" \
  --filein file:rawsim.root --fileout file:step1.root \
  --python_filename "${OUTDIR}/step1_RECO_cfg.py"

sw_make_ntuple_cfg "${OUTDIR}" file:step1.root -- --conditions "${GT}" --era "${ERA}" --mc --no_exec -n "${NEVT}"
sw_append_tail "${OUTDIR}/step1_RECO_cfg.py" "${TAIL}"
sw_log "done: step1_RECO_cfg.py $(sw_ntuple_cfg_name)  (ntuple args: ${NTUPLE_ARGS:-<none>})"
