# AOD and RECO workflows

The two workflows intentionally have the same command-line interface.

## Common options

- `inputFiles`: input EDM file(s), required
- `secondaryInputFiles`: optional secondary input
- `output`: output Pico file
- `maxEvents`: standard VarParsing analysis option
- `skipEvents`: number of events to skip
- `tables`: comma-separated table groups
- `isMC=auto|true|false`: MC/data selection
- `globalTag`: explicit GlobalTag; empty means automatic Run-3 MC/data tag
- `pfCandMinPt`
- `trackMinPt`
- `pfClusterMinEnergy`
- `recHitMinAbsEnergy`
- `tpPileupMinPt`: pile-up `TrackingParticle`s below this pT are left out of the `TP` table (signal ones are all kept; default 1 GeV)
- `simJetSelection`: SimTracks clustered into `SimJet`: `leaves` (default), `boundary` or `primaries`
- `simJetMinPt`: pT threshold of the `SimJet` and `GenJet` tables (default 5 GeV)
- `tpAssociation`: track <-> TrackingParticle association written to `TrackTPLink`: `chi2` (default, `TrackAssociatorByChi2` on `mix:MergedTrackTruth`), `hits` (`quickTrackAssociatorByHits` on `prunedTrackingParticles`/`prunedDigiSimLinks`) or `none`
- `ecalCellThreshold`, `hcalCellThreshold`: `simcalo` per-cell thresholds on the summed sim deposit (default 0, none)
- `simPFChargedMaxAbsEta`, `simPFChargedMinPt`: tracker acceptance of the ideal PF charged candidates (2.5, 0.5 GeV)
- `dumpPython`: optional process dump

## AOD

```bash
cmsRun Reco2Pico/PicoProducer/python/workflows/AOD_to_pico_cfg.py \
  inputFiles=/store/.../AODSIM/...root \
  maxEvents=100 \
  tables=event,jets,muons,electrons,pfcands,tracks,vertices \
  output=pico_aod.root
```

Standard AOD does not contain the native PFCluster collections used by this
baseline, so `tables=pfclusters` is rejected.

RecHits are supported through reduced AOD collections:

```bash
tables=pfcands,tracks,vertices,rechits recHitMinAbsEnergy=0.1
```

## RECO

```bash
cmsRun Reco2Pico/PicoProducer/python/workflows/RECO_to_pico_cfg.py \
  inputFiles=/store/.../RECO/...root \
  maxEvents=100 \
  tables=event,pfcands,tracks,vertices,pfclusters \
  output=pico_reco.root
```

Add `rechits` only when needed because it can substantially increase event
size.

RECO MC additionally supports `pfblocks` (PF block elements and links),
`genparts` (`GenPart`, `GenJet`, `GenJetConst`), `sim` (`SimTrack`,
`SimVertex`, `SimJet`, `SimGenJetMatch`, `TP`, `TrackTPLink`), `simcalo`
(`SimCalo`, `SimPFCand`, `SimCaloJet`, `SimPFJet` and their GenJet matches) and
`recojets` (`PFCandTruth`, re-clustered `PFJet`/`PFJetCHS`/`PFJetPuppi` with
constituents and GenJet matches).
`sim` needs the TrackingParticles and `simcalo` the calorimeter sim hits in the
RECO file, which standard RECOSIM drops: produce the RECO with
`samples_workflows/run3_rawsim/recoCustomise.keepSimTruth`.

## Local files

For a local `file:...root` path the workflow cannot safely infer whether the
sample is MC or data. Specify it explicitly:

```bash
isMC=true
```

or

```bash
isMC=false
```
