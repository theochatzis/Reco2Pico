# Windowed Balance workflow

## produce unweighted data and MC histograms

Run `run_analysis.py` for data and MC with the supplied
`zjet_rdf_definition.py` and `zjet_histograms.yaml`.

The histogram YAML contains:

```text
zjet/PV_npvs
```

which is used to derive NPV weights.

## derive NPV weights

From this package root:

```bash
python3 make_npv_weights.py \
  --data histograms_data.root \
  --mc histograms_mc_unweighted.root \
  --output npv_weights.json \
  --plot npv_reweighting.pdf
```

The script normalizes the Data and MC NPV distributions to unit area and
stores the binned Data/MC ratio.

## Rerun MC with NPV weighting

Create:

```yaml
npv_weights: "/absolute/path/to/WindowedBalanceStudy/npv_weights.json"
```

and rerun:

```bash
python3 SkimRDFAnalysisBase/run_analysis.py \
  ... \
  --rdf-definition WindowedBalanceStudy/analyses/zjet_rdf_definition.py \
  --histograms-defs WindowedBalanceStudy/analyses/zjet_histograms.yaml \
  --analysis-config WindowedBalanceStudy/analysis_config.yaml
```

For MC the event weight becomes:

```text
sign(genWeight) * NPV_weight(PV_npvs)
```

For data it stays 1.

## Make the study plots

```bash
python3 WindowedBalanceStudy/plot_windowed_balance.py \
  --data histograms_data.root \
  --mc histograms_mc_npvweighted.root \
  --output-dir plots
```

Outputs include:

```text
plots/
  jet_eta_parallel.{pdf,png}
  jet_eta_transverse.{pdf,png}
  jet_eta_windowed.{pdf,png}

  DB_nominal_vs_windowed.{pdf,png}
  MPF_nominal_vs_windowed.{pdf,png}

  fractions/
    fractions_parallel_eta0to1p3.{pdf,png}
    ...
    fractions_windowed_eta3p0to5p0.{pdf,png}
```

Every comparison has a Data/MC ratio panel.