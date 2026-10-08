# Phase-2 single charged-hadron gun chain

Full-simulation chain for single charged hadrons in the HGCAL acceptance,
flat in |p| (1-200 GeV) and eta (1.6-2.9), run with Reco2Pico's `bdriver`
step chaining on HTCondor:

    step1  GEN,SIM                                  gun (EmptySource)      -> GEN-SIM
    step2  DIGI:pdigi_valid,L1TrackTrigger,L1,L1P2GT,DIGI2RAW,HLT:@relvalRun4  -> GEN-SIM-DIGI-RAW
    step3  RAW2DIGI,RECO,RECOSIM                                             -> GEN-SIM-RECO
    step4  ntuple definition (default hgcalval-nano = NANO:@HGCALVal)          -> NANOAODSIM

Steps 1-3 define the *sample*; step 4 is an *ntuple definition* chosen with
`NTUPLE=<name>` from `../common/ntuples/` (`hgcalval-nano`, `hgcal-nano`,
`phys-nano`, ...). Only the step-4 file is staged out (`bdriver
--save-intermediates` keeps the others).

The generic machinery (bdriver command-line contract, cmsDriver helpers, local
test scaffolding, ntuple definitions, generic bdriver submission) lives in
`../common/` and is shared with any other sample workflow; see
`../common/README.md`. This directory only holds what is specific to the gun.

## Files

| file | purpose |
|------|---------|
| `SingleHadronPGun_cfi.py` | cmsDriver generator fragment (`FlatRandomMultiParticlePGunProducer`, one particle per event, flat in p, eta, phi). Defaults: pi+ (211), p 1-200 GeV, 1.6 < eta < 2.9, full phi, no anti-particle, `firstRun=1`. |
| `gun_options.py` | the gun's extra VarParsing options (`pdgId pMin pMax etaMin etaMax`) and the GEN hook that applies them to `process.generator.PGunParameters`. |
| `gun_varparsing_tail.py` | four-line snippet appended to every cfg: imports `common.varparsing.apply_varparsing` and `gun_options`, and calls `apply_varparsing(process, extra_options=GUN_OPTIONS, on_gen=apply_gun, tag='phase2_gun')`. The marker line `samples_workflows: VarParsing tail` keeps the append idempotent. |
| `make_gun_cfgs.sh [OUTDIR]` | three `cmsDriver.py --no_exec` commands (steps 1-3) + the ntuple cfg from the `NTUPLE` definition, then appends the tail. Env: `GEOM ERA GT GTGEN PU PUINPUT DIGISTEP NTUPLE`. Output: `step1_GENSIM_cfg.py step2_DIGIRAW_cfg.py step3_RECO_cfg.py ntuple_<NTUPLE>_cfg.py`. |
| `run_gun_local.sh [NEVENTS] [PDGID]` | generates the cfgs in `local_test/cfgs`, runs the four steps locally and inspects the ntuple branches (`NTUPLE_INSPECT` of the definition). Asks before wiping an existing `local_test/` (`CLEAN=yes|no` to skip the prompt, `TESTDIR=...` to relocate). |
| `make_gun_dataset.py` | writes a bdriver dataset JSON with one virtual `gun://jobNNN` "file" per job (validated with `assert_dataset_data`). |
| `steps_gun_chain.json` | *sample* steps manifest (steps 2-3, `cfgs/...` relative to the JSON). The ntuple step is appended at submission time. |
| `steps_gun_chain_pu200.json` | same, pointing at `cfgs_pu200/...` for the PU200 recipe. |
| `submit_gun_bdriver.sh [--submit] [--dry-run]` | one bdriver job area per species (pip pim Kp Km p pbar): writes the dataset JSON, composes `datasets/steps_<tag>_<NTUPLE>.json` = sample steps + `cfgs/ntuple_<NTUPLE>_cfg.py`, and calls `../common/submit_bdriver_chain.sh`. |

Generated, not versioned: `cfgs/`, `cfgs_pu200/`, `datasets/`, `jobs/`, `local_test/`.

## How the pieces fit together

* bdriver runs step 1 as
  `cmsRun -j step1.xml cfg.py pdgId=.. pMin=.. pMax=.. etaMin=.. etaMax=.. maxEvents=M skipEvents=0 inputFiles=gun://jobNNN output=step1_out_NNN.root`
  and then each step of `steps.json` with
  `inputFiles=file:<previous> secondaryInputFiles= maxEvents=-1 skipEvents=0 output=<next>`.
