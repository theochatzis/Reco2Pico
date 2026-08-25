#!/bin/bash

python3 pfcand_charged_offset_rings_v2.py /eos/user/t/tchatzis/reco2pico/CMSSW_15_0_4/src/Reco2Pico/PicoProducer/python/workflows/test_pico_pfoffset.root \
    --label ChargedHadrons \
    --all-events \
    --event 0 \
    --min-nvtx 40 \
    --probe-mode charged \
    --energy-source corrected \
    --probe-pt-min 0.0 \
    --probe-pt-max 10.0 \
    --offset-pt-bins 0 0.25 0.5 0.75 1 1.5 2 3 5 \
    --eta-bins -3 -2.5 -1.5 0 1.5 2.5 3 \
    --output-dir ChargedOffsetStudy
