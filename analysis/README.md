# RDataFrame base analysis

Clone the SkimRDFAnalysisBase repo to have the basic scripts that are used for the baseline histograms making structure. Then code is built on top of this.

```bash
cd Reco2Pico/analysis
git clone --branch v1.0.0 git@github.com:theochatzis/SkimRDFAnalysisBase.git
```

`v1.0.0` is the SkimRDFAnalysisBase release that goes with Reco2Pico v1.0.0
(`v1.0.0_CMSSW_15_0_X` and `v1.0.0_CMSSW_20_1_X`). Cloning a tag leaves a
detached HEAD; to develop, run `git switch dev` (or `main`) inside the clone.

It is its own repository with its own history: Reco2Pico does not track it
(it is in `.gitignore`), so commit changes to it there. The analyses expect it
at `analysis/SkimRDFAnalysisBase`.

# RDF definition interface

The architecture is such that:

- `run_analysis.py` = generic execution
- `rdf_definition.py` = physics analysis
- histogram YAML = output description
- optional analysis YAML = numerical/configuration inputs

An analysis module must implement:

```python
def define_columns(df, sample, args, config):
    return df

def get_regions(sample, args, config):
    return {
        "region_name": {
            "cuts": [
                "selection expression",
                "another selection",
            ]
        }
    }
```

It may also implement:

```python
def setup(args, config):
    ...
```

`setup()` is called exactly once before any sample is processed. It is the right
place to load shared libraries, declare C++ helpers, or initialize correctionlib
objects.

`define_columns()` is called once per sample, immediately after construction of
the base RDataFrame. Put `Define()` and `Redefine()` calls there.

`get_regions()` is called once per sample. Regions can therefore depend on the
sample name or user configuration.

Example:

```bash
python3 run_analysis.py \
  --input-files-dir /path/to/input/ntuple \
  --output-dir output \
  --file-pattern "*.root" \
  --histograms-defs analyses/zjet_histograms.yaml \
  --rdf-definition analyses/zjet_rdf_definition.py \
  --add-no-selection
```



