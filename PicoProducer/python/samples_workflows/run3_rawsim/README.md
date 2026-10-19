# Run-3 GEN-SIM-RAW -> Pico chain

Re-reconstruct a centrally produced Run-3 GEN-SIM-RAW sample and write a Pico
with the full particle-flow structure and the simulation truth, with Reco2Pico's
`bdriver` step chaining on HTCondor:

    step1  RAW2DIGI,L1Reco,RECO,RECOSIM   (campaign recipe + sim truth kept)  -> GEN-SIM-RECO
    step2  ntuple definition reco-pico     (RECO_to_pico_cfg.py)              -> Pico

Only the Pico is staged out (`bdriver --save-intermediates` keeps the RECO).
The generic machinery lives in `../common/` (see its README); this directory
holds only what is specific to processing a DAS dataset.

## Why GEN-SIM-RAW

* `pfblocks`: PF blocks, their elements (tracks, clusters, GSF, brems, super
  clusters) and the stored element-element links, plus the candidate -> element
  map. Blocks are in RECO but not in AOD, and re-running RECO gives them with
  whatever PF configuration you want.
* `sim`: the Geant4 `SimTrack`/`SimVertex` tree of the signal event (decays in
  flight, conversions) with `SimJet`s clustered from it, and the
  `TrackingParticle`s with the hit-based track <-> TP association. RECOSIM drops
  the TrackingParticles and the DigiSimLinks; only GEN-SIM-RAW has them, and
  `recoCustomise.keepSimTruth` carries them through step 1.

## Default sample

`/DYto2Mu-4Jets_Bin-MLL-50_TuneCP5_13p6TeV_madgraphMLM-pythia8/Run3Winter26Digi-150X_mcRun3_2026_realistic_v4-v2/GEN-SIM-RAW`
(23.3M events, 48 TB in 12.5k files of ~1900 events, complete on `T1_US_FNAL_Disk`,
so no Rucio rule or tape recall is needed). Its Reco step on McM
(`JME-Run3Winter26Reco-00027`, CMSSW_15_0_18) is

```
cmsDriver.py --era Run3_2025 --step RAW2DIGI,L1Reco,RECO,RECOSIM --geometry DB:Extended \
  --conditions 150X_mcRun3_2026_realistic_v4 --datatier GEN-SIM-RECO,AODSIM --eventcontent RECOSIM,AODSIM --mc
```

which `make_rawsim_cfgs.sh` reproduces (`ERA`, `GT`, `GEOM`, `RECOSTEP`
override it for another campaign; look the Reco request up on McM, e.g.
`https://cms-pdmv-prod.web.cern.ch/mcm/public/restapi/requests/get_setup/<PREPID>`).

Truth content of the premixed Winter26 RAW, as found on the local test:

* `mix:MergedTrackTruth` holds the TrackingParticles of the **signal event only**
  (charged, pT > 0.1 GeV; ~500 per event); pile-up TPs are not merged by the
  premixing. `tpPileupMinPt` therefore has no effect on this sample.
* The pruned copy (`prunedTrackingParticles` + `prunedDigiSimLinks`) is tiny:
  the pruner keeps the charged status-1 descendants of b/c hadrons only, so a
  hit-based association on it links a handful of tracks per event.
* The `sim` group therefore defaults to `tpAssociation=chi2`
  (`TrackAssociatorByChi2`, track parameters vs. TP momentum and vertex,
  chi2 < 25, quality = -chi2) on the full collection: on the test ~75% of the
  TPs with pT > 1 GeV, |eta| < 2.4 and >= 5 tracker layers get a track.
  `tpAssociation=hits` switches to the hit association on the pruned
  collection, `none` writes no links.
* The HLT scouting products of the 15_0_18 RAW are dropped on input by
  `recoCustomise.keepSimTruth` (their classes do not exist in 15_0_4).

## Files

| file | purpose |
|------|---------|
| `make_rawsim_cfgs.sh [OUTDIR]` | `cmsDriver.py --no_exec` of step 1 with `--customise recoCustomise.keepSimTruth`, copy of the ntuple cfg, VarParsing tail appended to step 1. Env: `ERA GT GEOM RECOSTEP NTUPLE PICO_TABLES`. Output: `step1_RECO_cfg.py ntuple_reco-pico_cfg.py`. |
| `recoCustomise.py` | `keepSimTruth(process)`: adds the TrackingParticles, pruned TPs/DigiSimLinks, calorimeter sim hits, gen particles/jets and pile-up info to the RECO output, and drops the HLT scouting products on input. |
| `rawsim_varparsing_tail.py` | tail appended to step 1 (`apply_varparsing`, see `../common/varparsing.py`). |
| `steps_rawsim_chain.json` | sample steps manifest: empty (step 1 is the only sample step); the ntuple step is appended at submission time with its `NTUPLE_ARGS`. |
| `submit_rawsim_bdriver.sh [--submit] [--dry-run]` | composes `datasets/steps_<TAG>_<NTUPLE>.json` and calls `../common/submit_bdriver_chain.sh` with the DAS dataset. |
| `run_rawsim_local.sh [NEVENTS] [INPUT]` | local test: cfgs in `local_test/cfgs`, step 1 on `NEVENTS` events of one file (xrootd), step 2, table inspection, variable documentation `local_test/doc_reco-pico.html`. |

Generated, not versioned: `cfgs/`, `datasets/`, `jobs/`, `local_test/`.

## Local test

```bash
cmsenv; voms-proxy-init --voms cms
./run_rawsim_local.sh 5
```

