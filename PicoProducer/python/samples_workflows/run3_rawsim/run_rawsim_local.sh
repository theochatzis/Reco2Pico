#!/bin/bash
# ---------------------------------------------------------------------------
# Local end-to-end test of the Run-3 GEN-SIM-RAW -> Pico chain on a few events
# of one file of the dataset:
#   step1 RAW2DIGI,L1Reco,RECO,RECOSIM -> step2 RECO_to_pico (ntuple NTUPLE)
#
# Run from a shell where cmsenv has been done, with a valid grid proxy.
#
# Usage:  run_rawsim_local.sh [NEVENTS] [INPUT]      (defaults: 5, one file of the
#         DYto2Mu-4Jets Run3Winter26 GEN-SIM-RAW sample through the global redirector)
#
# Environment overrides:
#   TESTDIR    [<this dir>/local_test]  where cfgs and outputs go (not versioned)
#   CLEAN      [ask]  what to do when TESTDIR already exists (ask|yes|no)
#   NTUPLE     [reco-pico]  ntuple definition (../common/ntuples/)
#   plus everything make_rawsim_cfgs.sh understands (ERA, GT, PICO_TABLES, ...)
# ---------------------------------------------------------------------------
set -euo pipefail
SW_LOG=run_rawsim_local
WFDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck disable=SC1091
source "${WFDIR}/../common/chain_lib.sh"
sw_require_cmssw

NEVENTS="${1:-5}"
INPUT="${2:-root://cms-xrd-global.cern.ch//store/mc/Run3Winter26Digi/DYto2Mu-4Jets_Bin-MLL-50_TuneCP5_13p6TeV_madgraphMLM-pythia8/GEN-SIM-RAW/150X_mcRun3_2026_realistic_v4-v2/2820000/57860508-d92f-445b-ba90-1c97df93bcdf.root}"
TESTDIR="${TESTDIR:-${WFDIR}/local_test}"
CLEAN="${CLEAN:-ask}"
export NTUPLE="${NTUPLE:-reco-pico}"

sw_prepare_testdir "${TESTDIR}" "${CLEAN}"
sw_log "building cfgs in ${TESTDIR}/cfgs"
bash "${WFDIR}/make_rawsim_cfgs.sh" "${TESTDIR}/cfgs"
sw_load_ntuple "${NTUPLE}"
NTUPLE_CFG="cfgs/$(sw_ntuple_cfg_name)"

cd "${TESTDIR}"

sw_run_step 1 cfgs/step1_RECO_cfg.py inputFiles="${INPUT}" maxEvents="${NEVENTS}" skipEvents=0 output=step1.root
test -s step1.root

# shellcheck disable=SC2086
sw_run_step 2 "${NTUPLE_CFG}" inputFiles=file:step1.root secondaryInputFiles= maxEvents=-1 skipEvents=0 output=step2_pico.root ${NTUPLE_ARGS:-}
test -s step2_pico.root

sw_log "inspecting step2_pico.root (${NTUPLE})"
# shellcheck disable=SC2086
sw_inspect_nano step2_pico.root ${NTUPLE_INSPECT:-}
sw_make_ntuple_doc step2_pico.root "doc_${NTUPLE}.html" "run3_rawsim ${NTUPLE} (${NEVENTS} events)"
sw_log "done (outputs in ${TESTDIR}; variable documentation: ${TESTDIR}/doc_${NTUPLE}.html)"
