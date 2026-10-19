#!/bin/bash
# ---------------------------------------------------------------------------
# Build the cfgs of the classically mixed Run-3 chain
#   step0  DIGI,L1,DIGI2RAW with the MixingModule reading minimum-bias GEN-SIM
#          (the pile-up truth is kept: mixCustomise.pileupTruth)
#   step1  RAW2DIGI,L1Reco,RECO,RECOSIM (as run3_rawsim, plus the pile-up truth)
#   ntuple common/ntuples/reco-pico.sh with pileupTruth=picoMixedTruth
# and append the VarParsing tail to step0 and step1.
#
# Usage:  make_mix_cfgs.sh [OUTDIR]          (default OUTDIR = <this dir>/cfgs)
#
# Environment overrides:
#   ERA         [Run3_2025]                      -> --era
#   GT          [150X_mcRun3_2026_realistic_v4]  -> --conditions
#   GEOM        [DB:Extended]                    -> --geometry
#   DIGISTEP    [DIGI,L1,DIGI2RAW]               -> --step of step0 (no HLT: offline RECO does not need it)
#   RECOSTEP    [RAW2DIGI,L1Reco,RECO,RECOSIM]   -> --step of step1
#   PU_SCENARIO [2025_LHC_Simulation_fill12p5h_levelling9h_nb2340_xSec80mb_il2p23]
#                                                -> --pileup (mean 64, as the Winter26 premix library)
#   PU_INPUT    [<this dir>/minbias_files.txt]   -> --pileup_input: text file with the minimum-bias
#                                                GEN-SIM files (one per line, xrootd or local paths)
#   NTUPLE      [reco-pico]                      -> ntuple definition, see ../common/ntuples/
#   PICO_TABLES []                               -> table groups of the reco-pico ntuple
#   NEVT        [10]                             -> -n of the cmsDriver commands (dummy)
# ---------------------------------------------------------------------------
set -euo pipefail
SW_LOG=make_mix_cfgs
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
DIGISTEP="${DIGISTEP:-DIGI,L1,DIGI2RAW}"
RECOSTEP="${RECOSTEP:-RAW2DIGI,L1Reco,RECO,RECOSIM}"
PU_SCENARIO="${PU_SCENARIO:-2025_LHC_Simulation_fill12p5h_levelling9h_nb2340_xSec80mb_il2p23}"
PU_INPUT="${PU_INPUT:-${SCRIPT_DIR}/minbias_files.txt}"
NTUPLE="${NTUPLE:-reco-pico}"
NEVT="${NEVT:-10}"
export NTUPLE_EXTRA_ARGS="pileupTruth=picoMixedTruth"

TAIL="${SCRIPT_DIR}/../run3_rawsim/rawsim_varparsing_tail.py"
[ -f "${TAIL}" ] || sw_die "VarParsing tail not found: ${TAIL}"
[ -f "${PU_INPUT}" ] || sw_die "minimum-bias file list not found: ${PU_INPUT} (one GEN-SIM file per line)"
PU_FILES="$(grep -v '^\s*#' "${PU_INPUT}" | grep -v '^\s*$' | paste -sd, -)"
[ -n "${PU_FILES}" ] || sw_die "empty minimum-bias file list ${PU_INPUT}"
for f in "${SCRIPT_DIR}/../__init__.py" "${SCRIPT_DIR}/../common/__init__.py" "${SCRIPT_DIR}/__init__.py"; do
  [ -f "$f" ] || sw_die "missing package marker $f"
done

sw_load_ntuple "${NTUPLE}"
NTUPLE_ARGS="${NTUPLE_ARGS:-} ${NTUPLE_EXTRA_ARGS}"
export NTUPLE_ARGS

sw_log "CMSSW_BASE = ${CMSSW_BASE}"
sw_log "OUTDIR     = ${OUTDIR}"
sw_log "ERA=${ERA} GT=${GT} GEOM=${GEOM} DIGI=${DIGISTEP} RECO=${RECOSTEP} PU=${PU_SCENARIO} ($(echo "${PU_FILES}" | tr ',' '\n' | wc -l) minimum-bias files)"

cd "${OUTDIR}"

sw_run_driver step0 \
  --era "${ERA}" --conditions "${GT}" --geometry "${GEOM}" \
  --step "${DIGISTEP}" --eventcontent RAWSIM --datatier GEN-SIM-RAW \
  --pileup "${PU_SCENARIO}" --pileup_input "${PU_FILES}" \
  --customise Reco2Pico/PicoProducer/samples_workflows/run3_mix/mixCustomise.pileupTruth \
  --mc --no_exec -n "${NEVT}" \
  --filein file:gensim.root --fileout file:step0.root \
  --python_filename "${OUTDIR}/step0_DIGI_cfg.py"

sw_run_driver step1 \
  --era "${ERA}" --conditions "${GT}" --geometry "${GEOM}" \
  --step "${RECOSTEP}" --eventcontent RECOSIM --datatier GEN-SIM-RECO \
  --customise Reco2Pico/PicoProducer/samples_workflows/run3_rawsim/recoCustomise.keepSimTruth \
  --customise Reco2Pico/PicoProducer/samples_workflows/run3_mix/mixCustomise.keepPileupTruth \
  --mc --no_exec -n "${NEVT}" \
  --filein file:step0.root --fileout file:step1.root \
  --python_filename "${OUTDIR}/step1_RECO_cfg.py"

sw_make_ntuple_cfg "${OUTDIR}" file:step1.root -- --conditions "${GT}" --era "${ERA}" --mc --no_exec -n "${NEVT}"
sw_append_tail "${OUTDIR}/step0_DIGI_cfg.py" "${TAIL}"
sw_append_tail "${OUTDIR}/step1_RECO_cfg.py" "${TAIL}"
sw_log "done: step0_DIGI_cfg.py step1_RECO_cfg.py $(sw_ntuple_cfg_name)  (ntuple args: ${NTUPLE_ARGS:-<none>})"
