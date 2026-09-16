# Native AOD/RECO Pico table producers

These plugins write reconstruction-level CMSSW objects directly to
`nanoaod::FlatTable`. They are intentionally independent of PAT.

## `PicoRecoPFCandidateTableProducer`

**Input**

- `src`: `reco::PFCandidateCollection`, default `particleFlow`
- `tracks`: `reco::TrackCollection`, default `generalTracks`
- `vertices`: `reco::VertexCollection`, default `offlinePrimaryVertices`
- `minPt`: PFCandidate pT threshold
- `trackTableMinPt`: threshold used by the separate Track table; required to
  remap `TrackRef::key()` to the filtered Pico Track row

**Table**: `PFCand`

Important columns:

- kinematics: `pt`, `eta`, `phi`, `mass`, `charge`
- identity: `pdgId`, `particleId`
- candidate vertex: `vx`, `vy`, `vz`
- calorimeter information: `ecalEnergy`, `rawEcalEnergy`, `hcalEnergy`,
  `rawHcalEnergy`, `hoEnergy`, `rawHoEnergy`
- timing: `time`, `timeError`
- tracking link: `hasTrack`, `trackIdx`
- selected duplicated track diagnostics: `trkAlgo`, `trkOriginalAlgo`,
  `trkQualityMask`, `trkDxy`, `trkDz`, errors and hit counts

`trackIdx = -1` means there is no usable row in the configured Track table. It
can happen because there is no TrackRef, the TrackRef points to another track
collection, or the associated track was removed by `trackTableMinPt`.

## `PicoTrackTableProducer`

**Input**

- `src`: `reco::TrackCollection`, default `generalTracks`
- `vertices`: `reco::VertexCollection`, default `offlinePrimaryVertices`
- `minPt`: Track table pT threshold

**Table**: `Track`

Columns include:

- `pt`, `eta`, `phi`, `p`, `ptErr`, `charge`
- `vx`, `vy`, `vz`
- `dxy`, `dz`, `dxyErr`, `dzErr`
- `chi2`, `ndof`, `normalizedChi2`
- `algo`, `originalAlgo`, `algoMask`
- `qualityMask`, `highPurity`, `stopReason`
- `nValidHits`, `nLostHits`, `nPixelHits`, `nStripHits`
- `nTrackerLayers`, `nPixelLayers`
- `pvIdx`, `pvWeight`

`dxy` and `dz` are computed relative to the first configured vertex when one is
present. `pvIdx` is instead determined from the vertex where the track has the
largest fit weight.

## `PicoRecoVertexTableProducer`

**Input**

- `src`: `reco::VertexCollection`, default `offlinePrimaryVertices`

**Table**: `Vertex`

Columns:

- position/errors: `x`, `y`, `z`, `xErr`, `yErr`, `zErr`
- fit: `chi2`, `ndof`, `normalizedChi2`
- content: `nTracks`, `sumPt2`
- flags: `isValid`, `isFake`

Unlike the existing MiniAOD PV-only table, this table stores all configured
`reco::Vertex` objects so other low-level tables can refer to them by index.

## `PicoPFClusterTableProducer`

**Input**

- `src`: a `reco::PFClusterCollection`
- `minEnergy`: cluster energy threshold

One instance is normally created for each of:

- `particleFlowClusterECAL` -> `PFClusterECAL`
- `particleFlowClusterHCAL` -> `PFClusterHCAL`
- `particleFlowClusterHO` -> `PFClusterHO`
- `particleFlowClusterHF` -> `PFClusterHF`
- `particleFlowClusterPS` -> `PFClusterPS`

Columns:

- `energy`, `pt`, `eta`, `phi`
- centroid: `x`, `y`, `z`
- `layer`, `depth`
- `time`, `timeError`
- `nHits`, `seedRawId`, `algo`, `flags`

Standard RECO keeps these PFCluster collections. Standard AOD does not, so the
normal AOD workflow rejects the `pfclusters` group.

## Calorimeter RecHit producers

`PicoCaloRecHitTableProducers.cc` registers:

- `PicoEcalRecHitTableProducer`
- `PicoHBHERecHitTableProducer`
- `PicoHFRecHitTableProducer`
- `PicoHORecHitTableProducer`

All accept `minAbsEnergy`, which is applied as `abs(energy) >= threshold`.

### ECAL tables

Tables: `EBRecHit`, `EERecHit`.

Columns include `rawId`, subdetector, energy/time/error, chi2, energy error,
flags, and EB/EE crystal coordinates.

### HCAL tables

Tables: `HBHERecHit`, `HFRecHit`, `HORecHit`.

Columns include `rawId`, subdetector, `ieta`, `iphi`, `depth`, `energy`, and
`time`.

AOD uses `reducedHcalRecHits:*`; RECO uses `hbhereco`, `hfreco`, and `horeco`.

## Adding another producer

A producer only needs to:

1. consume the native EDM collection;
2. build vectors for the desired columns;
3. create `nanoaod::FlatTable`;
4. call `addColumn`;
5. `event.put()` the table;
6. register with `DEFINE_FWK_MODULE`;
7. add required packages to `plugins/BuildFile.xml`;
8. expose it through a small `python/tables/*_cff.py` helper.
