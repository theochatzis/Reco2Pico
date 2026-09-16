#!/bin/bash

# Make the histogram YAML file
cd analyses
python3 make_zjet_profile_maps.py
cd ../

# First pass of analysis un-weighted MC for NPVs
# Data
python3 ../SkimRDFAnalysisBase/run_analysis.py \
  --input-files-dir /eos/user/t/tchatzis/reco2pico/myPicosDirectory/windowedBalance2024/default/DATA/Muon2024I/ \
  --output-dir zjet_example_output \
  --file-pattern "*.root" \
  --histograms-defs analyses/zjet_histograms.yaml \
  --rdf-definition analyses/zjet_rdf_definition.py \
  --add-no-selection

# MC
python3 ../SkimRDFAnalysisBase/run_analysis.py \
  --input-files-dir /eos/user/t/tchatzis/reco2pico/myPicosDirectory/windowedBalance2024/default/MC/ZTo2Mu/ \
  --output-dir zjet_example_output \
  --file-pattern "*.root" \
  --histograms-defs analyses/zjet_histograms.yaml \
  --rdf-definition analyses/zjet_rdf_definition.py \
  --add-no-selection

# # Weighting from NPVs
# python3 make_npv_weights.py \
#   --data zjet_example_output/Muon2025G.root \
#   --mc zjet_example_output/ZTo2Mu.root \
#   --output npv_weights.json \
#   --plot npv_reweighting.pdf

# # Weight MC for NPVs in second pass
# python3 ../SkimRDFAnalysisBase/run_analysis.py \
#   --input-files-dir /eos/user/t/tchatzis/reco2pico/myPicosDirectory/zjet_window_default/default/MC/ZTo2Mu/ \
#   --output-dir zjet_example_output \
#   --file-pattern "*.root" \
#   --histograms-defs analyses/zjet_histograms.yaml \
#   --rdf-definition analyses/zjet_rdf_definition.py \
#   --add-no-selection \
#   --analysis-config analysis_config.yaml

# Make plots

python3 plot_zjet_profile_maps.py \
  --data zjet_example_output/Muon2024I.root \
  --mc zjet_example_output/ZTo2Mu.root \
  --db-min 0.0 \
  --db-max 2.0 \
  --mpf-min 0.5 \
  --mpf-max 1.5 \
  --response-ratio-min 0.90 \
  --response-ratio-max 1.10 \
  --ratio-min 0.50 \
  --ratio-max 2.00 \
  --zpt-min 10.0 \
  --output-dir /eos/user/t/tchatzis/php-plots/windowedBalance/plots_profile2d_2024

