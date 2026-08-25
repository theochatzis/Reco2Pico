# Reco2Pico 
For MiniAOD using FlatTables producers to convert the PAT collections directly to Picos. It is exactly the same as Nano just with reduced info and possibiliy to add more info of course.

AOD and RECO can be converted directly
into the same Pico/FlatTable style used by the MiniAOD workflow.

Separates high-level and low-level objects:

```text
MiniAOD PAT objects ---------------------------> existing Pico tables

AOD/RECO reco objects e.g. jets/muons/electrons
            |
            +--> minimal PAT compatibility ----> existing Pico tables

AOD/RECO native reconstruction objects
            |
            +--> dedicated native producers ---> Pico FlatTables
```

The PAT compatibility layer is intentionally small. It does **not** attempt to
reproduce MiniAOD and does not run PNet, b tagging, flavour matching, trigger
matching, mini-isolation, or electron VID.

## Files
- `python/workflows/` contains the config files for the different tiers to pico NTuples production.
- Table configurations under `python/tables/`

- `python/tables/event_cff.py`: adds configurable PU/PV sources so AOD/RECO MC
  uses `addPileupInfo` and `offlinePrimaryVertices`, while MiniAOD defaults are
  unchanged.
- `python/tables/electrons_cff.py`: adds `includeIDs=True`. MiniAOD behaviour is
  unchanged; AOD/RECO can use the same table builder with `includeIDs=False`
  because the minimal PAT layer does not run VID.

## Supported table groups

| group | AOD | RECO | source / notes |
|---|---:|---:|---|
| `event` | yes | yes | rho; PU table on MC |
| `muons` | yes | yes | `muons -> picoPatMuons -> Muon` |
| `electrons` | yes | yes | `gedGsfElectrons -> picoPatElectrons -> Electron` |
| `jets` | yes | yes | `ak4PFJetsPuppi -> picoPatJets -> Jet` |
| `pfcands` | yes | yes | native `particleFlow` |
| `tracks` | yes | yes | native `generalTracks` |
| `vertices` | yes | yes | native `offlinePrimaryVertices` |
| `pfclusters` | no* | yes | native PFCluster collections; standard AOD does not keep them |
| `rechits` | yes | yes | reduced AOD RecHits, fuller RECO RecHits |

`*` A custom AOD that explicitly keeps PFCluster collections can be supported
by changing the guard/source configuration.

## Installation into the current repository

Copy the supplied files into the matching paths of your existing checkout.
The supplied `plugins/BuildFile.xml` is the current Reco2Pico BuildFile with the
extra DataFormats dependencies merged in.

## MiniAOD Example

```bash
cmsRun Reco2Pico/PicoProducer/python/workflows/miniAOD_to_pico_cfg.py \
  inputFiles=/store/.../MINIAODSIM/...root \
  maxEvents=100 \
  output=pico_aod.root \
  tables=event,muons,electrons,jets,pfcands,vertices
```

## AOD example

```bash
cmsRun Reco2Pico/PicoProducer/python/workflows/AOD_to_pico_cfg.py \
  inputFiles=/store/.../AODSIM/...root \
  maxEvents=100 \
  output=pico_aod.root \
  tables=event,muons,electrons,jets,pfcands,tracks,vertices
```

For data you can normally let `isMC=auto` infer the type from `/store/data/`.
For local files use an explicit `isMC=true` or `isMC=false`.

## RECO example

```bash
cmsRun Reco2Pico/PicoProducer/python/workflows/RECO_to_pico_cfg.py \
  inputFiles=/store/.../RECO/...root \
  maxEvents=100 \
  output=pico_reco.root \
  tables=event,pfcands,tracks,vertices,pfclusters
```

or e.g. to inspect calorimeter RecHits:

```bash
cmsRun Reco2Pico/PicoProducer/python/workflows/RECO_to_pico_cfg.py \
  inputFiles=/store/.../RECO/...root \
  maxEvents=10 \
  output=pico_rechits.root \
  tables=pfcands,tracks,vertices,pfclusters,rechits \
  recHitMinAbsEnergy=0.1
```

Note that RecHit tables can be large.

## Filtering and indices conventions

`PFCand_trackIdx` points to a row of the Pico `Track` table, not blindly to the
original `reco::TrackRef::key()`. The producer remaps the index when
`trackMinPt` is non-zero.

Example:

```bash
trackMinPt=0.5 pfCandMinPt=0.2
```

still gives a valid `PFCand_trackIdx` for tracks retained in the Track table;
tracks removed by the threshold receive `trackIdx = -1`.

`Track_pvIdx` points to the row of the native `Vertex` table with the largest
vertex-fit weight for that track.

