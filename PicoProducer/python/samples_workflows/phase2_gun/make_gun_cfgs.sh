#!/bin/bash
# ---------------------------------------------------------------------------
# Build the four cmsDriver cfgs of the Phase-2 single-hadron gun chain
#   step1  GEN,SIM                           (EmptySource + particle gun)
#   step2  DIGI,L1TrackTrigger,L1,L1P2GT,DIGI2RAW,HLT:@relvalRun4  (optional PU)
#   step3  RAW2DIGI,RECO,RECOSIM
#   step4  NANO:@HGCALVal
# and append gun_varparsing_tail.py to each of them.
#
# Usage:  make_gun_cfgs.sh [OUTDIR]          (default OUTDIR = <this dir>/cfgs)
#
# Environment overrides (defaults in brackets):
#   GEOM     [D110]                      -> --geometry ExtendedRun4$GEOM
#   ERA      [Phase2C17I13M9]            -> --era
#   GT       [auto:phase2_realistic_T35] -> --conditions for steps 2-4
#   GTGEN    [${GT}_13TeV if that alias exists, else $GT]
#                                        -> --conditions for step 1 (the relval
#                                           GenSimHLBeamSpot step uses the _13TeV
#                                           alias, which adds the HL-LHC
#                                           SimBeamSpot payload for DBrealisticHLLHC)
#   PU       [0]                         -> when != 0: --pileup AVE_${PU}_BX_25ns
#   PUINPUT  []                          -> --pileup_input (required when PU != 0)
#   DIGISTEP [DIGI:pdigi_valid,L1TrackTrigger,L1,L1P2GT,DIGI2RAW,HLT:@relvalRun4]
#   NANOSTEP [NANO:@HGCALVal]
#   NEVT     [10]                        -> -n of the cmsDriver commands (dummy)
#
# !! Verify GEOM / ERA / GT against the release you are running in:
#      runTheMatrix.py -w upgrade -n | grep -i Run4D
#      runTheMatrix.py -w upgrade -l <D110 workflow number> --dryRun   (then read runall-report-step123-.log / cmdLog)
#    or  python3 -c "from Configuration.PyReleaseValidation.upgradeWorkflowComponents import upgradeProperties as p; print(p['Run4']['Run4D110'])"
#    In CMSSW_16_1_0_pre2 the Run4D110 workflow uses GT auto:phase2_realistic_T35
#    (T33 is not defined there), era Phase2C17I13M9 and HLT menu @relvalRun4.
# ---------------------------------------------------------------------------
set -euo pipefail

if [ -z "${CMSSW_BASE:-}" ]; then
  echo "[make_gun_cfgs] ERROR: CMSSW_BASE is not set; run cmsenv first" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
OUTDIR="${1:-${SCRIPT_DIR}/cfgs}"
mkdir -p "${OUTDIR}"
OUTDIR="$(cd "${OUTDIR}" && pwd -P)"

GEOM="${GEOM:-D110}"
ERA="${ERA:-Phase2C17I13M9}"
GT="${GT:-auto:phase2_realistic_T35}"
PU="${PU:-0}"
PUINPUT="${PUINPUT:-}"
DIGISTEP="${DIGISTEP:-DIGI:pdigi_valid,L1TrackTrigger,L1,L1P2GT,DIGI2RAW,HLT:@relvalRun4}"
NANOSTEP="${NANOSTEP:-NANO:@HGCALVal}"
NEVT="${NEVT:-10}"

FRAGMENT="Reco2Pico/PicoProducer/python/samples_workflows/phase2_gun/SingleHadronPGun_cfi.py"
TAIL="${SCRIPT_DIR}/gun_varparsing_tail.py"
MARKER="phase2_gun: VarParsing tail"

if [ ! -f "${CMSSW_BASE}/src/${FRAGMENT}" ]; then
  echo "[make_gun_cfgs] ERROR: gun fragment not found: ${CMSSW_BASE}/src/${FRAGMENT}" >&2
  exit 1
fi
if [ ! -f "${TAIL}" ]; then
  echo "[make_gun_cfgs] ERROR: VarParsing tail not found: ${TAIL}" >&2
  exit 1
fi
for f in "${CMSSW_BASE}/src/Reco2Pico/PicoProducer/python/samples_workflows/__init__.py" "${SCRIPT_DIR}/__init__.py"; do
  [ -f "$f" ] || { echo "[make_gun_cfgs] ERROR: missing package marker $f (needed so cmsDriver can import the fragment)" >&2; exit 1; }
done

# --- GEN-step global tag: prefer the _13TeV alias used by the relval GenSimHLBeamSpot step
if [ -z "${GTGEN:-}" ]; then
  if [[ "${GT}" == auto:* ]] && python3 - "${GT#auto:}" <<'PYEOF'
import sys
from Configuration.AlCa.autoCond import autoCond
sys.exit(0 if sys.argv[1] + '_13TeV' in autoCond else 1)
PYEOF
  then
    GTGEN="${GT}_13TeV"
  else
    GTGEN="${GT}"
  fi
