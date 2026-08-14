#!/bin/bash

python3 make_pf_rho_strip_plots_rdf.py /eos/user/t/tchatzis/reco2pico/CMSSW_15_0_4/src/Reco2Pico/PicoProducer/python/workflows/test_pico.root \
  -o /eos/user/t/tchatzis/php-plots/PFNoiseStudy/NeutrinoGunHF \
  --root-output pf_rho_strip_plots_rdf.root \
  --prefix PFRhoStrip \
  --nvtx-branch PV_npvsGood \
  --rho-npv-npv-max 80 \
  --rho-npv-bins-npv 20 \
  --rho-npv-rho-max 60 \
  --rho-npv-bins-rho 15 \
  --max-events 10000 \
  --no-phi-plots \
  --compile-cpp-helpers \
  --threads 0 \
  --progress