* `common/varparsing.py` derives the job index from `job(\d+)` in `inputFiles` (fallback:
  `skipEvents // maxEvents`) and sets, on the GEN step,
  `initialSeed = (seed or 12345) + 1000*job` for every module of
  `RandomNumberGeneratorService` (generator, VtxSmeared, g4SimHits, mix, ...),
  `source.firstEvent = 1 + maxEvents*job` and `source.firstLuminosityBlock = 1 + job`.
  Every job therefore has unique event ids and statistically independent events.
* In PoolSource steps it also recognises bdriver's `step1_out_NNN.root`
  naming and offsets the seeds the same way, so that pile-up mixing in step 2
  is not identical in every job (the default `mix` seed would be).
* The dataset JSON has `JOBS` entries of `EVENTS_PER_JOB` events; with
  `bdriver -n EVENTS_PER_JOB` this gives exactly one job per entry.

## Local test

```bash
./run_gun_local.sh 10 211
```

This generates the cfgs and runs, in `local_test/` next to the script (override with
`TESTDIR=...`). If that directory already exists the script shows its contents and
asks whether to wipe it; `CLEAN=yes` or `CLEAN=no` answers non-interactively.
Re-running on top of old outputs fails in cmsRun with
`Fatal Root Error: @SUB=TStorageFactorySystem::Unlink Unsupported`, because the
output module recreates the file and the storage adaptor refuses to delete the
old one. The steps are:

```bash
cmsRun -j step1.xml cfgs/step1_GENSIM_cfg.py inputFiles=gun://job000 maxEvents=10 skipEvents=0 output=step1.root pdgId=211 pMin=1 pMax=200 etaMin=1.6 etaMax=2.9
cmsRun -j step2.xml cfgs/step2_DIGIRAW_cfg.py inputFiles=file:step1.root maxEvents=-1 skipEvents=0 output=step2.root
cmsRun -j step3.xml cfgs/step3_RECO_cfg.py   inputFiles=file:step2.root maxEvents=-1 skipEvents=0 output=step3.root
cmsRun -j step4.xml cfgs/ntuple_hgcalval-nano_cfg.py inputFiles=file:step3.root maxEvents=-1 skipEvents=0 output=step4_ntuple.root
```

and finally prints OK/MISSING for the branch prefixes of the ntuple definition
(for `hgcalval-nano`: `ticlTrackstersCLUE3DHigh`, `ticlSimTrackstersfromCPs`,
`TICLCandidates`, `GeneralTrack`, `HGCalLayerClusters`, `SimCl2CPWithFraction`)
and the event count of `step4_ntuple.root` (`EMPTY` = branches exist but no table
entry in any event; the script then fails). It finally writes
`local_test/doc_<NTUPLE>.html` (+ `.csv`), the variable documentation of the
ntuple: one table per collection with type, size, NanoAOD `doc` string and fill
statistics (entries, distinct values, min/max, most-common fraction), a
collections summary with mean multiplicity and a size pie chart, in the style of
`workflows/doc_PicoAOD.html`. For any other file:
`python3 ../common/make_ntuple_doc.py out_000.root -o doc.html --csv doc.csv`.
`NTUPLE=hgcal-nano ./run_gun_local.sh` runs the same chain with another ntuple
definition.

On a 10-event pi+ sample the only collection empty in every event is
`TICLCandidatesGsfTrackIdxs` (no electrons, hence no GSF tracks to link).
Constant branches are placeholders of the release, not of this chain:
`TICLCandidatesExtra_track_boundary*` is -999 because the candidate tracksters
carry no `trackIdxs` in this release (the track->HGCAL-boundary extrapolation is
available per track in `GeneralTrack_hgcal_*`, reachable through
`TICLCandidatesTrackIdxs`), `HGCalLayerClusters_correctedEnergy` is -1 and the
tracksters' `regressed_energy` is 0 (not computed in the offline TICL of this
release), and the `GeneralTrack_isMuon`/`muon_*` columns are -1 (no muons).

To only (re)generate the cfgs: `./make_gun_cfgs.sh [OUTDIR]` (default `OUTDIR=cfgs`).

## Step 4: the NANO prevalidation trick

### The problem

`NANO:@HGCALVal` (`DPGAnalysis/HGCalNanoAOD`, sequence
`hgcalNanoValidationSequence`) writes, on top of the reco tables of `NANO:@HGCAL`,
the sim tracksters, the reco<->sim association tables, the layer clusters and the
gen particles. Those tables consume products that `RAW2DIGI,RECO,RECOSIM` does
**not** write:

