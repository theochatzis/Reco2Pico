#!/bin/bash

NEVENTS=1000
cmsRun miniAOD_to_pico_cfg.py \
	inputFiles=/store/mc/Run3Winter24ReRECO2023MiniAOD/DoublePhoton_FlatPT-0p01to10_13p6TeV/MINIAODSIM/FlatPU0to120ZM_ZM2023HLT_EGMExtZM_ZeroMaterial2022ReRECO_140X_mcRun3_2023_realistic_v6-v2/130000/00165161-1f75-4b18-8461-b6f8721146e4.root \
	picoOutputFile=test_pico.root \
	maxEvents=${NEVENTS} \
	tables=vertices,jets,met,muons,electrons,pfcands

size=$(du -b test_pico.root | awk '{print $1}')
sizeInKB=$((size / 1024))
echo "size is $sizeInKB KB"
sizePerEvent=$((sizeInKB / ${NEVENTS}))
echo "size (KB) per event: $sizePerEvent"

python3 make_workbook.py
