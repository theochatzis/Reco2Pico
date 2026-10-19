#!/bin/bash
# ---------------------------------------------------------------------------
# Build the cmsDriver cfgs of the Phase-2 single-hadron gun chain
#   step1  GEN,SIM                                          (EmptySource + particle gun)
#   step2  DIGI,L1TrackTrigger,L1,L1P2GT,DIGI2RAW,HLT:@relvalRun4  (optional PU)
#   step3  RAW2DIGI,RECO,RECOSIM
#   ntuple one of common/ntuples/*.sh (default hgcalval-nano)  -> ntuple_<NTUPLE>_cfg.py
# and append gun_varparsing_tail.py to each of them.
#
# Usage:  make_gun_cfgs.sh [OUTDIR]          (default OUTDIR = <this dir>/cfgs)
#
# Environment overrides (defaults in brackets):
#   GEOM     [D127]                      -> --geometry ExtendedRun4$GEOM
#   ERA      [Phase2C26I13M9]            -> --era
#   GT       [auto:phase2_realistic_T35] -> --conditions for steps 2-3 and the ntuple
#   GTGEN    [${GT}_13TeV if that alias exists, else $GT]  -> --conditions for step 1
#   PU       [0]                         -> when != 0: --pileup AVE_${PU}_BX_25ns
#   PUINPUT  []                          -> --pileup_input (required when PU != 0)
#   DIGISTEP [DIGI:pdigi_valid,L1TrackTrigger,L1,L1P2GT,DIGI2RAW,HLT:@relvalRun4]
#   NTUPLE   [hgcalval-nano]             -> ntuple definition, see ../common/ntuples/
#   NEVT     [10]                        -> -n of the cmsDriver commands (dummy)
#
# !! Verify GEOM / ERA / GT against the release you are running in:
#      runTheMatrix.py -w upgrade -n -e -l 37634.0,37696.0     (TTbar / CloseByPGun CE_E_Front_120um)
#      python3 -c "from Configuration.PyReleaseValidation.upgradeWorkflowComponents import upgradeProperties as p; print(p['Run4']['Run4D127'])"
#    D127 is the Phase-2 baseline since CMSSW_20_1_0_pre2 (Configuration/Geometry/README.md,
#    prefixDet=37600 in relval_Run4.py) and the geometry of the HGCAL/TICL relvals in the
#    limited matrix (CloseByPGun_CE_*). D128 (workflow 38434.0) is the same with the M16
#    muon geometry, "to be used for trigger studies"; same era/GT/HLT menu.
#    In CMSSW_20_1_0_pre3 the Run4D127 workflow uses GT auto:phase2_realistic_T35,
#    era Phase2C26I13M9 and HLT menu @relvalRun4 (= HLT_75e33, Configuration/HLT/autoHLT.py).
# ---------------------------------------------------------------------------
set -euo pipefail
SW_LOG=make_gun_cfgs
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../common/chain_lib.sh"
sw_require_cmssw

OUTDIR="${1:-${SCRIPT_DIR}/cfgs}"
mkdir -p "${OUTDIR}"
OUTDIR="$(cd "${OUTDIR}" && pwd -P)"

GEOM="${GEOM:-D127}"
ERA="${ERA:-Phase2C26I13M9}"
GT="${GT:-auto:phase2_realistic_T35}"
PU="${PU:-0}"
PUINPUT="${PUINPUT:-}"
DIGISTEP="${DIGISTEP:-DIGI:pdigi_valid,L1TrackTrigger,L1,L1P2GT,DIGI2RAW,HLT:@relvalRun4}"
NTUPLE="${NTUPLE:-hgcalval-nano}"
NEVT="${NEVT:-10}"
GTGEN="${GTGEN:-$(sw_gtgen "${GT}")}"

FRAGMENT="Reco2Pico/PicoProducer/python/samples_workflows/phase2_gun/SingleHadronPGun_cfi.py"
TAIL="${SCRIPT_DIR}/gun_varparsing_tail.py"

[ -f "${CMSSW_BASE}/src/${FRAGMENT}" ] || sw_die "gun fragment not found: ${CMSSW_BASE}/src/${FRAGMENT}"
[ -f "${TAIL}" ] || sw_die "VarParsing tail not found: ${TAIL}"
for f in "${SCRIPT_DIR}/../__init__.py" "${SCRIPT_DIR}/../common/__init__.py" "${SCRIPT_DIR}/__init__.py"; do
  [ -f "$f" ] || sw_die "missing package marker $f (needed so cmsDriver/cmsRun can import the fragment, the tail and the customise)"
done

sw_load_ntuple "${NTUPLE}"

PUOPTS=()
if [ "${PU}" != "0" ]; then
  [ -n "${PUINPUT}" ] || sw_die "PU=${PU} requires PUINPUT (e.g. das:/RelValMinBias_14TeV/.../GEN-SIM or filelist:...)"
  PUOPTS=(--pileup "AVE_${PU}_BX_25ns" --pileup_input "${PUINPUT}")
fi

COMMON=(--era "${ERA}" --geometry "ExtendedRun4${GEOM}" --no_exec --mc -n "${NEVT}")

sw_log "CMSSW_BASE = ${CMSSW_BASE}"
sw_log "OUTDIR     = ${OUTDIR}"
sw_log "GEOM=${GEOM} ERA=${ERA} GT=${GT} GTGEN=${GTGEN} PU=${PU} PUINPUT=${PUINPUT:-<none>} NTUPLE=${NTUPLE}"

cd "${OUTDIR}"

sw_run_driver "${FRAGMENT}" \
  --conditions "${GTGEN}" "${COMMON[@]}" \
  --step GEN,SIM --eventcontent FEVTDEBUG --datatier GEN-SIM \
  --beamspot DBrealisticHLLHC \
  --fileout file:step1.root \
  --python_filename "${OUTDIR}/step1_GENSIM_cfg.py"

sw_run_driver step2 \
  --conditions "${GT}" "${COMMON[@]}" \
  --step "${DIGISTEP}" --eventcontent FEVTDEBUGHLT --datatier GEN-SIM-DIGI-RAW \
  "${PUOPTS[@]}" \
  --filein file:step1.root --fileout file:step2.root \
  --python_filename "${OUTDIR}/step2_DIGIRAW_cfg.py"

sw_run_driver step3 \
  --conditions "${GT}" "${COMMON[@]}" \
  --step RAW2DIGI,RECO,RECOSIM --eventcontent FEVTDEBUGHLT --datatier GEN-SIM-RECO \
  --filein file:step2.root --fileout file:step3.root \
  --python_filename "${OUTDIR}/step3_RECO_cfg.py"

sw_make_ntuple_cfg "${OUTDIR}" file:step3.root -- --conditions "${GT}" "${COMMON[@]}"

for cfg in step1_GENSIM_cfg.py step2_DIGIRAW_cfg.py step3_RECO_cfg.py "$(sw_ntuple_cfg_name)"; do
  sw_append_tail "${OUTDIR}/${cfg}" "${TAIL}"
done
sw_log "done: step1_GENSIM_cfg.py step2_DIGIRAW_cfg.py step3_RECO_cfg.py $(sw_ntuple_cfg_name)"
