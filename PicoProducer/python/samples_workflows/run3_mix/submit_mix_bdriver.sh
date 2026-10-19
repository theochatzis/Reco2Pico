#!/bin/bash
# ---------------------------------------------------------------------------
# Create (and optionally submit) HTCondor jobs for the classically mixed Run-3
# chain with Reco2Pico's bdriver: step0 DIGI (MixingModule on minimum-bias
# GEN-SIM, pile-up truth kept) on the DY GEN-SIM files, step1 RECO, then the
# ntuple step (default reco-pico with pileupTruth=picoMixedTruth) whose output
# is staged out.
#
# Usage:  submit_mix_bdriver.sh [--submit] [--dry-run]
#
# Environment overrides (defaults in brackets):
#   DATASET        [<this dir>/datasets/DYto2Mu-4Jets_Winter26_GEN-SIM.json]
#                               bdriver dataset JSON (files + nevents) or a DAS dataset name;
#                               the central DY GEN-SIM is mostly on tape, so a JSON of the
#                               files copied to the group EOS area is the default
#   MAX_FILES      [10]         files taken from the dataset (-1: all)
#   EVENTS_PER_JOB [200]        events per job (DIGI: 15 min start-up + 20 s/event, RECO 10 s/event,
#                               Pico 4 s/event: about 2.5 h per job; 13 + 16 MB/event of intermediates)
#   NTUPLE         [reco-pico]  ntuple definition (../common/ntuples/)
#   FINAL_OUTPUT   [/eos/cms/store/group/phys_jetmet/tchatzis/reco2pico/run3_mix]  destination of the Picos
#   JOBAREA        [<this dir>/jobs]  bdriver -o
#   CONDOR_WORKDIR [bdriver default: ~/condor_jobs_files on AFS]  non-EOS area for the Condor
#                  bookkeeping (~1 GB per job area); e.g. /afs/cern.ch/work/<x>/<user>/condor_jobs_files
#   TAG            [<dataset JSON name, first two fields>]   job tag (subdirectory of JOBAREA/FINAL_OUTPUT)
#   OS             [el9]        bdriver --os
#   RUNTIME        [08:00:00]   bdriver -t
#   MEMORY         [7G]         bdriver --memory (classical mixing at 65 interactions: 5 GB)
#   DISK_MB        [20000]      bdriver --disk-mb (RAW + RECOSIM intermediates with the pile-up truth)
#   CFGDIR         [<this dir>/cfgs]                 cfg location (make_mix_cfgs.sh output)
#   SAMPLE_STEPS   [<this dir>/steps_mix_chain.json] sample steps manifest (step1 RECO; step0 is the DIGI cfg)
#   DATASETS       [<this dir>/datasets]  where composed manifests go
# ---------------------------------------------------------------------------
set -euo pipefail
SW_LOG=submit_mix_bdriver
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

DATASET="${DATASET:-${SCRIPT_DIR}/datasets/DYto2Mu-4Jets_Winter26_GEN-SIM.json}"
MAX_FILES="${MAX_FILES:-10}"
EVENTS_PER_JOB="${EVENTS_PER_JOB:-200}"
export NTUPLE="${NTUPLE:-reco-pico}"
FINAL_OUTPUT="${FINAL_OUTPUT:-/eos/cms/store/group/phys_jetmet/tchatzis/reco2pico/run3_mix}"
JOBAREA="${JOBAREA:-${SCRIPT_DIR}/jobs}"
OS="${OS:-el9}"
RUNTIME="${RUNTIME:-08:00:00}"
MEMORY="${MEMORY:-7G}"
DISK_MB="${DISK_MB:-20000}"
CFGDIR="${CFGDIR:-${SCRIPT_DIR}/cfgs}"
SAMPLE_STEPS="${SAMPLE_STEPS:-${SCRIPT_DIR}/steps_mix_chain.json}"
DATASETS="${DATASETS:-${SCRIPT_DIR}/datasets}"
if [ -z "${TAG:-}" ]; then
  TAG="$(basename "${DATASET}" .json | cut -d_ -f1-2)"
  [ -n "${TAG}" ] || TAG="mix"
fi

sw_load_ntuple "${NTUPLE}"
NTUPLE_ARGS="${NTUPLE_ARGS:-} pileupTruth=picoMixedTruth"
STEP1_CFG="${CFGDIR}/step0_DIGI_cfg.py"
NTUPLE_CFG="${CFGDIR}/$(sw_ntuple_cfg_name)"
for f in "${STEP1_CFG}" "${NTUPLE_CFG}" "${SAMPLE_STEPS}"; do
  [ -f "${f}" ] || sw_die "missing ${f}; run NTUPLE=${NTUPLE} make_mix_cfgs.sh ${CFGDIR}"
done

mkdir -p "${DATASETS}"
steps="${DATASETS}/steps_${TAG}_${NTUPLE}.json"

sw_section "run3 classically mixed GEN-SIM -> Pico chain (${TAG})"
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
  --name "mix_${TAG}" --events-per-job "${EVENTS_PER_JOB}" --max-files "${MAX_FILES}" \
  --parents 0 --runtime "${RUNTIME}" --os "${OS}" --memory "${MEMORY}" --cpus 1 --disk-mb "${DISK_MB}" --job-flavour workday
sw_log "done"