fi

# --- sanity check of the NANO flavour (cmsDriver's own error is not very explicit)
NANO_OK=1
NANOKEY=""
if [[ "${NANOSTEP}" == *@* ]]; then
  NANOKEY="${NANOSTEP#*@}"; NANOKEY="${NANOKEY%%[,+]*}"
  if ! python3 - "${NANOKEY}" <<'PYEOF'
import sys
from PhysicsTools.NanoAOD.autoNANO import autoNANO
sys.exit(0 if sys.argv[1] in autoNANO else 1)
PYEOF
  then
    NANO_OK=0
    echo "[make_gun_cfgs] WARNING: NANO flavour '@${NANOKEY}' is not defined in PhysicsTools.NanoAOD.autoNANO of ${CMSSW_VERSION:-this release}" >&2
    echo "[make_gun_cfgs]          steps 1-3 will be generated; step 4 is skipped unless NANOSTEP points to an existing flavour" >&2
    echo "[make_gun_cfgs]          available flavours: $(python3 -c 'from PhysicsTools.NanoAOD.autoNANO import autoNANO; print(" ".join(sorted(autoNANO)))')" >&2
  fi
fi

PUOPTS=()
if [ "${PU}" != "0" ]; then
  if [ -z "${PUINPUT}" ]; then
    echo "[make_gun_cfgs] ERROR: PU=${PU} requires PUINPUT (e.g. das:/RelValMinBias_14TeV/.../GEN-SIM or filelist:...)" >&2
    exit 1
  fi
  PUOPTS=(--pileup "AVE_${PU}_BX_25ns" --pileup_input "${PUINPUT}")
fi

COMMON=(--era "${ERA}" --geometry "ExtendedRun4${GEOM}" --no_exec --mc -n "${NEVT}")

echo "[make_gun_cfgs] CMSSW_BASE = ${CMSSW_BASE}"
echo "[make_gun_cfgs] OUTDIR     = ${OUTDIR}"
echo "[make_gun_cfgs] GEOM=${GEOM} ERA=${ERA} GT=${GT} GTGEN=${GTGEN} PU=${PU} PUINPUT=${PUINPUT:-<none>}"

cd "${OUTDIR}"

run_driver() {
  echo "[make_gun_cfgs] cmsDriver.py $*"
  cmsDriver.py "$@"
}

run_driver "${FRAGMENT}" \
  --conditions "${GTGEN}" "${COMMON[@]}" \
  --step GEN,SIM --eventcontent FEVTDEBUG --datatier GEN-SIM \
  --beamspot DBrealisticHLLHC \
  --fileout file:step1.root \
  --python_filename "${OUTDIR}/step1_GENSIM_cfg.py"

run_driver step2 \
  --conditions "${GT}" "${COMMON[@]}" \
  --step "${DIGISTEP}" --eventcontent FEVTDEBUGHLT --datatier GEN-SIM-DIGI-RAW \
  "${PUOPTS[@]}" \
  --filein file:step1.root --fileout file:step2.root \
  --python_filename "${OUTDIR}/step2_DIGIRAW_cfg.py"

run_driver step3 \
  --conditions "${GT}" "${COMMON[@]}" \
  --step RAW2DIGI,RECO,RECOSIM --eventcontent FEVTDEBUGHLT --datatier GEN-SIM-RECO \
  --filein file:step2.root --fileout file:step3.root \
  --python_filename "${OUTDIR}/step3_RECO_cfg.py"

if [ "${NANO_OK}" = "1" ]; then
  run_driver step4 \
    --conditions "${GT}" "${COMMON[@]}" \
    --step "${NANOSTEP}" --eventcontent NANOAODSIM --datatier NANOAODSIM \
    --filein file:step3.root --fileout file:step4.root \
    --python_filename "${OUTDIR}/step4_NANO_cfg.py"
fi

# --- append the VarParsing tail (idempotent)
for cfg in step1_GENSIM_cfg.py step2_DIGIRAW_cfg.py step3_RECO_cfg.py step4_NANO_cfg.py; do
  [ -f "${OUTDIR}/${cfg}" ] || continue
  if grep -q "${MARKER}" "${OUTDIR}/${cfg}"; then
    echo "[make_gun_cfgs] ${cfg}: VarParsing tail already present"
  else
    cat "${TAIL}" >> "${OUTDIR}/${cfg}"
    echo "[make_gun_cfgs] ${cfg}: VarParsing tail appended"
  fi
done

if [ "${NANO_OK}" != "1" ]; then
  echo "[make_gun_cfgs] ERROR: step4_NANO_cfg.py was NOT generated (unknown NANO flavour '@${NANOKEY}')" >&2
  exit 2
fi
echo "[make_gun_cfgs] done: $(ls "${OUTDIR}"/step?_*_cfg.py | xargs -n1 basename | tr '\n' ' ')"
