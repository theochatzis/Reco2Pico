# Condor submission for Reco2Pico

This directory contains the batch-submission utilities for producing PicoAOD files with HTCondor.

The current production workflow is:

```text
miniAOD input files
        ↓
cmsRun Reco2Pico/PicoProducer/python/workflows/miniAOD_to_pico_cfg.py
        ↓
PicoAOD ROOT files
```

The Condor machinery is meant to run the same `cmsRun` command that you have already tested interactively on lxplus.

---

## 1. Prerequisites

Before using Condor, make sure the local test works.

From a valid CMSSW area:

```bash
cd $CMSSW_BASE/src
cmsenv
scram b -j 8
```

Then test one file interactively:

```bash
cd $CMSSW_BASE/src/Reco2Pico

cmsRun PicoProducer/python/workflows/miniAOD_to_pico_cfg.py \
  inputFiles=/store/mc/RunIII2024Summer24MiniAODv6/SingleNeutrino_Par-E-10_gun/MINIAODSIM/FlatPU0to120_150X_mcRun3_2024_realistic_v2-v2/120000/0c48c891-c516-475b-a87e-07b752be4cb2.root \
  picoOutputFile=test_pico.root \
  maxEvents=100 \
  tables=vertices,muons,electrons,jets,met,pfcands
```

Check that the output exists:

```bash
ls -lh test_pico.root
```

Inspect branches:

```bash
root -l test_pico.root
```

Inside ROOT:

```cpp
Events->Print()
```

Do not submit to Condor until the interactive test runs successfully.

---

## 2. Input file list

Prepare a text file containing one miniAOD file per line.

Example:

```text
/store/mc/RunIII2024Summer24MiniAODv6/SingleNeutrino_Par-E-10_gun/MINIAODSIM/FlatPU0to120_150X_mcRun3_2024_realistic_v2-v2/120000/0c48c891-c516-475b-a87e-07b752be4cb2.root
/store/mc/RunIII2024Summer24MiniAODv6/SingleNeutrino_Par-E-10_gun/MINIAODSIM/FlatPU0to120_150X_mcRun3_2024_realistic_v2-v2/120000/another-file.root
```

A typical location is:

```bash
condor/datasets/my_dataset.txt
```

If using DAS, you can make a file list with something like:

```bash
dasgoclient --query="file dataset=/DATASET/NAME/MINIAODSIM" > condor/datasets/my_dataset.txt
```

---

## 3. Recommended output location

Use an EOS directory for production outputs, for example:

```bash
/eos/user/t/tchatzis/Reco2Pico/outputs/test_v1
```

Create it before submitting:

```bash
mkdir -p /eos/user/t/tchatzis/Reco2Pico/outputs/test_v1
```

For large campaigns, use a tag-based layout:

```text
/eos/user/t/tchatzis/Reco2Pico/outputs/
├── single_neutrino_test_v1/
├── single_neutrino_test_v2/
└── my_analysis_sample_v1/
```

---

## 4. Basic submission command

From:

```bash
cd $CMSSW_BASE/src/Reco2Pico
```

submit jobs with:

```bash
python3 condor/submit_pico.py \
  --dataset condor/datasets/my_dataset.txt \
  --cfg PicoProducer/python/workflows/miniAOD_to_pico_cfg.py \
  --output-dir /eos/user/t/tchatzis/Reco2Pico/outputs/test_v1 \
  --tag test_v1 \
  --files-per-job 1 \
  --max-events -1 \
  --tables vertices,muons,electrons,jets,met,pfcands
```

The important arguments are:

```text
--dataset        Text file with one input miniAOD file per line
--cfg            cmsRun configuration
--output-dir     Directory where PicoAOD ROOT files will be copied
--tag            Production tag used for job/log names
--files-per-job  Number of input files per Condor job
--max-events     Number of events per job; use -1 for all events
--tables         Comma-separated Pico table list
```

For a small test, use:

```bash
python3 condor/submit_pico.py \
  --dataset condor/datasets/my_dataset.txt \
  --cfg PicoProducer/python/workflows/miniAOD_to_pico_cfg.py \
  --output-dir /eos/user/t/tchatzis/Reco2Pico/outputs/test_v1 \
  --tag test_v1 \
  --files-per-job 1 \
  --max-events 100 \
  --tables vertices,muons,electrons,jets,met
```

---

## 5. Table selection

The Pico table list is passed to `cmsRun` through:

```bash
tables=...
```

Examples:

Minimal object test:

```bash
--tables muons,electrons,jets,met
```

With vertices:

```bash
--tables vertices,muons,electrons,jets,met
```

With PF candidates:

```bash
--tables vertices,muons,electrons,jets,met,pfcands
```

Use PF candidates carefully because they can significantly increase the output size.

---

## 6. What each Condor job should run

Each Condor job should eventually run a command equivalent to:

```bash
cmsRun PicoProducer/python/workflows/miniAOD_to_pico_cfg.py \
  inputFiles=file1.root,file2.root \
  picoOutputFile=pico_JOBID.root \
  maxEvents=-1 \
  tables=vertices,muons,electrons,jets,met,pfcands
```

