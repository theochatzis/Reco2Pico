#!/bin/bash
# ---------------------------------------------------------------------------
# Local end-to-end test of the classically mixed Run-3 chain on a few events:
#   step0 DIGI,L1,DIGI2RAW with the MixingModule on minimum-bias GEN-SIM (pile-up
#         truth kept) -> step1 RAW2DIGI,L1Reco,RECO,RECOSIM -> step2 RECO_to_pico
#
# Run from a shell where cmsenv has been done, with a valid grid proxy if the
# inputs are read through xrootd.
#
# Usage:  run_mix_local.sh [NEVENTS] [INPUT]      (defaults: 5, one DY GEN-SIM file
#         of the Run3Winter26 sample copied to the group EOS area)
#
# Environment overrides:
#   TESTDIR    [<this dir>/local_test]  where cfgs and outputs go (not versioned)
#   CLEAN      [ask]  what to do when TESTDIR already exists (ask|yes|no)
#   NTUPLE     [reco-pico]  ntuple definition (../common/ntuples/)
#   plus everything make_mix_cfgs.sh understands (PU_SCENARIO, PU_INPUT, ERA, GT, ...)
# ---------------------------------------------------------------------------
set -euo pipefail
SW_LOG=run_mix_local
WFDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck disable=SC1091
source "${WFDIR}/../common/chain_lib.sh"
sw_require_cmssw

NEVENTS="${1:-5}"
INPUT="${2:-root://eoscms.cern.ch//eos/cms/store/group/phys_jetmet/tchatzis/reco2pico/gensim/DYto2Mu-4Jets_Winter26/409c0e4f-26c3-42e8-b405-fd32516da747.root}"
TESTDIR="${TESTDIR:-${WFDIR}/local_test}"
CLEAN="${CLEAN:-ask}"
export NTUPLE="${NTUPLE:-reco-pico}"

sw_prepare_testdir "${TESTDIR}" "${CLEAN}"
sw_log "building cfgs in ${TESTDIR}/cfgs"
bash "${WFDIR}/make_mix_cfgs.sh" "${TESTDIR}/cfgs"
sw_load_ntuple "${NTUPLE}"
NTUPLE_ARGS="${NTUPLE_ARGS:-} pileupTruth=picoMixedTruth"
NTUPLE_CFG="cfgs/$(sw_ntuple_cfg_name)"

cd "${TESTDIR}"

sw_run_step 0 cfgs/step0_DIGI_cfg.py inputFiles="${INPUT}" maxEvents="${NEVENTS}" skipEvents=0 output=step0.root
test -s step0.root
sw_run_step 1 cfgs/step1_RECO_cfg.py inputFiles=file:step0.root maxEvents=-1 skipEvents=0 output=step1.root
test -s step1.root
# shellcheck disable=SC2086
sw_run_step 2 "${NTUPLE_CFG}" inputFiles=file:step1.root secondaryInputFiles= maxEvents=-1 skipEvents=0 output=step2_pico.root ${NTUPLE_ARGS:-}
test -s step2_pico.root

sw_log "inspecting step2_pico.root (${NTUPLE})"
# shellcheck disable=SC2086
sw_inspect_nano step2_pico.root ${NTUPLE_INSPECT:-} SimCaloCell SimCaloCellPUJet SimPFPUJet SimPFPUCHSJet
sw_make_ntuple_doc step2_pico.root "doc_${NTUPLE}.html" "run3_mix ${NTUPLE} (${NEVENTS} events)"
sw_log "done (outputs in ${TESTDIR}; variable documentation: ${TESTDIR}/doc_${NTUPLE}.html)"