| product | made by |
|---|---|
| `ticlSimTracksters`, `ticlSimTrackstersfromCPs` | `ticlSimTrackstersTask` (`RecoHGCal/TICL/python/SimTracksters_cff.py`) |
| `SimClusterToCaloParticleAssociation:simClusterToCaloParticleMap` | `hgcalAssociators` (`Validation/Configuration/python/hgcalSimValid_cff.py`) |
| `allTrackstersToSimTrackstersAssociationsByHits:*` | `hgcalAssociators` |
| `quickTrackAssociatorByHits` (needed by `trackingParticleGsfTrackAssociation` inside `ticlSimTrackstersTask`) | tracking prevalidation (`Validation/RecoTrack`) |

In the release they are produced by the **prevalidation** part of the
`VALIDATION` step (`globalPrevalidationHGCal = Sequence(hgcalAssociators,
ticlSimTrackstersTask)` in `Validation/Configuration/python/globalValidation_cff.py`).
The relval that exercises this flavour (`upgradeWFs['HGCALNanoVal']`, suffix
`_HGCALNanoVal`) runs

```
-s RAW2DIGI,RECO,RECOSIM,PAT,NANO:@HGCALVal,VALIDATION:@phase2Validation+@miniAODValidation,DQM:@phase2+@miniAODDQM
```

i.e. NANO in the *same job* as the validation, so the products are simply there.
Our chain runs NANO as a separate step on `step3.root`, and the first table dies with

```
An exception of category 'ProductNotFound' occurred while
   [1] Running path 'nanoAOD_step'
   [2] Calling method for module SimClusterCaloParticleFractionFlatTableProducer/'SimCl2CPOneToOneFlatTable'
Looking for module label: SimClusterToCaloParticleAssociation
Looking for productInstanceName: simClusterToCaloParticleMap
```

Merging steps 3 and 4 into one job is not an option here: the VarParsing tail
requires one output module per step, and `VALIDATION` would also run all the DQM
validators and add a DQMIO output.

### The fix

`../common/hgcalNanoPrevalidation.py` is a cmsDriver `--customise` function that re-uses the
release Tasks instead of re-implementing anything, and attaches them to the NANO
path:

```python
process.load('Configuration.StandardSequences.Accelerators_cff')  # resolves '@alpaka' ESProducers
process.load('RecoHGCal.TICL.TICLGeom_cff')                       # TICLGeomLayersHost etc.
process.load('Validation.Configuration.hgcalSimValid_cff')        # hgcalAssociators (Task)
process.load('RecoHGCal.TICL.SimTracksters_cff')                  # ticlSimTrackstersTask
process.load('RecoLocalCalo.HGCalRecProducers.recHitMapProducer_cff')
process.load('SimTracker.TrackerHitAssociation.tpClusterProducer_cfi')
process.load('SimTracker.TrackAssociatorProducers.quickTrackAssociatorByHits_cfi')
process.load('SimTracker.TrackAssociation.trackingParticleRecoTrackAsssociation_cfi')
process.load('SimGeneral.TrackingAnalysis.simHitTPAssociation_cfi')
process.hgcalNanoPrevalidationInputsTask = cms.Task(process.recHitMapProducer,
    process.tpClusterProducer, process.quickTrackAssociatorByHits,
    process.trackingParticleRecoTrackAsssociation, process.simHitTPAssocProducer)
process.nanoAOD_step.associate(process.hgcalNanoPrevalidationInputsTask,
                               process.hgcalAssociators,
                               process.ticlSimTrackstersTask)
```

Why this works: a `cms.Task` is *unscheduled*. Its modules run only when a
module on the path consumes their product, and the framework orders them by
dependency. So the associators and the sim-trackster producer run on demand right
before the table producers, and nothing else from the `VALIDATION` step (DQM
histogram fillers, harvesting, DQMIO output) is executed.

Several things a NANO-only job lacks that a RECO job (or the tracking
prevalidation) provides implicitly had to be added by hand. The first three
showed up as hard errors; the last three are worse, because the consumers only
**warn** and produce empty maps, so the sim tables of the NANO come out empty
without the job failing (`ticlSimTracksters`, every `Reco*2Sim*` / `Sim*2*`
table and `SimTICLCandidates` had 0 entries in every event):

1. **TICL geometry ESProducers** (`RecoHGCal.TICL.TICLGeom_cff`), otherwise
   `Cannot find EventSetup module to produce data of type "TICLGeomLayersHost"`.
2. **Accelerators** (`Configuration.StandardSequences.Accelerators_cff`): the
   geometry producers are `@alpaka` modules and without it you get
   `Unable to find plugin 'TICLGeomESProducer@alpaka'`.
