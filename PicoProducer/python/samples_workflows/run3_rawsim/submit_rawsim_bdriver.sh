#!/bin/bash
# ---------------------------------------------------------------------------
# Create (and optionally submit) HTCondor jobs for the Run-3 GEN-SIM-RAW -> Pico
# chain with Reco2Pico's bdriver: step1 RECO on the dataset files, then the
# ntuple step (default reco-pico) whose output is staged out.
#
# Usage:  submit_rawsim_bdriver.sh [--submit] [--dry-run]
#
# Environment overrides (defaults in brackets):
#   DATASET        [/DYto2Mu-4Jets_Bin-MLL-50_TuneCP5_13p6TeV_madgraphMLM-pythia8/Run3Winter26Digi-150X_mcRun3_2026_realistic_v4-v2/GEN-SIM-RAW]
#                               DAS dataset name (or a bdriver dataset JSON)
#   MAX_FILES      [10]         files taken from the dataset (-1: all)
#   EVENTS_PER_JOB [200]        events per job (one file of this sample holds ~1900)
#   NTUPLE         [reco-pico]  ntuple definition (../common/ntuples/)
#   FINAL_OUTPUT   [/eos/cms/store/group/phys_jetmet/tchatzis/reco2pico/run3_rawsim]  destination of the Picos
#   JOBAREA        [<this dir>/jobs]  bdriver -o
#   CONDOR_WORKDIR [bdriver default: ~/condor_jobs_files on AFS]  non-EOS area for the Condor
#                  bookkeeping (~1 GB per job area); e.g. /afs/cern.ch/work/<x>/<user>/condor_jobs_files
#   TAG            [<dataset primary name>]   job tag (subdirectory of JOBAREA/FINAL_OUTPUT)
#   OS             [el9]        bdriver --os
#   RUNTIME        [10:00:00]   bdriver -t
#   MEMORY         [6G]         bdriver --memory (RECO of 2026 pile-up events)
#   DISK_MB        [20000]      bdriver --disk-mb (RECOSIM intermediate + Pico)
#   CFGDIR         [<this dir>/cfgs]                    cfg location (make_rawsim_cfgs.sh output)
#   SAMPLE_STEPS   [<this dir>/steps_rawsim_chain.json] sample steps manifest (empty: step1 is the RECO cfg)
#   DATASETS       [<this dir>/datasets]  where composed manifests go
# ---------------------------------------------------------------------------
set -euo pipefail
SW_LOG=submit_rawsim_bdriver
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../common/chain_lib.sh"
sw_require_cmssw

PASS=()
for arg in "$@"; do
  case "${arg}" in
    --submit|--dry-run) PASS+=("${arg}") ;;
    -h|--help) sed -n '3,/^# ----/p' "${BASH_SOURCE[0]}" | sed '$d'; exit 0 ;;
    *) sw_die "unknown argument: ${arg}" ;;
  esac
done

DATASET="${DATASET:-/DYto2Mu-4Jets_Bin-MLL-50_TuneCP5_13p6TeV_madgraphMLM-pythia8/Run3Winter26Digi-150X_mcRun3_2026_realistic_v4-v2/GEN-SIM-RAW}"
MAX_FILES="${MAX_FILES:-10}"
EVENTS_PER_JOB="${EVENTS_PER_JOB:-200}"
export NTUPLE="${NTUPLE:-reco-pico}"
FINAL_OUTPUT="${FINAL_OUTPUT:-/eos/cms/store/group/phys_jetmet/tchatzis/reco2pico/run3_rawsim}"
JOBAREA="${JOBAREA:-${SCRIPT_DIR}/jobs}"
OS="${OS:-el9}"
RUNTIME="${RUNTIME:-10:00:00}"
MEMORY="${MEMORY:-6G}"
DISK_MB="${DISK_MB:-20000}"
CFGDIR="${CFGDIR:-${SCRIPT_DIR}/cfgs}"
SAMPLE_STEPS="${SAMPLE_STEPS:-${SCRIPT_DIR}/steps_rawsim_chain.json}"
DATASETS="${DATASETS:-${SCRIPT_DIR}/datasets}"
if [ -z "${TAG:-}" ]; then
  TAG="$(cut -d/ -f2 <<<"${DATASET}" | cut -d_ -f1-2)"
  [ -n "${TAG}" ] || TAG="rawsim"
fi

sw_load_ntuple "${NTUPLE}"
STEP1_CFG="${CFGDIR}/step1_RECO_cfg.py"
NTUPLE_CFG="${CFGDIR}/$(sw_ntuple_cfg_name)"
for f in "${STEP1_CFG}" "${NTUPLE_CFG}" "${SAMPLE_STEPS}"; do
  [ -f "${f}" ] || sw_die "missing ${f}; run NTUPLE=${NTUPLE} make_rawsim_cfgs.sh ${CFGDIR}"
done

mkdir -p "${DATASETS}"
steps="${DATASETS}/steps_${TAG}_${NTUPLE}.json"

sw_section "run3 GEN-SIM-RAW -> Pico chain (${TAG})"
sw_kv dataset "${DATASET}"
sw_kv files "${MAX_FILES} (max), ${EVENTS_PER_JOB} events per job"
sw_kv ntuple "${NTUPLE} ${NTUPLE_ARGS:-}"
sw_kv "job area" "${JOBAREA}/${TAG}"
sw_kv "final output" "${FINAL_OUTPUT}/${TAG}"
sw_kv mode "${PASS[*]:-prepare only (no --submit)}"

sw_compose_steps "${steps}" "${SAMPLE_STEPS}" "${NTUPLE_CFG}" "${NTUPLE_ARGS:-}"

bash "${SCRIPT_DIR}/../common/submit_bdriver_chain.sh" "${PASS[@]}" \
  --dataset "${DATASET}" --step1 "${STEP1_CFG}" --steps "${steps}" \
  --jobarea "${JOBAREA}/${TAG}" --final-output "${FINAL_OUTPUT}/${TAG}" \
  --name "rawsim_${TAG}" --events-per-job "${EVENTS_PER_JOB}" --max-files "${MAX_FILES}" \
  --parents 0 --runtime "${RUNTIME}" --os "${OS}" --memory "${MEMORY}" --cpus 1 --disk-mb "${DISK_MB}" --job-flavour workday
sw_log "done"
