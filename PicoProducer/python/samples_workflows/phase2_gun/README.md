# Phase-2 single charged-hadron gun chain

Full-simulation chain for single charged hadrons in the HGCAL acceptance,
flat in |p| (1-200 GeV) and eta (1.6-2.9), run with Reco2Pico's `bdriver`
step chaining on HTCondor:

    step1  GEN,SIM                                  gun (EmptySource)      -> GEN-SIM
    step2  DIGI:pdigi_valid,L1TrackTrigger,L1,L1P2GT,DIGI2RAW,HLT:@relvalRun4  -> GEN-SIM-DIGI-RAW
    step3  RAW2DIGI,RECO,RECOSIM                                             -> GEN-SIM-RECO
    step4  NANO:@HGCALVal                                                     -> NANOAODSIM

Only the step-4 NANO file is staged out (`bdriver --save-intermediates` keeps the others).

## Files

| file | purpose |
|------|---------|
| `SingleHadronPGun_cfi.py` | cmsDriver generator fragment (`FlatRandomMultiParticlePGunProducer`, one particle per event, flat in p, eta, phi). Defaults: pi+ (211), p 1-200 GeV, 1.6 < eta < 2.9, full phi, no anti-particle, `firstRun=1`. |
| `gun_varparsing_tail.py` | VarParsing snippet appended to every cfg. Adds `skipEvents`, `output`, `pdgId`, `pMin`, `pMax`, `etaMin`, `etaMax`, `seed` on top of the standard `analysis` options; applies gun parameters, per-job seeds and event/lumi offsets in the GEN step; sets input files / skipEvents in PoolSource steps; renames the output module (and `TFileService`) to `output=`. Marker `phase2_gun: VarParsing tail` keeps the append idempotent. |
| `make_gun_cfgs.sh [OUTDIR]` | runs the four `cmsDriver.py --no_exec` commands and appends the tail. Env: `GEOM ERA GT GTGEN PU PUINPUT DIGISTEP NANOSTEP`. |
| `run_gun_local.sh [NEVENTS] [PDGID]` | generates the cfgs in `$CMSSW_BASE/src/gun_local_test/cfgs`, runs the four steps locally and inspects the NANO branches. |
| `make_gun_dataset.py` | writes a bdriver dataset JSON with one virtual `gun://jobNNN` "file" per job (validated with `assert_dataset_data`). |
| `steps_gun_chain.json` | bdriver `--steps` manifest for steps 2-4 (`cfgs/...`, resolved relative to the JSON). |
| `steps_gun_chain_pu200.json` | same, pointing at `cfgs_pu200/...` for the PU200 recipe. |
| `submit_gun_bdriver.sh [--submit]` | one bdriver job area per species (pip pim Kp Km p pbar). |

Generated, not versioned: `cfgs/`, `cfgs_pu200/`, `datasets/`, `jobs/`.

## How the pieces fit together

* bdriver runs step 1 as
  `cmsRun -j step1.xml cfg.py pdgId=.. pMin=.. pMax=.. etaMin=.. etaMax=.. maxEvents=M skipEvents=0 inputFiles=gun://jobNNN output=step1_out_NNN.root`
  and then each step of `steps.json` with
  `inputFiles=file:<previous> secondaryInputFiles= maxEvents=-1 skipEvents=0 output=<next>`.
* The tail derives the job index from `job(\d+)` in `inputFiles` (fallback:
  `skipEvents // maxEvents`) and sets, on the GEN step,
  `initialSeed = (seed or 12345) + 1000*job` for every module of
  `RandomNumberGeneratorService` (generator, VtxSmeared, g4SimHits, mix, ...),
  `source.firstEvent = 1 + maxEvents*job` and `source.firstLuminosityBlock = 1 + job`.
  Every job therefore has unique event ids and statistically independent events.
* In PoolSource steps the tail also recognises bdriver's `step1_out_NNN.root`
  naming and offsets the seeds the same way, so that pile-up mixing in step 2
  is not identical in every job (the default `mix` seed would be).
* The dataset JSON has `JOBS` entries of `EVENTS_PER_JOB` events; with
  `bdriver -n EVENTS_PER_JOB` this gives exactly one job per entry.

## Local test

```bash
./run_gun_local.sh 10 211
```

This generates the cfgs and runs, in `$CMSSW_BASE/src/gun_local_test/`:

