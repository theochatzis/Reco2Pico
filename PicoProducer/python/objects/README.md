# `pat_from_reco_cff.py` code

`pat_from_reco_cff.py` converts:

```text
ak4PFJetsPuppi -> picoPatJets
gedGsfElectrons -> picoPatElectrons
muons -> picoPatMuons
```
so it is not a standard MiniAOD producer in this sense, but makes PAT collections that are compatible with the tables producers used from MiniAOD.

The resulting PAT collections can be passed to the same `jetTables`,
`electronTables`, and `muonTables` helpers already used in the MiniAOD backend.

For jets the adapter runs only standard AK4 PUPPI JEC factors so the existing
Jet table can use `jecFactor('Uncorrected')`. It does not run b tagging, PNet,
flavour matching, or tag-info production. (*ToDo*).

Muon PAT production keeps the standard selector recomputation needed by the
current Muon table but disables matching features.

Note:
Electron PAT production is deliberately minimal and does not run VID. The
AOD/RECO builder therefore calls `electronTables(..., includeIDs=False)`.
Electron VID can be added later as an optional enrichment layer without
changing the basic AOD/RECO architecture.
