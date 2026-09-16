#!/bin/bash

python3 pfcand_charged_offset_rings_direct.py \
    /eos/user/t/tchatzis/reco2pico/CMSSW_15_0_4/src/Reco2Pico/PicoProducer/python/workflows/test_pico_pfoffset.root \
    --label ChargedHadrons \
    --event 0 \
    --min-nvtx 40 \
    --eta-bins -3.0 -2.5 -1.5 0 1.5 2.5 3.0 \
    --output-dir ChargedOffset