# PicoAOD format

Reco2Pico writes NanoAOD-style flat tables to a ROOT file. The main analysis tree is expected to be `Events`.

Recommended naming follows NanoAOD conventions: `nMuon`, `Muon_pt`, `nJet`, `Jet_pt`, `MET_pt`.

Custom objects should use a clear prefix, e.g. `PicoHighPtMuon_pt`.
