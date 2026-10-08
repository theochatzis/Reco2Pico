# samples_workflows/common

Everything a chained sample workflow needs that is not specific to one sample.
A workflow directory (e.g. `../phase2_gun/`) keeps only its generator fragment,
its extra VarParsing options, its sample steps manifest and thin wrapper scripts.

```
common/
  varparsing.py              bdriver command-line contract for every cmsRun step (importable)
  chain_lib.sh               shell helpers: cmsDriver, tail append, ntuple cfg, manifests, local test
  submit_bdriver_chain.sh    one bdriver job area for one dataset of a chain
  hgcalNanoPrevalidation.py  --customise for a standalone NANO:@HGCALVal step
  make_ntuple_doc.py         variable documentation (HTML + CSV, fill statistics) of an ntuple
  ntuples/<name>.sh          ntuple definitions (the last step of every chain)
```

## Calling the tools from anywhere

`Reco2Pico/PicoProducer/scripts/` holds thin wrappers that scram installs into
`$CMSSW_BASE/bin/$SCRAM_ARCH` on `scram b` (the same mechanism as `bdriver`), so
after `cmsenv` these work from any directory:

| command | runs |
|---|---|
| `make_ntuple_doc FILE.root [-o doc.html] [--csv ...]` | `common/make_ntuple_doc.py` |
| `submit_bdriver_chain ...` | `common/submit_bdriver_chain.sh` |
| `samples_workflows_common` | prints the absolute path of this directory, e.g. `source "$(samples_workflows_common)/chain_lib.sh"` |

The wrappers resolve `common/` through `CMSSW_BASE` first and `CMSSW_RELEASE_BASE`
as fallback, so a checked-out copy wins over an installed one. After adding a new
wrapper, run `scram b` once so it appears in `bin/`. The Python modules are also
importable as `Reco2Pico.PicoProducer.samples_workflows.common.<module>`.

## The chain model

    sample steps (workflow)           ntuple step (common/ntuples)
    step1 GEN-SIM -> step2 -> step3   ->   ntuple_<NTUPLE>_cfg.py   -> staged out by bdriver

bdriver runs step 1 with the workflow's arguments plus
`maxEvents= skipEvents= inputFiles= output=`, and every later step with
`inputFiles=file:<previous> secondaryInputFiles= maxEvents=-1 skipEvents=0 output=<next>`.
Only the last step's output is transferred to the final destination. Any cfg
that honours these arguments can be a step, so the ntuple step is pluggable.

## varparsing.py

```python
from Reco2Pico.PicoProducer.samples_workflows.common.varparsing import apply_varparsing
process = apply_varparsing(process, extra_options=OPTS, on_gen=hook, tag='my_workflow')
```

* registers `skipEvents`, `output`, `seed` and `extra_options`
  (`(name, default, VarParsing.varType.X, doc)` tuples) on `VarParsing('analysis')`
  and parses the command line once;
* job index: `job(\d+)` in the first input (`gun://jobNNN`), else bdriver's
  `*_out_NNN.root`, else `skipEvents // maxEvents`;
* GEN steps (EmptySource + `process.generator`): `initialSeed = (seed or 12345) + 1000*job`
  on every `RandomNumberGeneratorService` PSet (it refuses to run if `generator`,
  `VtxSmeared`, `g4SimHits` or `mix` has none), `source.firstEvent = 1 + maxEvents*job`,
  `source.firstLuminosityBlock = 1 + job`, then `on_gen(process, opts, job)`;
* PoolSource steps: `fileNames`, `secondaryFileNames`, `skipEvents`; seeds are
  offset the same way when the job index came from the input name (so pile-up
  mixing differs between jobs);
* renames the single output module (and `TFileService`) to `output=`.

A workflow appends a few lines to each cfg (see `../phase2_gun/gun_varparsing_tail.py`);
the marker `samples_workflows: VarParsing tail` makes the append idempotent and
is what `submit_bdriver_chain.sh` checks for.

