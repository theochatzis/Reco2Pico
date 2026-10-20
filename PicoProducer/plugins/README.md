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

## `PicoPFBlockTableProducer`

Writes the particle-flow block structure (RECO only, `reco::PFBlock` is not in AOD).
The three tables answer different questions: `PFBlockElem` is the inventory of
elements, `PFBlockLink` the geometric connectivity PF found between them (the
algorithm's input), `PFCandElem` the elements each candidate finally used (the
algorithm's decision). See "PF block tables" in `../README.md` for the meaning
of the link distances and a usage example.

- `PFBlockElem` (instance `elements`): one row per `reco::PFBlockElement` of every
  block: `blockIdx`, `elemIdx`, `type` (TRACK, PS1, PS2, ECAL, HCAL, GSF, BREM,
  HFEM, HFHAD, SC, HO, HGCAL), the kinematics of the linked object, links to the
  Pico tables (`trackIdx` -> `Track`, `clusterTable`/`clusterIdx` ->
  `PFCluster<ECAL|HCAL|HO|HF|PS>`) and raw keys (`trackKey`, `clusterKey`,
  `gsfTrackKey`, `muonKey`, `superClusterKey`), track-type bits (displaced,
  conversion, V0, muon), the extrapolated ECAL-entrance position of tracks, the
  element time, and `candIdx`/`nCands` (which `PFCand` rows use the element).
- `PFBlockLink` (instance `links`): one row per stored element-element link of
  `PFBlock::linkData()`: `blockIdx`, `elem1`, `elem2`, `elemRow1`, `elemRow2`
  (rows of `PFBlockElem`), `distance`, `test`.
- `PFCandElem` (instance `candElements`): one row per
  `reco::PFCandidate::elementsInBlocks()` entry: `candIdx` (row of `PFCand`),
  `blockIdx`, `elemIdx`, `elemRow`, `type`.

Row indices follow the thresholds of the other tables (`candMinPt`,
`trackTableMinPt`, `clusterMinEnergy`); filtered objects give `-1` while the raw
keys are always filled.

## `PicoMixedTruthProducer`

Runs in the DIGI step of a classically mixed sample (`samples_workflows/run3_mix`),
after the mixing module, and turns its transient `CrossingFrame`s into
persistent collections: the SimTracks and SimVertices of the in-time pile-up
interactions (instance `pileup`, with their `EncodedEventId`, vertex indices
renumbered into the merged collection), their calorimeter sim hits
(`EcalHitsEB`, `EcalHitsEE`, `EcalHitsES`, `HcalHits`, hit by hit) and the
out-of-time deposits summed per cell and bunch crossing (`Oot...`, event id =
(bx, 0)) for the crossings in [`minBunch`, `maxBunch`], plus `nInTime`.

## `PicoCaloEntranceProducer`

Flags the calorimeter-entrance particles among the Geant4 `SimTrack`s of the
signal event (`PicoCaloEntrance.h`): the cut through the stored decay tree at
the tracker/calorimeter boundary, read off the boundary-crossing flag, the
production vertex (inside the tracker volume: `trackerMaxRadius` 123 cm,
`trackerMaxAbsZ` 293 cm) and the ownership of calorimeter sim hits, top-down
with an entrance ancestor always winning. Products parallel to the SimTracks:
`isEntrance`, `entranceOf` (the entrance particle every track belongs to,
itself or an ancestor, -1 before the boundary or lost in the tracker),
`ownsHits`, `reachesCalo`, and the two momenta of every track as an entrance
particle: `prodPx/prodPy/prodPz/prodE` (production, with the energy of its
entrance daughters taken out; knocked-out nucleons by kinetic energy) and
`px/py/pz/e` (at the calorimeter face: recorded at the crossing, else the
production one). Needs the `PCaloHit` collections (`PicoCaloSimHits.h`
parameters). Tracks are keyed by (event id, Geant4 id), so with `pileup=True`
it runs on the merged pile-up SimTracks of `PicoMixedTruthProducer` with the
pile-up hits (`pileupHits`). See "The calorimeter-entrance particles" in `../README.md`.

## `PicoSimTrackCandidateProducer`

Converts the Geant4 `SimTrack`s of the signal event into `reco::GenParticle`
candidates (plus `std::vector<int>` `simTrackIndex`) so that
`FastjetJetProducer` can cluster "sim jets". `selection`: `entrance` (the
calorimeter-entrance particles from `caloEntrance`, with `momentum` =
`production` (default, `SimJet`) or `boundary` (`SimBoundaryJet`); default),
`leaves` (the
terminal particles of the stored decay tree: no stored daughters, or
daughters carrying less than `maxDaughterEnergyFraction` = 0.5 of the energy,
production momentum), `boundary` (the same with the momentum at the crossing)
or `primaries` (generator particles only). Neutrinos are dropped.

## `PicoSimGenJetMatchProducer`

Tables `SimGenJetMatch` (instance `matches`) and, with `writeGenConstituents`,
`GenJetConst` (instance `genConstituents`). Any jet collection whose
constituents carry a SimTrack index can be matched (the `simcalo` group clones
it for `SimCaloJet` and `SimPFJet`); with `constituentShares` set to the
`PicoSimCaloCandidateProducer` label, a constituent is instead split between
several SimTracks with the per-cell shares (`SimCaloCellJet`; `constituentSharesPrefix` selects the share products, e.g. `cellPUShare` for the cells with pile-up). Matches sim jets to gen jets through the Geant4 ancestry
of the sim-jet constituents (every SimTrack descends from one generator
primary, every generator particle sits in at most one gen jet): per pair the
shared energy, `simFraction` (share of the sim jet energy coming from the gen
jet), `genFraction` (share of the gen jet energy whose descendants were
clustered into the sim jet), `nShared`, `ptRatio`, `dR` and the best-pair
flags. The gen jets must be clustered in the same job (the stored
`ak4GenJetsNoNu` have no constituent references); `genParticleTables` does
that. See "Sim jets and the SimJet to GenJet matching" in `../README.md`.

## `PicoSimTrackTableProducer`

Tables `SimTrack` (instance `tracks`) and `SimVertex` (instance `vertices`) from
`g4SimHits`: kinematics at production, production vertex, `vertIdx`,
`parentIdx`, `genPartIdx` (row of the pruned `GenPart` table, matched through
the HepMC barcode), `isPrimary`, `isOrphan` (not a primary and no stored
parent: Geant4 dropped the ancestor), `nDaughters`, `isLeaf`, boundary-crossing and
tracker-surface momenta (the tracker-surface ones are never filled by
CMSSW_15_0_X and read 0), `simJetIdx` (row of the `SimJet` table the track was
clustered into), the calorimeter-entrance flags `isEntrance`, `entranceIdx`,
`ownsCaloHits` with `entrancePt/E` and `facePt/E` (from `caloEntrance`) and
the Geant4 ids; vertices carry position, time, `parentIdx`,
`nDaughters` and the Geant4 process type.

## `PicoSimCaloCandidateProducer`

Sums the calorimeter sim hits (`PCaloHit`, ECAL/ES/HCAL) per
calorimeter-entrance particle (the Geant4 id stored in the hit, mapped to its
entrance particle with `entranceOf` from `caloEntrance`) into massless
`reco::GenParticle` candidates (`calo`: energy = deposit, direction =
energy-weighted cell direction) with parallel vectors of the per-subdetector
energies and `caloNOwners`; writes the cells themselves (`cells`: energy = cell
total, direction = cell centre, with `cellSub`, `cellDetId` and the per-cell
shares `cellShareBegin`/`cellShareTrack`/`cellShareEnergy` for the matching);
and builds the ideal PF candidates (`pf`: production momentum for charged
entrance particles born inside the tracker volume, inside the acceptance and
above `chargedMinPt`; deposit otherwise). With `pileupSimTracks` /
`pileupSimVertices` / `pileupCaloEntrance` / `pileupHits` set (pile-up truth)
it adds the pile-up deposit of every cell (`cellPUEnergy`, `cellOotEnergy`,
`cellNPU`), the cells with signal + in-time pile-up (`cellsPU`, with the
signal shares `cellPUShare*`), the deposits of the pile-up entrance particles
(`caloPU`) and the ideal PF with pile-up (`pfPU`, kinds 11/12/13 for the
pile-up entries) and after a perfect charged-hadron subtraction (`pfPUCHS`). `verbose` (untracked)
prints the HCAL relabelling and conversion bookkeeping per event. HCAL hits are
relabelled with `HcalHitRelabeller` and scaled with the digitiser sampling
factors (`hbSamplingFactors`, `heSamplingFactors`, `hoSamplingFactors`,
`hf1SamplingFactor`, `hf2SamplingFactor`); per-cell thresholds apply to the
cell total over all particles. Needs `CaloGeometry` and `HcalDDDRecConstants`.

## `PicoSimCaloTableProducer`

Tables `SimCalo` (instance `calo`), `SimCaloCell` (instance `cells`, with
`writeCells`) and `SimPFCand` (instance `pf`) from the products above, with
the per-subdetector energies, the single-particle `response` (deposit / energy
at the calorimeter entrance) and the rows of the
`SimCaloJet`/`SimCaloCellJet`/`SimPFJet` the candidates were clustered into;
`pileup` adds the `puEnergy`/`ootEnergy`/`nPU` columns of the cells. See "Per-particle
calorimeter deposits" in `../README.md`.

## `PicoPFCandTruthProducer`

Tables `PFCandTruth` (instance `candidates`, one row per `PFCand` row:
`signalFraction`, dominant `simTrackIdx` and `simTrackFraction`, `method`) and
`PFCandSim` (instance `shares`), plus the flat share vectors read by the jet
matching. Charged candidates are attributed through the track association,
the others through their cluster cells and the sim-hit shares of
`PicoCaloSimHits.h` (shared with the sim-calo producer), capped by the sim
energy of the cell. Needs the rechit collections of RECO.

With `pileupHits` set (pile-up truth of a classically mixed sample) the cap of
the cell attribution is the in-time sim energy of the cell, signal plus
pile-up, the pile-up share goes to `puFraction`, and a track whose
TrackingParticle belongs to another interaction is pile-up entirely.

## `PicoRecoJetGenMatchProducer`

Tables `<name>GenMatch` (instance `matches`) and `<name>Const` (instance
`constituents`) for any `reco::Jet` collection whose constituents resolve to
`particleFlow` (directly, by object address for FwdPtr inputs, or through
`sourceCandidatePtr`); optional puppi `weights`. Same scores as
`PicoSimGenJetMatchProducer` through the candidate attribution and the Geant4
ancestry (`PicoSimAncestry.h`), plus `signalPtRatio`.

## `PicoTrackingParticleTableProducer`

Tables `TP` (instance `particles`) and `TrackTPLink` (instance `links`).
`TP` rows are the `TrackingParticle`s of `mix:MergedTrackTruth` (signal and
pile-up, charged, pT > 0.1 GeV at mixing; `pileupMinPt` thins the pile-up ones):
kinematics, vertex, `bx`/`event`/`isSignal`, tracker hits and layers,
`genPartIdx`, `simTrackIdx`, `parentIdx` and the first decay vertex.
`TrackTPLink` holds the `reco::RecoToSimCollection`/`SimToRecoCollection`
entries of `association` as (`trackIdx`, `tpIdx`, `recoToSimQuality`,
`simToRecoQuality`, `hasRecoToSim`, `hasSimToReco`); `qualityDoc` describes the
quality (shared-hit fraction for the hit associator, -chi2 for
`TrackAssociatorByChi2`). The association may have been computed on another
`TrackingParticle` collection (the pruned one of premixed samples); its entries
are matched to `TP` rows through (event id, Geant4 track id).

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
