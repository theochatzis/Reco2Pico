# Reco2Pico

`Reco2Pico` is a CMSSW-based toolkit for producing custom NanoAOD-like **PicoAOD** files from CMS event data and analyzing them with ROOT RDataFrame.

Functionalities include:

- Produce NanoAOD-structured PicoAOD files from CMS data tiers.
- Allow users to choose which `FlatTable` producers are written.
- Make it easy to add custom physics objects and custom branches.
- Provide Condor submission utilities for large-scale PicoAOD production.
- Provide RDataFrame-based analysis examples over PicoAOD files.

## Branches and releases

| use case | branch | CMSSW release | latest tag |
|---|---|---|---|
| Phase 2 | `main` | CMSSW_20_1_0_pre3 | `v1.0.0_CMSSW_20_1_X` |
| Run 3 | `CMSSW_15_0_X` | CMSSW_15_0_4 | `v1.0.0_CMSSW_15_0_X` |

Supported features, compatibility with central CMSSW and release notes:
[docs/releases/](docs/releases/README.md). How branches, tags and porting work:
[docs/releases/branching.md](docs/releases/branching.md).

## Setup

```bash
# CMSSW release setup (Note: Use LXPLUS8)
cmsrel CMSSW_15_0_4
cd CMSSW_15_0_4/src
cmsenv
# Optional : if you want to connect to your cmssw fork
git cms-init
# Get Reco2Pico: the branch matching the release (table above; main for Phase 2)
git clone -b CMSSW_15_0_X git@github.com:theochatzis/Reco2Pico.git
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

Submit jobs to Condor:

Use examples from `PicoProducer/test/scripts`
