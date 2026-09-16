#!/bin/bash

FINALROOT_NAME=test_pico_pfoffset_nojec.root
NEVENTS=1000
JECS_DIR=$CMSSW_BASE/src/Reco2Pico/PicoProducer/python/workflows/jecs/
cmsRun miniAOD_to_pico_cfg.py \
	inputFiles=/store/mc/RunIII2024Summer24MiniAODv6/SingleNeutrino_Par-E-10_gun/MINIAODSIM/FlatPU0to120_150X_mcRun3_2024_realistic_v2-v2/120000/7324e590-b0e6-4c31-90f7-b24c9a13d2a1.root \
	reApplyJEC=False \
	rerunPUPPI=False \
    jecDBFile=${JECS_DIR}/Winter25Prompt25_V3_MC.db \
	jecDBTag=JetCorrectorParametersCollection_Winter25Prompt25_V3_MC_AK4PFPuppi \
	output=test_pico.root \
	maxEvents=${NEVENTS} \
	skim="" \
	dumpPython=test_mini_cfg.py \
	tables=event,pfRhoStrip,vertices,jets,met,muons,electrons,pfcands,genJets
	#tables=event,pfRhoStrip,vertices,jets,met,muons,electrons,pfcands,genJets #\
	#lumis=/eos/user/c/cmsdqm/www/CAF/certification/Collisions25/Cert_Collisions2025_391658_398903_Golden.json

size=$(du -b test_pico.root | awk '{print $1}')
sizeInKB=$((size / 1024))
echo "size is $sizeInKB KB"
sizePerEvent=$((sizeInKB / ${NEVENTS}))
echo "size (KB) per event: $sizePerEvent"

python3 make_workbook.py

# mv test_pico.root ${FINALROOT_NAME}

# Possible samples for inputs:
#/store/mc/Run3Winter25MiniAOD/ZTo2Mu_Bin-M-50to120_TuneCP5_13p6TeV_powheg-pythia8/MINIAODSIM/142X_mcRun3_2025_realistic_v7-v2/120000/e76d5a6d-41a4-4e61-b119-245a3c7d4ded.root
#/store/data/Run2025G/Muon0/MINIAOD/PromptReco-v1/000/397/954/00000/81f09d25-b38c-4bc7-b627-997f304d4c18.root
#inputFiles=/store/mc/Run3Winter25MiniAOD/ZTo2Mu_Bin-M-50to120_TuneCP5_13p6TeV_powheg-pythia8/MINIAODSIM/142X_mcRun3_2025_realistic_v7-v2/120000/04307e36-9706-4355-9854-20251ba5ed25.root
#/store/mc/Run3Winter26MiniAODv6/QCD_Bin-PT-15to7000_Par-PT-flat2022_TuneCP5_13p6TeV_pythia8/MINIAODSIM/150X_mcRun3_2026_realistic_v4-v4/2550000/1a5a39e1-eea4-4f2b-8ebd-04c72d48f36b.root
#root://hip-cms-se.csc.fi//store/user/nbinnorj/RAWToPFNANO_2026_v0p1/CRABOUTPUT/QCD_Bin-PT-15to7000_Par-PT-flat2022_TuneCP5_13p6TeV_pythia8/Run3Winter26MiniAODv6_NoPFHCEta2p5To3p0v2_RAWToPFNANO_2026_v0p1/260422_154703/0000/MINIAODSIM_190.root
#inputFiles=/store/data/Run2025G/ZeroBias/MINIAOD/PromptReco-v1/000/398/011/00000/0db8a2f5-d145-4f83-b8f9-480bbb77f38d.root
#inputFiles=/store/mc/RunIII2024Summer24MiniAODv6/SingleNeutrino_Par-E-10_gun/MINIAODSIM/FlatPU0to120_150X_mcRun3_2024_realistic_v2-v2/120000/7324e590-b0e6-4c31-90f7-b24c9a13d2a1.root