For files under `/store/...`, the config can usually receive the `/store/...` path directly. If xrootd access is needed explicitly, use:

```text
root://cms-xrd-global.cern.ch//store/...
```

or a local redirector such as:

```text
root://xrootd-cms.infn.it//store/...
```

depending on site behavior.

---

## 7. Logs

A typical Condor layout should create:

```text
condor/jobs/<tag>/
├── logs/
│   ├── job_0.out
│   ├── job_0.err
│   ├── job_0.log
│   └── ...
├── inputs/
│   ├── input_0.txt
│   ├── input_1.txt
│   └── ...
└── submit/
    ├── job_0.sub
    └── ...
```

Check running jobs:

```bash
condor_q
```

Check finished jobs:

```bash
condor_history
```

Inspect logs:

```bash
less condor/jobs/test_v1/logs/job_0.err
less condor/jobs/test_v1/logs/job_0.out
```

The `.err` file is usually the first place to check for CMSSW exceptions.

---

## 8. Output validation

After jobs finish, check the output directory:

```bash
ls -lh /eos/user/t/tchatzis/Reco2Pico/outputs/test_v1
```

Count files:

```bash
ls /eos/user/t/tchatzis/Reco2Pico/outputs/test_v1/*.root | wc -l
```

Check one output file:

```bash
root -l /eos/user/t/tchatzis/Reco2Pico/outputs/test_v1/pico_0.root
```

Inside ROOT:

```cpp
Events->Print()
```

Useful branch checks:

```cpp
Events->Print("*PV*")
Events->Print("Muon*")
Events->Print("Electron*")
Events->Print("Jet*")
Events->Print("PFCand*")
```

---

## 9. Common failures

### `PluginNotFound: PicoVertexTableProducer`

The custom C++ plugin was not found at runtime.

Check:

```bash
cd $CMSSW_BASE/src
scram b -j 8
cmsenv
edmPluginDump | grep PicoVertexTableProducer
```

If nothing appears, inspect:

```bash
Reco2Pico/PicoProducer/plugins/BuildFile.xml
Reco2Pico/PicoProducer/plugins/PicoVertexTableProducer.cc
```

Then rebuild cleanly:

```bash
scram b clean
scram b -j 8
cmsenv
```

### `ProductNotFound`

The job is requesting a collection that is not present in the input file.

Common examples:

```text
offlineSlimmedSecondaryVertices
muonBSConstrain
some NanoAOD helper ValueMap
```

For PicoAOD production, avoid cloning full official NanoAOD tables unless all their helper tasks are also run. Prefer cloning official tables and overriding:

```python
variables=cms.PSet(...)
externalVariables=cms.PSet()
```

### Electron `userInt` not found

Raw `slimmedElectrons` may contain long VID names like:

```text
cutBasedElectronID-RunIIIWinter22-V1-tight
```

while NanoAOD-style tables may expect short aliases like:

```text
cutBasedID_tight
```

Either use the long names directly or run an electron preprocessing step that embeds the short aliases.

### Output file is tiny

Check whether the job crashed before writing events.

Look at:

```bash
less condor/jobs/<tag>/logs/job_<N>.err
```

Also check whether `maxEvents` was accidentally set to `0`.

### PF candidates make the file too large

Try running without `pfcands`:

```bash
--tables vertices,muons,electrons,jets,met
```

or tighten the PF candidate cut in:

```text
PicoProducer/python/tables/pfcands_cff.py
```

---

## 10. Suggested first Condor test

Use a one-file dataset and only 100 events:

```bash
cat > condor/datasets/test_one_file.txt <<'EOF_INNER'
/store/mc/RunIII2024Summer24MiniAODv6/SingleNeutrino_Par-E-10_gun/MINIAODSIM/FlatPU0to120_150X_mcRun3_2024_realistic_v2-v2/120000/0c48c891-c516-475b-a87e-07b752be4cb2.root
EOF_INNER
```

Submit:

```bash
python3 condor/submit_pico.py \
  --dataset condor/datasets/test_one_file.txt \
  --cfg PicoProducer/python/workflows/miniAOD_to_pico_cfg.py \
  --output-dir /eos/user/t/tchatzis/Reco2Pico/outputs/test_condor_one_file \
  --tag test_condor_one_file \
  --files-per-job 1 \
  --max-events 100 \
  --tables vertices,muons,electrons,jets,met
```

After it finishes:

```bash
ls -lh /eos/user/t/tchatzis/Reco2Pico/outputs/test_condor_one_file
```

Then inspect the ROOT file.

---

## 11. Production checklist

Before submitting many jobs:

- The same `cmsRun` command works interactively.
- `scram b -j 8` finishes cleanly.
- `edmPluginDump | grep PicoVertexTableProducer` finds the PV plugin.
- The output directory exists on EOS.
- A one-file Condor test finishes successfully.
- The output branches look correct in `Events->Print()`.
- The output size per event is reasonable.

Only then increase `files-per-job` or submit a full dataset.