```bash
cmsRun -j step1.xml cfgs/step1_GENSIM_cfg.py inputFiles=gun://job000 maxEvents=10 skipEvents=0 output=step1.root pdgId=211 pMin=1 pMax=200 etaMin=1.6 etaMax=2.9
cmsRun -j step2.xml cfgs/step2_DIGIRAW_cfg.py inputFiles=file:step1.root maxEvents=-1 skipEvents=0 output=step2.root
cmsRun -j step3.xml cfgs/step3_RECO_cfg.py   inputFiles=file:step2.root maxEvents=-1 skipEvents=0 output=step3.root
cmsRun -j step4.xml cfgs/step4_NANO_cfg.py   inputFiles=file:step3.root maxEvents=-1 skipEvents=0 output=step4_nano.root
```

and finally prints OK/MISSING for the branch prefixes `ticlTrackstersCLUE3DHigh`,
`ticlSimTrackstersfromCPs`, `TICLCandidates`, `GeneralTrack`, `hgcalLayerClusters`
and the event count of `step4_nano.root`.

To only (re)generate the cfgs: `./make_gun_cfgs.sh [OUTDIR]` (default `OUTDIR=cfgs`).

## Condor production

```bash
./make_gun_cfgs.sh                       # -> cfgs/step{1..4}_*_cfg.py
voms-proxy-init --voms cms
./submit_gun_bdriver.sh                  # creates the job areas, no submission
./submit_gun_bdriver.sh --submit         # creates and submits
```

Defaults (all overridable through the environment): `JOBS=200`,
`EVENTS_PER_JOB=500`, `PMIN=1 PMAX=200`, `ETAMIN=1.6 ETAMAX=2.9`,
`SPECIES="211 -211 321 -321 2212 -2212"`, `FINAL_OUTPUT=/eos/user/t/tchatzis/phase2_gun`,
`JOBAREA=jobs`, `OS=el9`, `RUNTIME=20:00:00`, `SEED=` (when set, passed as
`seed=<n>` to all steps; job offsets are added on top).

For each species the script writes `datasets/gun_<label>_p<PMIN>to<PMAX>.json`
and calls

```bash
python3 $CMSSW_BASE/src/Reco2Pico/PicoProducer/scripts/bdriver \
  -c cfgs/step1_GENSIM_cfg.py --steps steps_gun_chain.json -d datasets/gun_<label>_p1to200.json \
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
CFGDIR=$PWD/cfgs_pu200 STEPS=$PWD/steps_gun_chain_pu200.json TAGSUFFIX=_pu200 ./submit_gun_bdriver.sh [--submit]
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

## Release-specific choices (CMSSW_16_1_0_pre2)

* Geometry/era/GT follow the Run4D121 relval workflow: `ExtendedRun4D121`,
  era `Phase2C22I13M9`, GT `auto:phase2_realistic_T35`, HLT menu `@relvalRun4`.
  D121 is the Phase-2 baseline since CMSSW_15_1_0_pre4 and the geometry of the
  HGCAL/TICL relvals in the limited matrix (`CloseByPGun_CE_*`). Verify with
  `runTheMatrix.py -w upgrade -n | grep -i Run4D121`. The GEN-SIM step uses
  the `_13TeV` GT alias (HL-LHC SimBeamSpot payload for
  `--beamspot DBrealisticHLLHC`), reproduced by `GTGEN`. Override with
  `GEOM=... ERA=... GT=...` (e.g. `GEOM=D110 ERA=Phase2C17I13M9` for the
  previous baseline).
* `FlatRandomPGunProducer` does not exist in `IOMC/ParticleGuns`;
  `FlatRandomMultiParticlePGunProducer` with a single `PartID` is used instead.
* The relval DIGI step includes `L1P2GT` (Phase-2 L1 global trigger emulation),
  which the `@relvalRun4` HLT menu consumes; it is kept in `DIGISTEP`.
* `NANO:@HGCALVal` is **not** defined in `PhysicsTools.NanoAOD.autoNANO` of this
  release, so `make_gun_cfgs.sh` writes steps 1-3, prints the available flavours
  and exits with status 2 without `step4_NANO_cfg.py`. Override with
  `NANOSTEP=NANO:@<flavour>` once an HGCAL/TICL NANO flavour is available (or
  in a release that has it).
