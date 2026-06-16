#!/bin/bash

python3 make_pf_rho_strip_plots.py /eos/user/t/tchatzis/reco2pico/myPicosDirectory/LumiApplicationTest/default/ZeroBias2025G/test_data.root \
  -o /eos/user/t/tchatzis/php-plots/PFNoiseStudy/ZeroBias/ \
  --root-output pf_rho_strip_plots.root \
  --prefix PFRhoStrip \
  --nvtx-branch PV_npvsGood \
  --rho-npv-npv-max 100 \
  --rho-npv-bins-npv 20 \
  --rho-npv-rho-max 60 \
  --rho-npv-bins-rho 15 \
  --max-events 10000 \
  --no-phi-plots \
#PV_npvsGood \
