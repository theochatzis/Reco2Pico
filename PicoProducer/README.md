# Pico production

## Chained batch processing

Use `bdriver -c first_cfg.py --steps steps.json` to run configurations in order.
The JSON lists subsequent steps; paths are relative to the JSON file:

```json
[
  {
    "cfg": "python/workflows/RECO_to_pico_cfg.py",
    "args": ["isMC=true", "era=Run3_2024", "globalTag=133X_mcRun3_2024_realistic_v10"]
  }
]
```

An optional `"cmssw": "/absolute/path/to/CMSSW_X_Y_Z"` selects a release area
for that step. Otherwise it uses the active `CMSSW_BASE` from job preparation,
even if the preceding step overrides its release. Areas must support the
submission `SCRAM_ARCH` and be accessible on the workers.

Each subsequent configuration must accept `inputFiles`, `secondaryInputFiles`,
`output`, `maxEvents`, and `skipEvents`. The driver owns these arguments.
Only the first step receives the event slice; later steps process its output
from the beginning. Additional command-line configuration arguments apply
only to the first step; use each JSON entry's `args` for later steps.

```bash
bdriver -c reco_cfg.py --customize-cfg --steps steps.json \
  -d /PRIMARY/PROCESSING/GEN-SIM-RAW -p 0 \
  -o jobs/raw_to_pico -fo root://hip-cms-se.csc.fi//store/user/USERNAME/picos \
  -n 100 --cpus 1 --memory 8G --disk-mb 20000 --time 02:00:00
```

Generate and validate `reco_cfg.py` with `cmsDriver.py` in the intended
reconstruction release first. `--customize-cfg` adapts the first configuration;
a generated configuration should have one output module. Reconstruction
settings and downstream conditions must match the sample and chosen releases.

The last output is always transferred as `out_N.root`. Add
`--save-intermediates` to also transfer `step1_out_N.root`, `step2_out_N.root`,
etc. Each intermediate is transferred or removed after its consumer succeeds.
The job is marked complete only after all steps and required transfers succeed.
Failed jobs are not resumed from saved intermediate files.

The resource values above are starting points for a small pilot, not measured
requirements. Request memory for the largest step, runtime for the complete
chain, and scratch space for adjacent outputs plus processing overhead.
CPU requests do not automatically configure CMSSW threads.
For HIP, use an explicit writable XRootD destination; bare `/store/` output
paths currently target CERN. The destination directory must already exist
when using a `root://` URL.

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
