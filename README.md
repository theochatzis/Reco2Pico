# Reco2Pico

`Reco2Pico` is a CMSSW-based toolkit for producing custom NanoAOD-like **PicoAOD** files from CMS event data and analyzing them with ROOT RDataFrame.

The first supported production path is:

```text
miniAOD -> custom flatTables -> PicoAOD
```

Planned extensions include AOD and RECO inputs.

Functionalities include:

- Produce NanoAOD-structured PicoAOD files from CMS data tiers.
- Allow users to choose which `FlatTable` producers are written.
- Make it easy to add custom physics objects and custom branches.
- Provide Condor submission utilities for large-scale PicoAOD production.
- Provide RDataFrame-based analysis examples over PicoAOD files.

## Setup

```bash
# CMSSW release setup (Note: Use LXPLUS8)
cmsrel CMSSW_15_0_4
cd CMSSW_15_0_4/src
cmsenv
# Optional : if you want to connect to your cmssw fork
git cms-init
# Get Reco2Pico 
git clone git@github.com:theochatzis/Reco2Pico.git
# Compile
scram b -j 8
```

Run a local miniAOD test:

```bash
cmsRun Reco2Pico/python/workflows/miniAOD_to_pico_cfg.py \
  inputFiles=file:<miniAODFile.root> \
  outputFile=pico.root \
  maxEvents=100
```

Inspect the output:

```bash
rootls -t pico.root
python Reco2Pico/scripts/validate_branches.py pico.root --branches nMuon Muon_pt nJet Jet_pt MET_pt
```

Run the example RDataFrame analysis:

```bash
python Reco2Pico/analysis/rdf/analyze.py \
  --config Reco2Pico/analysis/configs/example_analysis.yaml \
  --input pico.root \
  --output histograms.root
```

Submit jobs to Condor:

```bash
python Reco2Pico/condor/submit_pico.py \
  --dataset Reco2Pico/condor/datasets/example_miniAOD.txt \
  --cfg Reco2Pico/python/workflows/miniAOD_to_pico_cfg.py \
  --output-dir /store/user/$USER/reco2pico/test_v0 \
  --tag test_v0 \
  --files-per-job 1
```

## Status

This is a v0 scaffold. The structure is intended to be stable, but CMSSW configs should be validated in the exact CMSSW release you intend to use.
