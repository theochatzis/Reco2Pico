#!/bin/bash

python3 make_pf_rho_strip_plots.py /eos/user/t/tchatzis/reco2pico/CMSSW_15_0_4/src/Reco2Pico/PicoProducer/python/workflows/test_pico_zerobias.root \
  -o /eos/user/t/tchatzis/php-plots/PFNoiseStudy/ZeroBias/ \
  --root-output pf_rho_strip_plots.root \
  --prefix PFRhoStrip \
  --nvtx-branch PV_npvsGood \
  --rho-npv-npv-max 100 \
  --rho-npv-bins-npv 20 \
  --rho-npv-rho-max 60 \
  --rho-npv-bins-rho 15 \
  --max-events 1000 \
  --no-phi-plots \
#PV_npvsGood \
