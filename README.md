# Reco2Pico

`Reco2Pico` is a CMSSW-based toolkit for producing custom NanoAOD-like **PicoAOD** files from CMS event data and analyzing them with ROOT RDataFrame.

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

Use examples from `PicoProducer/test/scripts`
