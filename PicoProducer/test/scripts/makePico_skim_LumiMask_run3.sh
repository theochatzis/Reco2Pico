#!/bin/bash

set -e

if [ $# -ne 1 ]; then
  printf "\n%s\n\n" ">> argument missing - specify path to local condor working/output directory"
  exit 1
fi

DEFAULT_NEVT=1000000
EVENTS_PER_JOB=10000
MEMORY=2G
RUNTIME=02:00:00

USE_JSON=true

OUTPUT_DIR_EOS=/eos/user/${USER:0:1}/${USER}/reco2pico/myPicosDirectory/
ODIR=${1}

LUMI_JSON=/eos/user/c/cmsdqm/www/CAF/certification/Collisions25/Cert_Collisions2025_391658_398903_Golden.json
SKIM="zjet"

declare -A dataSamplesMap
declare -A mcSamplesMap
declare -A dataMaxEventsMap
declare -A mcMaxEventsMap

# DATA samples
#dataSamplesMap["Muon2025G"]="/Muon0/Run2025G-PromptReco-v1/MINIAOD"

# Per-DATA-sample max events
#dataMaxEventsMap["Muon2025G"]=500000000

# MC samples
mcSamplesMap["ZTo2Mu"]="/ZTo2Mu_Bin-M-50to120_TuneCP5_13p6TeV_powheg-pythia8/Run3Winter25MiniAOD-142X_mcRun3_2025_realistic_v7-v2/MINIAODSIM"

# Per-MC-sample max events
mcMaxEventsMap["ZTo2Mu"]=10000000

recoKeys=(
  default
)

if [ -d ${OUTPUT_DIR_EOS}/${ODIR} ]; then
  printf "%s\n" "output directory already exists: ${OUTPUT_DIR_EOS}/${ODIR}"
  echo "If you continue the following directories may get overwritten:"
  for recoKey in "${recoKeys[@]}"; do
    find ${OUTPUT_DIR_EOS}/${ODIR} -path ${OUTPUT_DIR_EOS}/${ODIR}/${recoKey} 2>/dev/null || true
  done
  read -p "Do you want to continue? [y/n] " yn
  case $yn in
      [Yy]* ) echo "Continuing the process...";;
      [Nn]* ) echo "Exiting..."; unset recoKey recoKeys dataSamplesMap mcSamplesMap dataMaxEventsMap mcMaxEventsMap DEFAULT_NEVT ODIR; exit 1;;
      * ) echo "Please answer with y/n."; exit 1;;
  esac
fi

run_samples() {
  local sampleType=$1
  local -n samplesMap=$2

  for sampleKey in "${!samplesMap[@]}"; do
    sampleName=${samplesMap[${sampleKey}]}

    if [ "${sampleType}" = "DATA" ]; then
      numEvents=${dataMaxEventsMap[${sampleKey}]:-${DEFAULT_NEVT}}
    else
      numEvents=${mcMaxEventsMap[${sampleKey}]:-${DEFAULT_NEVT}}
    fi

    FINAL_OUTPUT_DIR=${OUTPUT_DIR_EOS}/${ODIR}/${recoKey}/${sampleType}/${sampleKey}

    if [ -d ${FINAL_OUTPUT_DIR} ]; then rm -rf ${OUTPUT_DIR_EOS}/${ODIR}/${recoKey}/${sampleType}; fi
    mkdir -p ${FINAL_OUTPUT_DIR}

    if [ -d ${ODIR}/${recoKey}/${sampleType}/${sampleKey} ]; then rm -rf ${ODIR}/${recoKey}/${sampleType}/${sampleKey}; fi

    bdriver_args=(
      -c tmp_cfg.py --customize-cfg
      -m ${numEvents}
      -n ${EVENTS_PER_JOB}
      --memory ${MEMORY}
      --time ${RUNTIME}
      -d ${sampleName}
      -p 0
      -o ${ODIR}/${recoKey}/${sampleType}/${sampleKey}
      --final-output ${FINAL_OUTPUT_DIR}
    )

    if [ "${sampleType}" = "DATA" ] && [ "${USE_JSON}" = true ]; then
      bdriver_args+=(--golden-json ${LUMI_JSON})
    fi

    bdriver "${bdriver_args[@]}" --submit

  done
}

for recoKey in "${recoKeys[@]}"; do
  python3 "${CMSSW_BASE}/src/Reco2Pico/PicoProducer/python/workflows/miniAOD_to_pico_cfg.py" \
    "tables=event,pfRhoStrip,vertices" \
    "skim=${SKIM}" \
    "dumpPython=tmp_cfg.py"

  run_samples DATA dataSamplesMap
  run_samples MC mcSamplesMap
done

unset recoKey recoKeys dataSamplesMap mcSamplesMap dataMaxEventsMap mcMaxEventsMap DEFAULT_NEVT ODIR

rm -rf tmp_cfg.py