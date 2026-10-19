#!/bin/bash
# ---------------------------------------------------------------------------
# A small Pico sample WITH THE DIGIS from the classically mixed chain, locally:
#   step0 DIGI,L1,DIGI2RAW (mixing, pile-up truth)  ->  step1 RECO  ->
#   Pico with every table group, every ECAL rechit and the calodigis group, the
#   step0 RAW given as the secondary input (the digis are unpacked from it).
# The Pico is copied to FINAL_OUTPUT; the intermediate files stay in WORKDIR.
#
# Usage:  produce_digi_sample.sh [NEVENTS] [SKIP] [WORKDIR]
#         (defaults: 200 events, skip 0, WORKDIR = <this dir>/digi_sample_<skip>)
# Environment overrides:
#   INPUT        one DY GEN-SIM file (default: the first file of the group EOS copy)
#   FINAL_OUTPUT [/eos/cms/store/group/phys_jetmet/tchatzis/reco2pico/run3_mix_digis/DYto2Mu-4Jets_Winter26]
#   DIGI_MIN_AMPLITUDE [0.1]  digis kept above this [GeV on the rechit scale]
#   plus everything make_mix_cfgs.sh understands (PU_SCENARIO, PU_INPUT, ERA, GT, ...)
# Needs cmsenv and access to the inputs (xrootd with a grid proxy or a CERN
# Kerberos ticket). About 2.5 hours and 7 GB of disk for 200 events.
# ---------------------------------------------------------------------------
set -euo pipefail
SW_LOG=produce_digi_sample
WFDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck disable=SC1091
source "${WFDIR}/../common/chain_lib.sh"
sw_require_cmssw

NEVENTS="${1:-200}"
SKIP="${2:-0}"
WORKDIR="${3:-${WFDIR}/digi_sample_${SKIP}}"
INPUT="${INPUT:-root://eoscms.cern.ch//eos/cms/store/group/phys_jetmet/tchatzis/reco2pico/gensim/DYto2Mu-4Jets_Winter26/409c0e4f-26c3-42e8-b405-fd32516da747.root}"
FINAL_OUTPUT="${FINAL_OUTPUT:-/eos/cms/store/group/phys_jetmet/tchatzis/reco2pico/run3_mix_digis/DYto2Mu-4Jets_Winter26}"
DIGI_MIN_AMPLITUDE="${DIGI_MIN_AMPLITUDE:-0.1}"
export NTUPLE="${NTUPLE:-reco-pico}"
# the table groups go through the ntuple definition (NTUPLE_ARGS), the pile-up truth label is added here
export PICO_TABLES="${PICO_TABLES:-event,muons,electrons,jets,pfcands,tracks,vertices,pfclusters,pfblocks,genparts,sim,simcalo,recojets,rechits,calodigis}"
LAST=$((SKIP + NEVENTS - 1))
PICO="pico_digis_events${SKIP}to${LAST}.root"

mkdir -p "${WORKDIR}"
WORKDIR="$(cd "${WORKDIR}" && pwd -P)"
sw_log "building cfgs in ${WORKDIR}/cfgs"
bash "${WFDIR}/make_mix_cfgs.sh" "${WORKDIR}/cfgs"
sw_load_ntuple "${NTUPLE}"
NTUPLE_CFG="cfgs/$(sw_ntuple_cfg_name)"
cd "${WORKDIR}"

sw_run_step 0 cfgs/step0_DIGI_cfg.py inputFiles="${INPUT}" maxEvents="${NEVENTS}" skipEvents="${SKIP}" output=step0.root
test -s step0.root
sw_run_step 1 cfgs/step1_RECO_cfg.py inputFiles=file:step0.root maxEvents=-1 skipEvents=0 output=step1.root
test -s step1.root
# shellcheck disable=SC2086
sw_run_step 2 "${NTUPLE_CFG}" inputFiles=file:step1.root secondaryInputFiles=file:step0.root maxEvents=-1 skipEvents=0 \
  output="${PICO}" ${NTUPLE_ARGS:-} \
  pileupTruth=picoMixedTruth fullEcalRecHits=True digiMinAmplitude="${DIGI_MIN_AMPLITUDE}"
test -s "${PICO}"
mkdir -p "${FINAL_OUTPUT}"
cp "${PICO}" "${FINAL_OUTPUT}/"
sw_log "done: ${FINAL_OUTPUT}/${PICO} (intermediate files in ${WORKDIR})"