## chain_lib.sh

Source it (`source .../common/chain_lib.sh`) after `set -euo pipefail`; set `SW_LOG`
for the log prefix. Functions:

| function | purpose |
|---|---|
| `sw_require_cmssw` | abort unless `cmsenv` was done |
| `sw_gtgen GT` | `GT_13TeV` if that `autoCond` alias exists (HL-LHC beam spot for `--beamspot DBrealisticHLLHC`), else `GT` |
| `sw_run_driver ARGS` | echo + `cmsDriver.py ARGS` |
| `sw_append_tail CFG TAIL` | append `TAIL` unless the marker is present |
| `sw_load_ntuple NAME` | source `ntuples/NAME.sh`, validate it (NANO flavour exists in `autoNANO`, cfg exists) |
| `sw_ntuple_cfg_name` | `ntuple_<NAME>_cfg.py` |
| `sw_make_ntuple_cfg OUTDIR FILEIN -- CMSDRIVER_ARGS` | write the ntuple cfg: `cmsDriver.py ntuple -s $NTUPLE_STEP ...` or copy `$NTUPLE_CFG` |
| `sw_compose_steps OUT SAMPLE_STEPS NTUPLE_CFG` | bdriver manifest = sample steps (made absolute) + ntuple step |
| `sw_prepare_testdir DIR CLEAN` | `CLEAN=ask|yes|no`; wipes a leftover test directory (stale outputs make cmsRun fail with `TStorageFactorySystem::Unlink Unsupported`) |
| `sw_run_step N CFG ARGS` | `cmsRun -j stepN.xml`, log `stepN.log`, exit on failure (PIPESTATUS handled correctly under `pipefail`) |
| `sw_inspect_nano FILE PREFIX...` | per table prefix: `OK` (with entry count), `EMPTY` (branches but 0 entries in every event) or `MISSING`; non-zero exit on EMPTY/MISSING |
| `sw_make_ntuple_doc FILE [OUT.html] [TITLE]` | variable documentation via `make_ntuple_doc.py` (+ CSV next to the HTML) |

## Ntuple definitions (`ntuples/<name>.sh`)

A definition is a small shell file setting