3. **Track<->TrackingParticle associator** (`tpClusterProducer` +
   `quickTrackAssociatorByHits`): `ticlSimTracksters` links sim tracksters to GSF
   tracks via `trackingParticleGsfTrackAssociation`, which in the relval is fed by
   the tracking prevalidation. Without it:
   `ProductNotFound ... reco::TrackToTrackingParticleAssociator quickTrackAssociatorByHits`.
4. **HGCAL hit map** (`recHitMapProducer`, `RecoLocalCalo.HGCalRecProducers.recHitMapProducer_cff`):
   DetId->index map plus the `RefProdVector` of the `HGCalRecHit` collections; it
   is a transient product of the local reco. Without it every associator logs
   `Hit map not valid. Producing empty associator`, `RecHitCollections is invalid`,
   `Missing MultiRecHitCollection` and the sim tracksters find no hits.
5. **TrackingParticle<->generalTracks association**
   (`trackingParticleRecoTrackAsssociation`, on top of `quickTrackAssociatorByHits`):
   `SimTrackstersProducer` returns early with `Missing TP->RecoTrack association`.
6. **SimTrack->TrackingParticle map** (`simHitTPAssocProducer`,
   `SimGeneral.TrackingAnalysis.simHitTPAssociation_cfi`), read by
   `ticlSimTracksters` once 5. is in place.

Always check the sim tables for entries, not only for the presence of branches:
`sw_inspect_nano` (used by `run_gun_local.sh`) now reports `EMPTY` and fails
when a checked table has zero entries in every event, and the generated
`doc_<NTUPLE>.html` flags empty collections and constant branches.

### How it is wired in

The customisation lives in `../common/hgcalNanoPrevalidation.py` (it is about
`NANO:@HGCALVal`, not about the gun). The ntuple definition
`../common/ntuples/hgcalval-nano.sh` sets

```
NTUPLE_CUSTOMISE='Reco2Pico/PicoProducer/samples_workflows/common/hgcalNanoPrevalidation.customise'
```

and `sw_make_ntuple_cfg` (in `../common/chain_lib.sh`) passes it as `--customise`
to the ntuple `cmsDriver.py`. cmsDriver turns `A/B/file.func` into
`from A.B.file import func`; the `python/` directory is implicit because scram
links it into `$CMSSW_BASE/python`. The call ends up inside the generated
`ntuple_hgcalval-nano_cfg.py` (`customising the process with customise from
.../hgcalNanoPrevalidation`), so the Condor chain picks it up through the
composed manifest with nothing else to configure.

Cost: the associators and sim tracksters run once more in step 4 (they are not
in `step3.root`); for a single-particle gun this is negligible next to RECO.
The `hgcal-nano` definition (`NANO:@HGCAL`, reco tables only) does not need it
and does not set it.

## Condor production

```bash
./make_gun_cfgs.sh                       # -> cfgs/step{1..3}_*_cfg.py + cfgs/ntuple_hgcalval-nano_cfg.py
voms-proxy-init --voms cms
./submit_gun_bdriver.sh --dry-run        # prints the bdriver commands only
./submit_gun_bdriver.sh                  # creates the job areas, no submission
./submit_gun_bdriver.sh --submit         # creates and submits
```

Another ntuple: `NTUPLE=hgcal-nano ./make_gun_cfgs.sh` then
`NTUPLE=hgcal-nano ./submit_gun_bdriver.sh ...` (the submit script refuses to
run if `cfgs/ntuple_<NTUPLE>_cfg.py` is missing).

Defaults (all overridable through the environment): `JOBS=200`,
`EVENTS_PER_JOB=500`, `PMIN=1 PMAX=200`, `ETAMIN=1.6 ETAMAX=2.9`,
`SPECIES="211 -211 321 -321 2212 -2212"`, `NTUPLE=hgcalval-nano`,
`FINAL_OUTPUT=/eos/user/t/tchatzis/phase2_gun`,
`JOBAREA=jobs`, `OS=el9`, `RUNTIME=20:00:00`, `SEED=` (when set, passed as
`seed=<n>` to all steps; job offsets are added on top).

For each species the script writes `datasets/gun_<label>_p<PMIN>to<PMAX>.json`,
composes `datasets/steps_<tag>_<NTUPLE>.json` (absolute paths of
`cfgs/step2_DIGIRAW_cfg.py`, `cfgs/step3_RECO_cfg.py`, `cfgs/ntuple_<NTUPLE>_cfg.py`)
and, through `../common/submit_bdriver_chain.sh`, calls

