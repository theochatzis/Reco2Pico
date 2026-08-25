#!/bin/bash

# First pass of analysis un-weighted MC for NPVs
# Data
python3 ../SkimRDFAnalysisBase/run_analysis.py \
  --input-files-dir /eos/user/t/tchatzis/reco2pico/myPicosDirectory/windowed_balance_reclusterV2/default/DATA/Muon2025G/ \
  --output-dir zjet_example_output \
  --file-pattern "*.root" \
  --histograms-defs analyses/zjet_histograms.yaml \
  --rdf-definition analyses/zjet_rdf_definition.py \
  --add-no-selection

# MC
python3 ../SkimRDFAnalysisBase/run_analysis.py \
  --input-files-dir /eos/user/t/tchatzis/reco2pico/myPicosDirectory/windowed_balance_reclusterV2/default/MC/ZTo2Mu/ \
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
  --data zjet_example_output/Muon2025G.root \
  --mc zjet_example_output/ZTo2Mu.root \
  --db-min 0.0 \
  --db-max 2.0 \
  --mpf-min 0.5 \
  --mpf-max 1.5 \
  --output-dir /eos/user/t/tchatzis/php-plots/windowedBalance/plots_profile2d

# python3 plot_windowed_balance_mplhep.py \
#   --data zjet_example_output/Muon2025G.root \
#   --mc zjet_example_output/ZTo2Mu.root \
#   --output-dir /eos/user/t/tchatzis/php-plots/windowedBalance \
#   --fractions-ratio-min 0.5 \
#   --fractions-ratio-max 2.0 \
#   --response-y-min 0.5 \
#   --response-y-max 2.0 \
#   --response-ratio-min 0.8 \
#   --response-ratio-max 1.2 \
#   --zpt-min 3.0 \
#   --stage-local