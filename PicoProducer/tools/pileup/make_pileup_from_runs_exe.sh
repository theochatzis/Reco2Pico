#!/bin/bash

python3 make_pileup_from_runs.py \
    '/eos/user/t/tchatzis/reco2pico/myPicosDirectory/Run3Winter25ZTo2Mu/default/MC/ZTo2Mu/*.root' \
    -o pileup_Run3Winter25.root
