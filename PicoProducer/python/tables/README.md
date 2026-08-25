# Tables

Here all the producers that make the tables of Pico format are stored.
There are two main categories.

- The standard `cff` files of objetcs that are used from any tier level e.g. `electrons_cff`. These can have standard producers existing in CMSSW.

- The ones which have `reco_cff` which are made to work only with `RECO` objects using native producers of the Reco2Pico framework.

# Low level helpers

The low-level table helpers are deliberately small wrappers around the native
C++ producers.

- `pfcands_reco_cff.py` -> `PFCand`
- `tracks_cff.py` -> `Track`
- `vertices_reco_cff.py` -> `Vertex`
- `pfclusters_cff.py` -> PFCluster tables
- `rechits_cff.py` -> calorimeter RecHit tables
- `reco_lowlevel_cff.py` -> can help to wrap all producers together in one task

Typical direct use can be:

```python
from Reco2Pico.PicoProducer.tables.reco_lowlevel_cff import recoLowLevelTables

recoLowLevelTables(
    process,
    inputTier="RECO",
    tables=("pfcands", "tracks", "vertices", "pfclusters", "rechits"),
    pfCandMinPt=0.2,
    trackMinPt=0.5,
    pfClusterMinEnergy=0.2,
    recHitMinAbsEnergy=0.1,
)

process.p.associate(process.picoRecoLowLevelTask)
```

In the supplied AOD/RECO workflows this task is assembled automatically by
`buildRecoPicoSequence`.