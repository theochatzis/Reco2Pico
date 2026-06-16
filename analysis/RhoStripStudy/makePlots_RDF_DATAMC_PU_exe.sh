#!/bin/bash

python3 make_pf_rho_strip_plots_rdf_DATAMC_PU.py /eos/user/t/tchatzis/reco2pico/myPicosDirectory/ZJetDataMCBigStats/default/DATA/dimuon.root \
  --mc-input /eos/user/t/tchatzis/reco2pico/myPicosDirectory/ZJetDataMCBigStats/default/MC/dimuon.root \
  --mc-pu-reweight \
  --pu-reweight-max-npv 100 \
  -o /eos/user/t/tchatzis/php-plots/PFNoiseStudy/dy/pfpuppiDataMC \
  --root-output pf_rho_strip_plots_datamc_purw.root \
  --prefix PFPuppiRhoStrip \
  --nvtx-branch PV_npvsGood \
  --rho-npv-npv-max 60 \
  --rho-npv-bins-npv 20 \
  --rho-npv-rho-max 60 \
  --rho-npv-bins-rho 15 \
  --max-events 100000 \
  --no-phi-plots \
  --compile-cpp-helpers \
  --threads 0 \
  --progress