Reads 5 events of the default file through `root://cms-xrd-global.cern.ch`,
runs RECO and the Pico step, then prints `OK`/`EMPTY`/`MISSING` for the tables of
`NTUPLE_INSPECT` and writes `local_test/doc_reco-pico.html`. Another file or
event count: `./run_rawsim_local.sh 20 root://...`.

Result of the test in CMSSW_15_0_4 (5 events, 16 Oct 2026): RECO takes about
10 s per event (single thread) after a ~3 min start-up and writes ~5 MB per
event of RECOSIM with the sim truth; every table of `NTUPLE_INSPECT` is filled. Per event:
~2700 PF candidates, ~2100 tracks, ~7300 PF block elements with ~2200 stored
links and ~5000 candidate-element pairs, ~1100 SimTracks, ~500 TrackingParticles,
~7 SimJets and ~7 GenJets above 5 GeV, of which ~80% are matched by ancestry
with both fractions above 0.5, ~650 particles with calorimeter deposits
(`SimCalo`) and ~500 ideal PF candidates. All cross-table indices were checked to be in range and
consistent (SimTrack <-> GenPart pdgId, TP <-> SimTrack pdgId, SimJet pT equal
to the vector sum of its SimTrack constituents, PFCand_trackIdx equal to the
track of its TRACK element).

## Condor production

```bash
./make_rawsim_cfgs.sh                      # -> cfgs/step1_RECO_cfg.py + cfgs/ntuple_reco-pico_cfg.py
voms-proxy-init --voms cms
./submit_rawsim_bdriver.sh --dry-run       # prints the bdriver command only
MAX_FILES=10 EVENTS_PER_JOB=200 ./submit_rawsim_bdriver.sh --submit
```

Defaults (environment overrides): `MAX_FILES=10`, `EVENTS_PER_JOB=200`,
`NTUPLE=reco-pico`, `FINAL_OUTPUT=/eos/user/t/tchatzis/run3_rawsim`,
`JOBAREA=jobs`, `TAG=<primary dataset name, first two fields>`, `OS=el9`,
`RUNTIME=10:00:00`, `MEMORY=6G`, `DISK_MB=20000`. The full sample is ~24M
events; with ~10 s per event for RECO (so ~35 min per 200-event job) plan the
number of files accordingly (`MAX_FILES=-1` takes all of them).

`-p 0` is passed (the files are processed without their parents) and
`--customize-cfg` is never used: the tail handles every argument bdriver passes.

## Pico content of the chain

Groups `event,muons,electrons,jets,pfcands,tracks,vertices,pfclusters,pfblocks,genparts,sim,simcalo,recojets`
(`PICO_TABLES` overrides). Index conventions, all 0-based rows of the Pico tables:

| table | links |
|---|---|
| `PFCand` | `trackIdx` -> `Track` |
| `PFCandElem` | `candIdx` -> `PFCand`, `elemRow` -> `PFBlockElem`: the elements each candidate *used* (PF's decision) |
| `PFBlockElem` | `trackIdx` -> `Track`, `clusterTable`/`clusterIdx` -> `PFCluster<ECAL,HCAL,HO,HF,PS>` (codes 1..5), `candIdx` -> first `PFCand` using it: the inventory of elements |
| `PFBlockLink` | `elemRow1`/`elemRow2` -> `PFBlockElem`, with the link `distance`: what PF found *connected* (its input, not its decision); see "PF block tables" in `PicoProducer/README.md` |
| `SimTrack` | `vertIdx` -> `SimVertex`, `parentIdx` -> `SimTrack`, `genPartIdx` -> `GenPart`, `simJetIdx` -> `SimJet` |
| `SimVertex` | `parentIdx` -> `SimTrack` |
| `SimGenJetMatch` | `simJetIdx` -> `SimJet`, `genJetIdx` -> `GenJet`, with the ancestry-based shared-energy scores (see "Sim jets and the SimJet to GenJet matching" in `PicoProducer/README.md`) |
| `GenJetConst` | `genJetIdx` -> `GenJet`, `genPartIdx` -> `GenPart` |
| `SimCalo` | `simTrackIdx` -> `SimTrack`, `simCaloJetIdx` -> `SimCaloJet`: per-particle calorimeter deposits and single-particle `response` |
| `SimPFCand` | `simTrackIdx` -> `SimTrack`, `simCaloIdx` -> `SimCalo`, `simPFJetIdx` -> `SimPFJet` |
| `SimCaloGenJetMatch`, `SimPFGenJetMatch` | same scores as `SimGenJetMatch` for `SimCaloJet` and `SimPFJet` |
| `PFCandTruth` | one row per `PFCand`: `signalFraction`, dominant `simTrackIdx`; `PFCandSim` holds the shares |
| `PFJet`, `PFJetCHS`, `PFJetPuppi` | raw re-clustered jets; `<Jet>Const` -> `PFCand`, `<Jet>GenMatch` -> `GenJet` with `ptRatio` and `signalPtRatio` |
| `TP` | `genPartIdx` -> `GenPart`, `simTrackIdx` -> `SimTrack`, `parentIdx` -> `TP` |
| `TrackTPLink` | `trackIdx` -> `Track`, `tpIdx` -> `TP`, with `recoToSimQuality`/`simToRecoQuality` (valid when `hasRecoToSim`/`hasSimToReco`) |
| `GenPart` | `genPartIdxMother` -> `GenPart` |

`SimJet` = anti-kt 0.4 of the SimTracks selected by `simJetSelection`
(`leaves`: terminal particles of the stored Geant4 decay tree, no neutrinos),
i.e. generator jets after the decays and conversions Geant4 simulated; `GenJet`
is the `ak4GenJetsNoNu` definition re-clustered in the job for comparison, and
`SimGenJetMatch` pairs the two by ancestry rather than by deltaR.
