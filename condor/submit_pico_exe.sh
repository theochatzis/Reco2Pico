#!/bin/bash

BASE=${CMSSW_BASE}/src/Reco2Pico/

python3 submit_pico.py \
  --dataset ./datasets/SingleNeutrino_SmallSample.txt \
  --cfg PicoProducer/python/workflows/miniAOD_to_pico_cfg.py \
  --output-dir root://eosuser.cern.ch//eos/user/t/tchatzis/Reco2Pico/outputs/test_v1 \
  --tag test_v1 \
  --files-per-job 1 \
  --max-events -1 \
  --tables event,pfRhoStrip,vertices,jets,met,muons,electrons,pfcands \
  --global-tag auto:phase1_2024_realistic

# python3 submit_pico.py \
#   --dataset ./datasets/SingleNeutrino_SmallSample.txt \
#   --cfg ${BASE}/PicoProducer/python/workflows/miniAOD_to_pico_cfg.py \
#   --output-dir root://eosuser.cern.ch//eos/user/t/tchatzis/Reco2Pico/outputs/test_v1 \
#   --tag test_v1 \
#   --files-per-job 1 \
#   --max-events -1 \
#   --tables vertices,muons,electrons,jets,met,pfcands \
#   --global-tag auto:phase1_2024_realistic
