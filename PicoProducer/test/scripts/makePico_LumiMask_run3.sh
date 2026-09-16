#!/bin/bash

set -e

if [ $# -ne 1 ]; then
  printf "\n%s\n\n" ">> argument missing - specify path to local condor working/output directory"
  exit 1
fi

NEVT=10000
EVENTS_PER_JOB=2500
MEMORY=2G
RUNTIME=02:00:00

OUTPUT_DIR_EOS=/eos/user/${USER:0:1}/${USER}/reco2pico/myPicosDirectory/
ODIR=${1}

LUMI_JSON=/eos/user/c/cmsdqm/www/CAF/certification/Collisions25/Cert_Collisions2025_391658_398903_Golden.json

declare -A samplesMap

# Replace/add samples as needed. The value can be a DAS dataset or a bdriver dataset.json dump.
# samplesMap["NeutrinoGun"]="/SingleNeutrino_Par-E-10_gun/RunIII2024Summer24MiniAODv6-FlatPU0to120_150X_mcRun3_2024_realistic_v2-v2/MINIAODSIM"
samplesMap["ZeroBias2025G"]="/ZeroBias/Run2025G-PromptReco-v1/MINIAOD"

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
      [Nn]* ) echo "Exiting..."; unset recoKey recoKeys samplesMap NEVT ODIR; exit 1;;
      * ) echo "Please answer with y/n."; exit 1;;
  esac
fi

for recoKey in "${recoKeys[@]}"; do
  python3 "${CMSSW_BASE}/src/Reco2Pico/PicoProducer/python/workflows/miniAOD_to_pico_cfg.py" \
    "tables=event,pfRhoStrip,vertices" \
    "lumis=${LUMI_JSON}" \
    "dumpPython=tmp_cfg.py"
  CFG=${CMSSW_BASE}/src/Reco2Pico/PicoProducer/python/workflows/miniAOD_to_pico_cfg.py

  for sampleKey in ${!samplesMap[@]}; do
    sampleName=${samplesMap[${sampleKey}]}
    numEvents=${NEVT}
    FINAL_OUTPUT_DIR=${OUTPUT_DIR_EOS}/${ODIR}/${recoKey}/${sampleKey}

    if [ -d ${FINAL_OUTPUT_DIR} ]; then rm -rf ${OUTPUT_DIR_EOS}/${ODIR}/${recoKey}/; fi
    mkdir -p ${FINAL_OUTPUT_DIR}

    if [ -d ${ODIR}/${recoKey}/${sampleKey} ]; then rm -rf ${ODIR}/${recoKey}/${sampleKey}; fi
    # Note: If your cfg does not support the skipEvents and output etc the way it should
    # will be problematic to take the output run on the data you want and to recognize any cfg option
    # For this reason use --customize-cfg in such cases and make sure its good for your script.
    bdriver -c tmp_cfg.py --customize-cfg \
      -m ${numEvents} -n ${EVENTS_PER_JOB} --memory ${MEMORY} --time ${RUNTIME} \
      -d ${sampleName} -p 0 -o ${ODIR}/${recoKey}/${sampleKey} \
      --final-output ${FINAL_OUTPUT_DIR} \
      --golden-json ${LUMI_JSON} \
      --submit 
# --customise-commands \
# '# output [NanoAOD/PicoAOD]' \
# "if hasattr(process, 'nanoAODOutput'):" \
# '  process.nanoAODOutput.fileName = opts.outputFile' \
# "if hasattr(process, 'TFileService'):" \
# '  process.TFileService.fileName = opts.outputFile'
  done
  unset sampleKey numEvents sampleName
done

unset recoKey recoKeys samplesMap NEVT ODIR

rm -rf tmp_cfg.py