```bash
python3 $CMSSW_BASE/src/Reco2Pico/PicoProducer/scripts/bdriver \
  -c cfgs/step1_GENSIM_cfg.py --steps datasets/steps_<tag>_hgcalval-nano.json -d datasets/gun_<label>_p1to200.json \
  -o jobs/<tag> -fo /eos/user/t/tchatzis/phase2_gun/<tag> -n 500 -p 0 --name gun_<tag> \
  --JobFlavour tomorrow -t 20:00:00 --memory 4G --cpus 1 --disk-mb 8000 --os el9 [--submit] \
  pdgId=<pdg> pMin=1 pMax=200 etaMin=1.6 etaMax=2.9
```

with `<tag> = <label>_p1to200`. Outputs land in
`/eos/user/t/tchatzis/phase2_gun/<tag>/out_NNN.root`. Because `-o` resolves
under `/eos`, bdriver mirrors the Condor bookkeeping area under
`/afs/cern.ch/user/t/tchatzis/condor_jobs_files/...` (see its `paths.json`);
a job area that already exists makes bdriver stop, so remove it (or change
`JOBAREA`/`TAGSUFFIX`) before re-running.

`-p 0` is required (the gun dataset entries have no parent files and bdriver's
default `-p 2` stops on an empty secondary-file list). `-t` is passed explicitly
because bdriver's default of one hour is far too short for 500 full-simulation
Phase-2 events.

## PU200 recipe

Same dataset JSONs (hence the same seeds, event ids and gun kinematics per job),
second cfg set with pile-up in step 2:

```bash
PU=200 PUINPUT='das:/RelValMinBias_14TeV/<campaign>-<GT>/GEN-SIM' ./make_gun_cfgs.sh cfgs_pu200
CFGDIR=$PWD/cfgs_pu200 SAMPLE_STEPS=$PWD/steps_gun_chain_pu200.json TAGSUFFIX=_pu200 ./submit_gun_bdriver.sh [--submit]
```

Only `mix` differs between `cfgs/` and `cfgs_pu200/`; step 1 is identical
(and, for a given job, produces identical events) in the two productions.
Adjust `--memory`/`--disk-mb`/`RUNTIME` for PU200 (the RAW and RECO files are
much larger and the reconstruction much slower).

## bdriver caveats

1. **Never use `--customize-cfg`.** bdriver's customization unconditionally does
   `process.source.fileNames = opts.inputFiles`, which is not a parameter of the
   gun's `EmptySource` and makes step 1 fail; it would also create a second
   VarParsing object. `gun_varparsing_tail.py` already handles every argument
   bdriver passes (`maxEvents`, `skipEvents`, `inputFiles`,
   `secondaryInputFiles`, `output`). For the same reason do not put the reserved
   keys in `steps_gun_chain.json` `args` (bdriver refuses them anyway).
2. **Job OS.** `submit_gun_bdriver.sh` passes `--os el9` so the job runs natively
   on EL9 workers. An older bdriver without `--os` hard-codes `el8` and
   re-executes inside `cmssw-el8`, which cannot run an `el9_amd64_gcc13` release.

## Release-specific choices (CMSSW_20_1_0_pre3)

* Geometry/era/GT follow the Run4D127 relval workflow: `ExtendedRun4D127`,
  era `Phase2C26I13M9`, GT `auto:phase2_realistic_T35`, HLT menu `@relvalRun4`
  (`HLT_75e33`, see `Configuration/HLT/python/autoHLT.py`).
  D127 is the Phase-2 baseline since CMSSW_20_1_0_pre2 (`prefixDet=37600` in
  `relval_Run4.py`) and the geometry of the HGCAL/TICL relvals in the limited
  matrix (`CloseByPGun_CE_*`). D128 (workflow 38434.0) is the same detector with
  the M16 muon geometry, "to be used for trigger studies"; it shares era, GT and
  HLT menu. Verify with
  `runTheMatrix.py -w upgrade -n -e -l 37634.0,37696.0`. The GEN-SIM step uses
  the `_13TeV` GT alias (HL-LHC SimBeamSpot payload for
  `--beamspot DBrealisticHLLHC`), reproduced by `GTGEN`. Override with
  `GEOM=... ERA=... GT=...` (e.g. `GEOM=D128`, or `GEOM=D121 ERA=Phase2C22I13M9`
  for the previous baseline).
* `FlatRandomPGunProducer` does not exist in `IOMC/ParticleGuns`;
  `FlatRandomMultiParticlePGunProducer` with a single `PartID` is used instead.
* The relval DIGI step includes `L1P2GT` (Phase-2 L1 global trigger emulation),
  which the `@relvalRun4` HLT menu consumes; it is kept in `DIGISTEP`.
* `NANO:@HGCALVal` cannot run standalone on a `RECOSIM` file; step 4 needs the
  `hgcalNanoPrevalidation.py` customisation. See "Step 4: the NANO prevalidation
  trick" above.
