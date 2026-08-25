#!/bin/bash
python3 pfcand_offset_spectra.py \
    /eos/user/t/tchatzis/reco2pico/CMSSW_15_0_4/src/Reco2Pico/PicoProducer/python/workflows/test_pico_pfoffset.root \
    --labels ZeroBias \
    --event 0 \
    --eta-bins -5.2 -3.0 -2.5 -1.5 0 1.5 2.5 3.0 5.2 \
    --pt-max 10 \
    --min-nvtx 40 \
    --output-dir pfcand_offset_study