| variable | meaning |
|---|---|
| `NTUPLE_KIND` | `cmsdriver` (build the cfg with cmsDriver from the sample's conditions) or `cfg` (copy a hand-written cfg, `NTUPLE_CFG` relative to `$CMSSW_BASE/src`) |
| `NTUPLE_STEP` | cmsDriver `-s`, e.g. `NANO:@HGCALVal` or `PAT,NANO:@PHYS` |
| `NTUPLE_EVENTCONTENT`, `NTUPLE_DATATIER` | cmsDriver `--eventcontent` / `--datatier` |
| `NTUPLE_CUSTOMISE` | cmsDriver `--customise` (optional) |
| `NTUPLE_INSPECT` | branch prefixes the local test checks |
| `NTUPLE_DESCRIPTION` | one line for the logs |

Available:

| name | step | notes |
|---|---|---|
| `hgcalval-nano` (default) | `NANO:@HGCALVal` | HGCAL reco + sim tracksters, reco<->sim associations, layer clusters, gen particles. Needs `hgcalNanoPrevalidation.customise` (see below). |
| `hgcal-nano` | `NANO:@HGCAL` | HGCAL reco tables only (tracksters, TICL candidates, tracks). |
| `phys-nano` | `PAT,NANO:@PHYS` | standard NanoAOD; PAT runs in the same step because central NANO reads MiniAOD. Runs on Phase-2 gun events; content not reviewed for that use. |

A `cfg`-kind definition (e.g. a Reco2Pico `RECO_to_pico` cfg) must honour the
bdriver arguments above, i.e. call `apply_varparsing` or register the same options.

### hgcalNanoPrevalidation.py

`NANO:@HGCALVal` consumes `ticlSimTracksters*`, `SimClusterToCaloParticleAssociation`
and the hit-based trackster<->sim-trackster associations, which `RAW2DIGI,RECO,RECOSIM`
does not write; the relval only has them because NANO runs in the same job as
`VALIDATION:@phase2Validation`. The customisation attaches the release Tasks
`hgcalAssociators` and `ticlSimTrackstersTask` to the NANO path together with the
transient inputs they need and that are neither in the file nor loaded by a NANO
job: `recHitMapProducer` (HGCAL hit map + rechit `RefProdVector`),
`tpClusterProducer` + `quickTrackAssociatorByHits` + `trackingParticleRecoTrackAsssociation`
(TP<->track), `simHitTPAssocProducer` (SimTrack->TP), plus the ESProducers of
`RecoHGCal.TICL.TICLGeom_cff` and `Configuration.StandardSequences.Accelerators_cff`.
Tasks are unscheduled, so only what the tables consume actually runs. Beware that
the associators and `SimTrackstersProducer` only *warn* when an input is missing
and then write empty maps, so a missing input shows up as empty sim tables, not
as a failed job; `sw_inspect_nano` and `make_ntuple_doc.py` both flag that. Full
story: "Step 4: the NANO prevalidation trick" in `../phase2_gun/README.md`.

## make_ntuple_doc.py

```
python3 make_ntuple_doc.py FILE.root [-o doc.html] [--csv vars.csv] [--title T] [--max-events N]
```

Same idea as `PicoProducer/python/workflows/make_workbook.py` (one searchable
DataTable per collection, size pie chart) with fill statistics on top: a
collections summary (mean multiplicity, fraction of events with >= 1 entry,
size, `EMPTY` flag) and, per branch, entries, distinct values, min/max and the
fraction of entries equal to the most common value, so that empty tables and
constant placeholders (-999, -1, 0) stand out. The description column is the
NanoAOD `doc` string (branch title). `run_gun_local.sh` writes
`local_test/doc_<NTUPLE>.html`; on any staged `out_NNN.root` run
`make_ntuple_doc out_NNN.root -o doc.html --csv doc.csv` (wrapper in `bin/`, see above).

## submit_bdriver_chain.sh

```
submit_bdriver_chain.sh [--submit] [--dry-run] \
  --dataset DATASET.json --step1 STEP1_CFG --steps STEPS.json \
  --jobarea DIR --final-output DIR --name NAME --events-per-job N \
  [--parents 0] [--runtime 20:00:00] [--os el9] [--memory 4G] [--cpus 1] \
  [--disk-mb 8000] [--job-flavour tomorrow] [-- key=value ...]
```

Checks bdriver, the dataset, the step-1 tail marker and every cfg of the
manifest, prints the bdriver command and runs it (`--dry-run`: print only).
`--parents 0` is for datasets without parent files (bdriver's own default `-p 2`
refuses an empty secondary-file list). Never pass `--customize-cfg` to bdriver:
it sets `process.source.fileNames` on the EmptySource of a GEN step.

## Adding a workflow

1. `mkdir ../my_workflow && touch ../my_workflow/__init__.py`, add the generator
   fragment and a `my_options.py` with the extra options and GEN hook.
2. A tail snippet (copy `../phase2_gun/gun_varparsing_tail.py`, change the imports).
3. `make_my_cfgs.sh`: source `chain_lib.sh`, run the sample cmsDriver steps,
   `sw_load_ntuple "$NTUPLE"`, `sw_make_ntuple_cfg`, `sw_append_tail` on every cfg.
4. A sample steps manifest (steps 2..N-1) and a submit wrapper that builds the
   dataset JSON(s), `sw_compose_steps`, and calls `submit_bdriver_chain.sh`.
5. Optionally a local test wrapper using `sw_prepare_testdir`, `sw_run_step`,
   `sw_inspect_nano`.
